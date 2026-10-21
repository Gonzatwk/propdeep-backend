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


def test_parlay_wins_only_if_all_legs_win_and_void_leg_leaves_the_odds(api, gonza):
    api.c.post(f"/admin/board?game_date={DAY}", headers=ADMIN)
    lines = api.c.get("/board/games/ev1", headers=gonza).json()["lines"]
    pts = next(x for x in lines if x["stat"] == "pts")
    ast = next(x for x in lines if x["stat"] == "ast")
    body = {"bookmaker": "Bet365", "stake": 2, "legs": [
        {"line_id": pts["id"], "side": "over", "odds": 1.9},
        {"line_id": ast["id"], "side": "over", "odds": 2.0},
    ]}
    assert api.c.post("/parlays", json={**body, "legs": body["legs"][:1]}, headers=gonza).status_code == 422
    assert api.c.post("/parlays", json=body).status_code == 403
    r = api.c.post("/parlays", json=body, headers=gonza)
    assert r.status_code == 201 and r.json()["odds"] == 3.8 and len(r.json()["legs"]) == 2

    got = api.c.get("/picks").json()
    # Las selecciones no cuentan como picks sueltos.
    assert got["picks"] == [] and got["parlay_summary"]["pending"] == 1

    bdl = main.bdl_client()
    row = stat_row(DAY, 40.0, game_id=999)  # 40 puntos y 8 asistencias: ganan las dos
    bdl.final_stats[999] = [row]
    api.c.post("/admin/settle", headers=ADMIN)
    got = api.c.get("/picks").json()
    assert got["parlays"][0]["status"] == "won"
    assert got["parlay_summary"]["profit_units"] == pytest.approx(2 * 2.8)
    assert got["total"]["won"] == 1


def test_parlay_settlement_rules():
    from propdeep.db import make_session_factory

    factory = make_session_factory("sqlite://")
    later = datetime.fromisoformat(LATER)
    with factory() as s:
        legs = [{**MANUAL, "commence_time": later, "odds": o} for o in (2.0, 1.5, 3.0)]
        p = picks.create_parlay(s, legs, "Bet365", odds=10.0)
        a, b, c = picks.legs_of(s, p.id)
        a.status, b.status = "won", "void"
        assert picks.refresh_parlays(s) == []  # falta una
        c.status = "won"
        picks.refresh_parlays(s)
        assert p.status == "won" and p.settled_odds == pytest.approx(10.0 / 1.5, abs=1e-3)
        q = picks.create_parlay(s, legs[:2], "Bet365")
        x, _ = picks.legs_of(s, q.id)
        x.status = "lost"
        picks.refresh_parlays(s)
        assert q.status == "lost" and q.odds == 3.0


def test_moneyline_shows_on_the_board_and_settles_by_score(api, gonza):
    api.c.post(f"/admin/board?game_date={DAY}", headers=ADMIN)
    game = next(g for g in api.c.get(f"/board?game_date={DAY}").json()["games"] if g["event_id"] == "ev1")
    assert game["moneyline"]["best"]["home"] == {"bookmaker": "bookB", "odds": 1.65}
    assert game["moneyline"]["best"]["away"]["odds"] == 2.4
    assert len(api.c.get("/board/games/ev1").json()["game"]["moneyline"]["books"]) == 2

    ml = {"stat": "ml", "event_id": "ev1", "side": "over", "odds": 2.4, "bookmaker": "bookA"}
    assert api.c.post("/picks", json={**ml, "team": "Boston Celtics"}, headers=gonza).status_code == 422
    r = api.c.post("/picks", json={**ml, "team": "Los Angeles Lakers"}, headers=gonza).json()
    assert r["player"] == "Los Angeles Lakers" and r["stat"] == "ml" and r["auto_settle"]
    # En una combinada junto a un prop.
    line = next(x for x in api.c.get("/board/games/ev1", headers=gonza).json()["lines"] if x["stat"] == "pts")
    legs = [{**ml, "team": "Dallas Mavericks", "odds": 1.65}, {"line_id": line["id"], "side": "over", "odds": 1.9}]
    assert api.c.post("/parlays", json={"legs": legs, "bookmaker": "bookB"}, headers=gonza).status_code == 201

    bdl = main.bdl_client()
    bdl.scores[999] = (110, 104)  # gana Dallas (local)
    bdl.final_stats[999] = [stat_row(DAY, 40.0, game_id=999)]
    api.c.post("/admin/settle", headers=ADMIN)
    body = api.c.get("/picks").json()
    assert body["picks"][0]["status"] == "lost" and body["picks"][0]["actual"] == -6
    assert body["parlays"][0]["status"] == "won"


def test_moneyline_paper_bet_links_its_game_later(api, gonza):
    from propdeep.moneyline import refresh

    with main.session_factory()() as session:
        refresh(session, api.odds, DAY)  # partido sin props publicados: sin game_id aún
    ml = {"stat": "ml", "event_id": "ev2", "team": "Miami Heat", "side": "over", "odds": 2.4,
          "bookmaker": "bookA", "stake": 20}
    assert api.c.post("/paper/bets", json=ml, headers=gonza).status_code == 201
    with main.session_factory()() as session:
        [p] = picks.pending_ml_unlinked(session)
        p.commence_time = datetime.now(timezone.utc) - timedelta(hours=3)
        session.commit()
    bdl = main.bdl_client()
    bdl.games_on = lambda day: [{"id": 555, "home_team": {"full_name": "Boston Celtics"},
                                 "visitor_team": {"full_name": "Miami Heat"}}]
    bdl.game = lambda gid: {"id": gid, "status": "Final", "home_team": {"full_name": "Boston Celtics"},
                            "visitor_team": {"full_name": "Miami Heat"}, "home_team_score": 99,
                            "visitor_team_score": 101}
    api.c.post("/admin/settle", headers=ADMIN)
    state = api.c.get("/paper", headers=gonza).json()
    assert state["bank"]["profit"] == 28.0
