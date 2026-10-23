"""Uso personal en el PC: entrar sin correo y jornada automática."""
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone

import main
from propdeep import auto
from propdeep.config import Settings
from propdeep.pipeline import Analyzer
from tests.fakes import FakeBDL
from tests.test_board import DAY, FakeOdds


def _local(monkeypatch, **kw):
    s = replace(main.settings(), admin_emails="gonza@example.com", local_login=True, **kw)
    monkeypatch.setattr(main, "settings", lambda: s)


def test_local_login_returns_token_for_admin_on_localhost(api, monkeypatch):
    _local(monkeypatch, web_url="http://localhost:5173")
    r = api.c.post("/auth/login", json={"email": "Gonza@example.com"})
    assert r.status_code == 202 and api.sent == []
    v = api.c.post("/auth/verify", json={"token": r.json()["token"]}).json()
    me = api.c.get("/me", headers={"Authorization": f"Bearer {v['token']}"}).json()
    assert me["admin"] and me["email"] == "gonza@example.com"


def test_local_login_never_for_others_or_outside_localhost(api, monkeypatch):
    _local(monkeypatch, web_url="http://localhost:5173")
    assert "token" not in api.c.post("/auth/login", json={"email": "otra@example.com"}).json()
    _local(monkeypatch, web_url="https://propdeep.pages.dev")
    assert "token" not in api.c.post("/auth/login", json={"email": "gonza@example.com"}).json()
    assert len(api.sent) == 2


def test_jornada_rolls_over_after_last_games():
    assert auto.jornada(datetime(2026, 10, 22, 3, 0, tzinfo=timezone.utc)) == date(2026, 10, 21)
    assert auto.jornada(datetime(2026, 10, 22, 9, 0, tzinfo=timezone.utc)) == date(2026, 10, 22)


class CountingOdds(FakeOdds):
    def __init__(self, starts):
        super().__init__()
        for e, start in zip(self.events, starts):
            e["commence_time"] = start.strftime("%Y-%m-%dT%H:%M:%SZ")
        self.calls = []

    def player_props(self, event):
        self.calls.append(event["id"])
        return super().player_props(event)


def test_tick_publishes_each_game_once_when_it_is_close(tmp_path):
    from propdeep.db import make_session_factory

    now = datetime(2026, 11, 20, 18, 0, tzinfo=timezone.utc)
    odds = CountingOdds([now + timedelta(hours=2), now + timedelta(hours=12)])
    bdl = FakeBDL([34.0, 33.0, 35.0, 32.0, 36.0] * 4, DAY)
    s = Settings(database_url=f"sqlite:///{tmp_path}/t.db", free_lines_per_day=1, auto_hours_before=10)
    factory = make_session_factory(s.database_url)
    an = Analyzer(bdl, 2026, 0.03, 0.5)
    report = lambda a, meta: "informe"  # noqa: E731

    with factory() as session:
        assert auto.tick(session, an, odds, bdl, s, report, now=now)["published"] == 2
        assert auto.tick(session, an, odds, bdl, s, report, now=now)["published"] == 0
        assert odds.calls == ["ev1"]
        later = now + timedelta(hours=3)
        assert auto.tick(session, an, odds, bdl, s, report, now=later)["published"] == 2
        assert odds.calls == ["ev1", "ev2"]


def test_balldontlie_waits_on_429_and_caches_repeated_queries():
    import httpx

    from propdeep.clients.balldontlie import BalldontlieClient

    calls = []

    def handler(request):
        calls.append(str(request.url))
        if len(calls) == 1:
            return httpx.Response(429, headers={"retry-after": "2"})
        return httpx.Response(200, json={"data": [{"id": 1}], "meta": {}})

    waits = []
    http = httpx.Client(base_url="https://bdl.test", transport=httpx.MockTransport(handler))
    bdl = BalldontlieClient("k", http=http, sleep=waits.append)
    day = date(2026, 10, 21)
    assert bdl.played_yesterday(16, day) and bdl.played_yesterday(16, day)
    assert waits == [2.0] and len(calls) == 2


