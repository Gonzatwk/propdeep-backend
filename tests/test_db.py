from datetime import datetime, timezone

from propdeep.db import Prediction, make_session_factory, publish, verify
from propdeep.model import MODEL_VERSION, model_version
from propdeep.track_record import OLD_VERSION, summary

ANALYSIS = {"player": "Luka Doncic", "stat": "pts", "line": 27.5, "side": "over", "prob_over_final": 0.56,
            "odds_taken": 1.9, "edge": 0.034, "confidence": "baja"}
META = {"game_date": "2026-11-20", "game_id": 999, "player_id": 1, "bookmaker": "bookB"}


def _session(tmp_path):
    return make_session_factory(f"sqlite:///{tmp_path}/t.db")()


def test_model_version_records_parameters():
    v = model_version(0.2, 0.03, False)
    assert v == f"{MODEL_VERSION} peso=0.2 ventaja=0.03 companeros=0"


def test_published_prediction_keeps_its_version_and_verifies(tmp_path):
    session = _session(tmp_path)
    p = publish(session, analysis=ANALYSIS, report="r", meta={**META, "model_version": "v1 peso=0.2"})
    session.expire_all()
    p = session.get(Prediction, p.id)
    assert p.model_version == "v1 peso=0.2"
    assert verify(p)
    # Cualquier cambio, también en la versión, rompe el hash.
    p.model_version = "v2"
    assert not verify(p)


def test_tampered_prediction_fails_verification(tmp_path):
    session = _session(tmp_path)
    p = publish(session, analysis=ANALYSIS, report="r", meta=META)
    assert verify(p)
    p.side = "under"
    assert not verify(p)


def test_old_predictions_without_version_still_verify(tmp_path):
    # Las del 21-oct se publicaron sin versión: su hash no la incluye y debe seguir cuadrando.
    session = _session(tmp_path)
    p = publish(session, analysis=ANALYSIS, report="r", meta=META)
    session.expire_all()
    p = session.get(Prediction, p.id)
    assert p.model_version is None
    assert p.published_at.tzinfo is None or p.published_at.tzinfo == timezone.utc
    assert verify(p)


def test_summary_separates_model_versions(tmp_path):
    session = _session(tmp_path)
    old = publish(session, analysis=ANALYSIS, report="r", meta=META)
    new = publish(session, analysis=ANALYSIS, report="r", meta={**META, "model_version": "v1"})
    old.status, new.status = "lost", "won"
    s = summary([old, new])
    assert s["overall"]["settled"] == 2
    assert s["by_version"][OLD_VERSION]["lost"] == 1
    assert s["by_version"]["v1"]["won"] == 1
    assert datetime.now(timezone.utc) >= new.published_at
