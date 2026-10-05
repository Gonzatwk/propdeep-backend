import hashlib
import hmac
import json
import time
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import main
from propdeep import board
from propdeep.clients.odds import PropLine
from propdeep.config import Settings
from propdeep.db import make_session_factory
from propdeep.pipeline import Analyzer
from tests.fakes import FakeBDL

DAY = date(2026, 11, 20)
SOON = (datetime.now(timezone.utc) + timedelta(hours=6)).strftime("%Y-%m-%dT%H:%M:%SZ")
PAST = (datetime.now(timezone.utc) - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
WEBHOOK_SECRET = "whsec_prueba"


class FakeOdds:
    """Dos partidos; Luka sale en ambos para tener varias líneas."""

    def __init__(self, second_start=SOON):
        self.events = [
            {"id": "ev1", "commence_time": SOON, "home_team": "Dallas Mavericks", "away_team": "Los Angeles Lakers"},
            {"id": "ev2", "commence_time": second_start, "home_team": "Boston Celtics", "away_team": "Miami Heat"},
        ]

    def events_on(self, day):
        return self.events

    def player_props(self, event):
        mk = lambda market, line, o, u, book: PropLine(event["id"], event["commence_time"], event["home_team"],
                                                       event["away_team"], "Luka Doncic", market, line, o, u, book)
        return [
            mk("player_points", 27.5, 1.95, 1.85, "bookA"),
            mk("player_points", 27.5, 1.90, 1.90, "bookB"),
            mk("player_points", 26.5, 1.80, 2.00, "bookC"),
            mk("player_assists", 7.5, 1.9, 1.9, "bookB"),
        ]


@pytest.fixture
def api(tmp_path, monkeypatch):
    bdl = FakeBDL([34.0, 33.0, 35.0, 32.0, 36.0] * 4, DAY)
    settings = Settings(admin_token="secreto", database_url=f"sqlite:///{tmp_path}/t.db", free_lines_per_day=1,
                        stripe_webhook_secret=WEBHOOK_SECRET, web_url="https://web.test")
    factory = make_session_factory(settings.database_url)
    odds = FakeOdds()
    sent = []
    monkeypatch.setattr(main, "settings", lambda: settings)
    monkeypatch.setattr(main, "session_factory", lambda: factory)
    monkeypatch.setattr(main, "bdl_client", lambda: bdl)
    monkeypatch.setattr(main, "odds_client", lambda: odds)
    monkeypatch.setattr(main, "claude_client", lambda: None)
    monkeypatch.setattr(main, "send_login_link", lambda s, to, link: sent.append((to, link)))
    main.app.dependency_overrides[main.analyzer] = lambda: Analyzer(bdl, 2026, 0.03, 0.5)
    yield SimpleNamespace(c=TestClient(main.app), sent=sent, odds=odds)
    main.app.dependency_overrides.clear()


ADMIN = {"x-admin-token": "secreto"}


def _login(api, email="ana@example.com"):
    assert api.c.post("/auth/login", json={"email": email}).status_code == 202
    token = api.sent[-1][1].split("token=")[1]
    r = api.c.post("/auth/verify", json={"token": token})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['token']}"}


def _webhook(api, event: dict):
    payload = json.dumps(event)
    t = int(time.time())
    sig = hmac.new(WEBHOOK_SECRET.encode(), f"{t}.{payload}".encode(), hashlib.sha256).hexdigest()
    return api.c.post("/stripe/webhook", content=payload,
                      headers={"stripe-signature": f"t={t},v1={sig}", "content-type": "application/json"})


def _subscribe(api, headers, status="trialing"):
    user_id = None
    # El id de usuario va en los metadatos de la suscripción (lo pone create_checkout).
    from propdeep.accounts import User
    with main.session_factory()() as s:
        user_id = s.query(User).one().id
    end = int((datetime.now(timezone.utc) + timedelta(days=7)).timestamp())
    return _webhook(api, {"type": "customer.subscription.created", "data": {"object": {
        "customer": "cus_1", "status": status, "metadata": {"user_id": str(user_id)},
        "items": {"data": [{"current_period_end": end}]}, "trial_end": end}}})


def test_board_publishes_every_line_once_with_free_quota(api):
    r = api.c.post(f"/admin/board?game_date={DAY}", headers=ADMIN).json()
    # Una línea principal por jugador y mercado (las de cada casa van dentro).
    assert r == {"published": 4, "free": 1}
    # Repetirlo no duplica nada: lo publicado no se toca.
    assert api.c.post(f"/admin/board?game_date={DAY}", headers=ADMIN).json()["published"] == 0

    b = api.c.get("/board").json()
    assert b["game_date"] == DAY.isoformat()
    assert [g["event_id"] for g in b["games"]] == ["ev1", "ev2"]
    assert b["viewer"] == {"logged_in": False, "subscriber": False}


