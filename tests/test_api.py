from datetime import date

import pytest
from fastapi.testclient import TestClient

import main
from propdeep.config import Settings
from propdeep.db import make_session_factory
from propdeep.pipeline import Analyzer
from tests.fakes import FakeBDL, PLAYER, stat_row

DAY = date(2026, 11, 20)


@pytest.fixture
def client(tmp_path, monkeypatch):
    bdl = FakeBDL([34.0, 33.0, 35.0, 32.0, 36.0] * 4, DAY)
    settings = Settings(admin_token="secreto", database_url=f"sqlite:///{tmp_path}/t.db")
    factory = make_session_factory(settings.database_url)
    monkeypatch.setattr(main, "settings", lambda: settings)
    monkeypatch.setattr(main, "session_factory", lambda: factory)
    monkeypatch.setattr(main, "bdl_client", lambda: bdl)
    monkeypatch.setattr(main, "claude_client", lambda: None)
    main.app.dependency_overrides[main.analyzer] = lambda: Analyzer(bdl, 2026, 0.03, 0.5)
    yield TestClient(main.app), bdl
    main.app.dependency_overrides.clear()


BODY = {"player": "Luka Doncic", "stat": "pts", "line": 27.5, "over_odds": 1.9,
        "under_odds": 1.9, "game_date": DAY.isoformat(), "bookmaker": "bookB"}


def test_analyze_returns_report_and_disclaimer(client):
    c, _ = client
    r = c.post("/analyze", json=BODY)
    assert r.status_code == 200
    body = r.json()
    assert body["analysis"]["side"] == "over"
    assert "mayores de 18" in body["disclaimer"]
    assert "Luka Doncic" in body["report"]


def test_publish_requires_admin(client):
    c, _ = client
    assert c.post("/admin/publish", json=BODY).status_code == 401
    assert c.post("/admin/publish", json=BODY, headers={"x-admin-token": "mal"}).status_code == 401


def test_publish_settle_and_track_record(client):
    c, bdl = client
    h = {"x-admin-token": "secreto"}
    pub = c.post("/admin/publish", json=BODY, headers=h).json()
    assert pub["status"] == "pending" and len(pub["content_hash"]) == 64

    # Sin estadísticas finales todavía: sigue pendiente.
    assert c.post("/admin/settle", headers=h).json()["settled"] == []

    bdl.final_stats[999] = [stat_row(DAY, 31.0, game_id=999)]
    settled = c.post("/admin/settle", headers=h).json()["settled"]
    assert settled[0]["status"] == "won" and settled[0]["actual"] == 31.0

    history = c.get("/predictions").json()
    assert len(history) == 1
    tr = c.get("/track-record").json()
    assert tr["overall"]["won"] == 1
    assert tr["overall"]["profit_units"] == pytest.approx(0.9)


def test_did_not_play_is_void(client):
    c, bdl = client
    h = {"x-admin-token": "secreto"}
    c.post("/admin/publish", json=BODY, headers=h)
    bdl.final_stats[999] = [stat_row(DAY, 0, mins="0", game_id=999)]
    assert c.post("/admin/settle", headers=h).json()["settled"][0]["status"] == "void"


def test_unknown_player_404(client):
    c, _ = client
    assert c.post("/analyze", json={**BODY, "player": "Nadie"}).status_code == 404


def test_player_fixture_sanity():
    assert PLAYER["last_name"] == "Doncic"
