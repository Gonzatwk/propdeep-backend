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
