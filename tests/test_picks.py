from datetime import datetime, timedelta, timezone

import pytest

import main
from propdeep import picks
from tests.fakes import stat_row
from tests.test_board import ADMIN, DAY, _login

LATER = (datetime.now(timezone.utc) + timedelta(hours=3)).isoformat()
BEFORE = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
MANUAL = {"player_name": "Jayson Tatum", "stat": "pts", "line": 26.5, "side": "under", "odds": 1.91,
          "bookmaker": "Bet365", "commence_time": LATER, "home_team": "Boston Celtics", "away_team": "Miami Heat"}


@pytest.fixture
def gonza(api, monkeypatch):
    s = main.settings()
    from dataclasses import replace
    monkeypatch.setattr(main, "settings", lambda: replace(s, admin_emails="gonza@example.com"))
    return _login(api, "gonza@example.com")


def test_only_the_author_can_publish(api, gonza):
    assert api.c.post("/picks", json=MANUAL).status_code == 403
    assert api.c.post("/picks", json=MANUAL, headers=_login(api, "ana@example.com")).status_code == 403
    assert api.c.get("/me", headers=gonza).json()["admin"] is True
    # El autor ve todas las líneas sin suscripción, para poder elegir sus picks.
    api.c.post(f"/admin/board?game_date={DAY}", headers=ADMIN)
    assert not any(x["locked"] for x in api.c.get("/board/games/ev1", headers=gonza).json()["lines"])
    r = api.c.post("/picks", json=MANUAL, headers=gonza)
    assert r.status_code == 201 and len(r.json()["content_hash"]) == 64
    assert api.c.post("/picks", json={**MANUAL, "side": "over"}, headers=ADMIN).status_code == 201


def test_picks_are_published_before_the_game_and_never_edited(api, gonza):
    assert api.c.post("/picks", json={**MANUAL, "commence_time": BEFORE}, headers=gonza).status_code == 422
    pid = api.c.post("/picks", json=MANUAL, headers=gonza).json()["id"]
    # No hay forma de editar ni borrar un pick.
    assert api.c.put(f"/picks/{pid}", json=MANUAL, headers=gonza).status_code in (404, 405)
    assert api.c.delete(f"/picks/{pid}", headers=gonza).status_code in (404, 405)
    # No se liquida antes de jugar.
    assert api.c.post(f"/picks/{pid}/settle", json={"actual": 20}, headers=gonza).status_code == 409


def test_pick_from_a_board_line_settles_by_itself_and_losses_stay(api, gonza):
    api.c.post(f"/admin/board?game_date={DAY}", headers=ADMIN)
    line = next(x for x in api.c.get("/board/games/ev1", headers=gonza).json()["lines"] if x["stat"] == "pts")
    r = api.c.post("/picks", json={"line_id": line["id"], "side": "under", "odds": 1.9, "bookmaker": "bookB",
                                   "note": "Viene de muchos minutos"}, headers=gonza).json()
    assert r["player"] == "Luka Doncic" and r["line"] == line["line"] and r["auto_settle"]

    bdl = main.bdl_client()
    bdl.final_stats[999] = [stat_row(DAY, 40.0, game_id=999)]
    api.c.post("/admin/settle", headers=ADMIN)
    body = api.c.get("/picks").json()
    assert body["picks"][0]["status"] == "lost" and body["picks"][0]["actual"] == 40.0
    assert body["summary"]["lost"] == 1 and body["summary"]["profit_units"] == -1.0
    assert "no garantizan nada" in body["warning"]


def test_manual_settle_only_once(api):
    with main.session_factory()() as s:
        p = picks.create(s, {**MANUAL, "commence_time": datetime.fromisoformat(LATER)})
        p.commence_time = datetime.now(timezone.utc) - timedelta(hours=3)
        s.commit()
        pid = p.id
    assert api.c.post(f"/picks/{pid}/settle", json={"actual": 22}, headers=ADMIN).json()["status"] == "won"
    assert api.c.post(f"/picks/{pid}/settle", json={"actual": 30}, headers=ADMIN).status_code == 409


def test_summary_counts_units():
    def mk(status, odds, stake=1.0):
        return picks.Pick(status=status, odds=odds, stake=stake)

    s = picks.summary([mk("won", 2.0), mk("lost", 1.9), mk("won", 1.5, 2.0), mk("void", 1.9), mk("pending", 1.8)])
    assert s["won"] == 2 and s["lost"] == 1 and s["pending"] == 1 and s["push_or_void"] == 1
    assert s["profit_units"] == pytest.approx(1.0 + 1.0 - 1.0)
    assert s["roi"] == pytest.approx(1.0 / 4)
    assert s["hit_rate"] == 0.6667