def test_background_loop_runs_a_tick(tmp_path, monkeypatch):
    import threading

    from propdeep.db import make_session_factory

    seen = threading.Event()
    s = Settings(database_url=f"sqlite:///{tmp_path}/t.db", auto_every_minutes=60)
    monkeypatch.setattr(auto, "tick", lambda session, an, odds, bdl, settings, report, now=None:
                        (seen.set(), {"settled": 0, "published": 0, "events": []})[1]
                        if settings is s and report == "r" else None)
    thread = auto.start(make_session_factory(s.database_url), lambda: ("an", "odds", "bdl", "r"), s)
    assert seen.wait(5)
    thread.stop.set()


def _auto_setup(tmp_path, odds):
    from propdeep.db import make_session_factory

    bdl = FakeBDL([34.0, 33.0, 35.0, 32.0, 36.0] * 4, DAY)
    s = Settings(database_url=f"sqlite:///{tmp_path}/t.db", free_lines_per_day=1, auto_hours_before=10)
    an = Analyzer(bdl, 2026, 0.03, 0.5)
    return make_session_factory(s.database_url)(), an, bdl, s, (lambda a, meta: "informe")


def test_game_without_lines_is_not_requested_every_tick(tmp_path):
    now = datetime(2026, 11, 20, 12, 0, tzinfo=timezone.utc)
    start = now + timedelta(hours=8)

    class NoProps(CountingOdds):
        def player_props(self, event):
            self.calls.append(event["id"])
            return []

    odds = NoProps([start, start + timedelta(days=2)])
    session, an, bdl, s, report = _auto_setup(tmp_path, odds)
    for minutes in range(0, 8 * 60, 20):  # una vuelta cada 20 min hasta el inicio
        auto.tick(session, an, odds, bdl, s, report, now=now + timedelta(minutes=minutes))
    # Una vez a ~8 h, un repaso a 3 h y otro a 1 h: 3 peticiones, no 24.
    assert odds.calls == ["ev1", "ev1", "ev1"]


def test_half_published_game_is_completed_later_without_duplicates(tmp_path):
    from propdeep.clients.odds import PropLine
    from propdeep.db import Prediction

    now = datetime(2026, 11, 20, 12, 0, tzinfo=timezone.utc)
    start = now + timedelta(hours=8)

    class LateRebounds(CountingOdds):
        rebounds = False

        def player_props(self, event):
            props = super().player_props(event)
            if self.rebounds:
                props.append(PropLine(event["id"], event["commence_time"], event["home_team"], event["away_team"],
                                      "Luka Doncic", "player_rebounds", 8.5, 1.9, 1.9, "bookB"))
            return props

    odds = LateRebounds([start, start + timedelta(days=2)])
    session, an, bdl, s, report = _auto_setup(tmp_path, odds)
    assert auto.tick(session, an, odds, bdl, s, report, now=now)["published"] == 2  # puntos y asistencias
    odds.rebounds = True
    assert auto.tick(session, an, odds, bdl, s, report, now=start - timedelta(hours=2, minutes=50))["published"] == 1
    stats = sorted(p.stat for p in session.query(Prediction).filter_by(event_id="ev1"))
    assert stats == ["ast", "pts", "reb"]


def test_one_failing_game_does_not_stop_the_others(tmp_path):
    now = datetime(2026, 11, 20, 18, 0, tzinfo=timezone.utc)

    class Broken(CountingOdds):
        def player_props(self, event):
            if event["id"] == "ev1":
                raise RuntimeError("The Odds API caída")
            return super().player_props(event)

    odds = Broken([now + timedelta(hours=1), now + timedelta(hours=2)])
    session, an, bdl, s, report = _auto_setup(tmp_path, odds)
    done = auto.tick(session, an, odds, bdl, s, report, now=now)
    assert done["published"] == 2 and len(done["events"]) == 2
