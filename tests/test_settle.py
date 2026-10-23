"""Liquidación: casos que no deben anular apuestas de más ni quedarse pendientes para siempre."""
from datetime import date, datetime, timedelta, timezone

from propdeep.db import make_session_factory, publish
from propdeep.track_record import settle
from tests.fakes import FakeBDL, stat_row

DAY = date(2026, 11, 20)
NEXT_DAY = datetime(2026, 11, 21, 10, tzinfo=timezone.utc)
ANALYSIS = {"player": "Luka Doncic", "stat": "pts", "line": 27.5, "side": "over", "prob_over_final": 0.56,
            "odds_taken": 1.9, "edge": 0.034, "confidence": "baja"}


def _setup(tmp_path, game_id=999, game_date=DAY):
    session = make_session_factory(f"sqlite:///{tmp_path}/t.db")()
    bdl = FakeBDL([30.0] * 10, DAY)
    p = publish(session, analysis=ANALYSIS, report="r",
                meta={"game_date": game_date.isoformat(), "game_id": game_id, "player_id": 132})
    return session, bdl, p


def test_final_game_without_box_score_waits(tmp_path):
    session, bdl, p = _setup(tmp_path)
    bdl.final_stats[999] = []  # "Final" pero el boxscore aún no está
    assert settle(session, bdl, now=NEXT_DAY) == []
    assert p.status == "pending"
    bdl.final_stats[999] = [stat_row(DAY, 31.0, game_id=999)]
    assert [x.status for x in settle(session, bdl, now=NEXT_DAY)] == ["won"]


def test_postponed_game_is_void(tmp_path):
    session, bdl, p = _setup(tmp_path)
    bdl.statuses[999] = "Postponed"
    settle(session, bdl, now=NEXT_DAY)
    assert p.status == "void" and p.actual is None


def test_game_not_played_after_some_days_is_void(tmp_path):
    session, bdl, p = _setup(tmp_path)
    settle(session, bdl, now=NEXT_DAY)
    assert p.status == "pending"  # al día siguiente aún se espera
    settle(session, bdl, now=NEXT_DAY + timedelta(days=4))
    assert p.status == "void"


def test_prediction_without_game_is_voided_after_its_day(tmp_path):
    session, bdl, p = _setup(tmp_path, game_id=None)
    settle(session, bdl, now=NEXT_DAY)
    assert p.status == "pending"
    settle(session, bdl, now=NEXT_DAY + timedelta(days=3))
    assert p.status == "void"


def test_one_failing_game_does_not_block_the_rest(tmp_path):
    session, bdl, broken = _setup(tmp_path, game_id=555)
    ok = publish(session, analysis=ANALYSIS, report="r",
                 meta={"game_date": DAY.isoformat(), "game_id": 999, "player_id": 132})
    bdl.final_stats[999] = [stat_row(DAY, 20.0, game_id=999)]
    real_game = bdl.game

    def game(game_id):
        if game_id == 555:
            raise RuntimeError("Balldontlie caído")
        return real_game(game_id)

    bdl.game = game
    settle(session, bdl, now=NEXT_DAY)
    assert ok.status == "lost" and broken.status == "pending"


def test_box_score_rows_without_player_do_not_crash(tmp_path):
    session, bdl, p = _setup(tmp_path)
    bdl.final_stats[999] = [{"min": "30", "pts": 10}, stat_row(DAY, 31.0, game_id=999)]
    settle(session, bdl, now=NEXT_DAY)
    assert p.status == "won"
