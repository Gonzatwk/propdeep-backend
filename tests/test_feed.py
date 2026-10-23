"""Feed de mejores jugadas: tarjetas guardadas al publicar, muro de pago y liquidación."""
import main
from propdeep import feed
from propdeep.db import content_hash
from tests.fakes import stat_row
from tests.test_board import ADMIN, DAY


def _publish(api, monkeypatch, min_score=0):
    monkeypatch.setattr(feed, "FEED_MIN_SCORE", min_score)
    api.c.post(f"/admin/board?game_date={DAY}", headers=ADMIN)
    with main.session_factory()() as s:
        return s.query(feed.FeedCard).all()


def test_cards_are_saved_once_with_their_hash(api, monkeypatch):
    cards = _publish(api, monkeypatch)
    assert cards and all(c.status == "pending" and c.side in ("over", "under") for c in cards)
    c = cards[0]
    record = {"prediction_id": c.prediction_id, "game_date": c.game_date, "player_id": c.player_id,
              "player_name": c.player_name, "stat": c.stat, "line": c.line, "side": c.side,
              "score": c.score, "prob": c.prob, "nota_version": c.nota_version}
    published = c.published_at.replace(tzinfo=None).isoformat() + "+00:00"
    assert content_hash({**record, "published_at": published}) == c.content_hash
    # Volver a publicar la jornada no duplica tarjetas.
    assert len(_publish(api, monkeypatch)) == len(cards)


def test_only_lines_above_the_minimum_score_make_the_feed(api, monkeypatch):
    assert _publish(api, monkeypatch, min_score=101) == []


def test_feed_hides_side_and_player_of_locked_cards(api, monkeypatch):
    _publish(api, monkeypatch)
    r = api.c.get(f"/feed?game_date={DAY}").json()
    assert "no son una recomendación" in r["disclaimer"]
    free = [c for c in r["cards"] if not c["locked"]]
    locked = [c for c in r["cards"] if c["locked"]]
    assert free and locked
    assert all({"player", "side", "prob", "reasons"} <= c.keys() for c in free)
    assert all(not ({"player", "side", "prob", "line", "reasons"} & c.keys()) for c in locked)
    # Con suscripción se ve todo.
    monkeypatch.setattr(main, "_sees_all", lambda user: True)
    assert not any(c["locked"] for c in api.c.get(f"/feed?game_date={DAY}").json()["cards"])


def test_cards_settle_with_the_games_and_feed_the_history(api, monkeypatch):
    cards = _publish(api, monkeypatch)
    main.bdl_client().final_stats[999] = [stat_row(DAY, 31.0, game_id=999)]
    api.c.post("/admin/settle", headers=ADMIN)
    with main.session_factory()() as s:
        settled = [c for c in s.query(feed.FeedCard).all() if c.status in ("won", "lost")]
    assert len(settled) == len(cards)
    h = api.c.get(f"/feed?game_date={DAY}").json()["history"]
    assert h["settled"] == len(cards) and h["won"] + h["lost"] == len(cards) and 0 < h["avg_prob"] < 1


def test_sides_below_fifty_percent_do_not_make_the_feed(api, monkeypatch):
    # Sin cuotas en pantalla, una "mejor jugada" con menos del 50 % confundiría.
    cards = _publish(api, monkeypatch)
    assert cards and all(c.prob >= feed.FEED_MIN_PROB for c in cards)
    monkeypatch.setattr(feed, "FEED_MIN_PROB", 1.0)
    with main.session_factory()() as s:
        s.query(feed.FeedCard).delete()
        s.query(main.Prediction).delete()
        s.commit()
    assert _publish(api, monkeypatch) == []