def test_free_visitor_sees_free_line_and_locked_rest(api):
    api.c.post(f"/admin/board?game_date={DAY}", headers=ADMIN)
    lines = api.c.get("/board/games/ev1").json()["lines"] + api.c.get("/board/games/ev2").json()["lines"]
    free = [l for l in lines if not l["locked"]]
    locked = [l for l in lines if l["locked"]]
    assert len(free) == 1 and free[0]["free"] and free[0]["stat"] == "pts" and free[0]["event_id"] == "ev1"
    assert all("projection" not in l and "hit_rates" not in l for l in locked)

    # Modo análisis: nada de veredicto, confianza ni ventaja en lo que sale de la API.
    f = free[0]
    assert f["line"] == 27.5 and f["books_count"] == 3 and f["projection"] > 27.5
    assert f["hit_rates"]["last5"] == 1.0 and f["hit_rates"]["last10"] == 1.0
    assert f["best"]["over"] == {"bookmaker": "bookC", "line": 26.5, "odds": 1.80}
    assert f["best"]["under"] == {"bookmaker": "bookB", "line": 27.5, "odds": 1.90}
    detail = api.c.get(f"/board/lines/{f['id']}")
    assert detail.status_code == 200
    d = detail.json()
    assert len(d["books"]) == 3 and d["trends"]["splits"]["home"]["games"] == 0
    for body in (f, d):
        for key in ("side", "confidence", "edge", "probability", "prob_over", "expected_value"):
            assert key not in body
    assert "ventaja" not in d["report"].lower() and "orientativa" in d["report"]
    assert api.c.get(f"/board/lines/{locked[0]['id']}").status_code == 402


def test_lines_open_to_everyone_once_the_game_starts(api):
    api.odds.events[1]["commence_time"] = PAST
    api.c.post(f"/admin/board?game_date={DAY}", headers=ADMIN)
    assert all(not l["locked"] for l in api.c.get("/board/games/ev2").json()["lines"])


def test_logged_in_without_subscription_is_still_locked(api):
    api.c.post(f"/admin/board?game_date={DAY}", headers=ADMIN)
    h = _login(api)
    assert api.c.get("/me", headers=h).json()["subscriber"] is False
    lines = api.c.get("/board/games/ev1", headers=h).json()["lines"]
    assert sum(l["locked"] for l in lines) >= 1


def test_subscriber_by_webhook_unlocks_everything(api):
    api.c.post(f"/admin/board?game_date={DAY}", headers=ADMIN)
    h = _login(api)
    assert _subscribe(api, h).status_code == 200
    me = api.c.get("/me", headers=h).json()
    assert me["subscriber"] and me["status"] == "trialing" and not me["trial_available"]
    lines = api.c.get("/board/games/ev1", headers=h).json()["lines"]
    assert all(not l["locked"] for l in lines)
    detail = api.c.get(f"/board/lines/{lines[1]['id']}", headers=h).json()
    assert detail["report"] and detail["trends"]["games"] == 20 and detail["game"]["home_team"] == "Dallas Mavericks"

    # Al cancelarse en Stripe se vuelve a bloquear.
    _webhook(api, {"type": "customer.subscription.deleted", "data": {"object": {"customer": "cus_1", "status": "canceled"}}})
    assert api.c.get("/me", headers=h).json()["subscriber"] is False


def test_webhook_rejects_bad_signature(api):
    r = api.c.post("/stripe/webhook", content="{}", headers={"stripe-signature": "t=1,v1=mal"})
    assert r.status_code == 400


def test_login_link_is_single_use_and_rate_limited(api):
    api.c.post("/auth/login", json={"email": "  Ana@Example.com "})
    to, link = api.sent[-1]
    assert to == "ana@example.com" and link.startswith("https://web.test/entrar?token=")
    token = link.split("token=")[1]
    assert api.c.post("/auth/verify", json={"token": token}).status_code == 200
    assert api.c.post("/auth/verify", json={"token": token}).status_code == 400
    assert api.c.post("/auth/login", json={"email": "no-es-correo"}).status_code == 422
    codes = [api.c.post("/auth/login", json={"email": "ana@example.com"}).status_code for _ in range(5)]
    assert codes[-1] == 429


def test_logout_and_delete_account(api):
    h = _login(api)
    assert api.c.delete("/me", headers=h).status_code == 200
    assert api.c.get("/me", headers=h).status_code == 401
    h = _login(api, "luis@example.com")
    api.c.post("/auth/logout", headers=h)
    assert api.c.get("/me", headers=h).status_code == 401


def test_cannot_delete_account_with_active_subscription(api):
    h = _login(api)
    _subscribe(api, h, status="active")
    assert api.c.delete("/me", headers=h).status_code == 409


def test_checkout_disabled_without_stripe_keys(api):
    h = _login(api)
    assert api.c.post("/billing/checkout", json={"plan": "monthly"}, headers=h).status_code == 503
    assert api.c.post("/billing/checkout", json={"plan": "monthly"}).status_code == 401


def test_pick_free_points_of_the_top_player_one_per_game():
    a = lambda player, stat, proj: SimpleNamespace(player=player, stat=stat, projection=proj)
    m = lambda ev, t: {"event_id": ev, "commence_time": t}
    cands = [
        (a("A", "pts", 20.0), m("e1", "1")),
        (a("B", "pts", 28.0), m("e1", "1")),
        (a("B", "ast", 9.0), m("e1", "1")),
        (a("C", "reb", 10.0), m("e2", "2")),
        (a("B", "pts", 30.0), m("e3", "3")),
        (a("D", "pts", 25.0), m("e3", "3")),
    ]
    assert board._pick_free(cands, 3) == {1, 3, 5}
    assert board._pick_free(cands, 0) == set()


def test_metrics_count_trials_and_conversions(api):
    h = _login(api)
    _subscribe(api, h, status="trialing")
    _subscribe(api, h, status="active")
    _login(api, "luis@example.com")
    assert api.c.post("/waitlist", json={"email": "Pepe@example.com", "source": "landing"}).status_code == 201
    assert api.c.post("/waitlist", json={"email": "pepe@example.com"}).status_code == 201
    assert api.c.get("/admin/metrics").status_code == 401
    m = api.c.get("/admin/metrics", headers=ADMIN).json()
    assert m["accounts"] == 2 and m["waitlist"] == 1
    assert m["trials_started"] == 1 and m["paid_after_trial"] == 1 and m["trial_to_paid"] == 1.0
