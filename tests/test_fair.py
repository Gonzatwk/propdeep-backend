"""Precio justo, probabilidad calibrada y distribución anclada (propdeep/fair.py)."""
import pytest

from propdeep import fair
from propdeep.model import devig, prob_over

BOOKS = [
    {"bookmaker": "dk", "line": 22.5, "over_odds": 1.90, "under_odds": 1.90},
    {"bookmaker": "fd", "line": 22.5, "over_odds": 2.00, "under_odds": 1.80},
    {"bookmaker": "pinnacle", "line": 22.5, "over_odds": 1.95, "under_odds": 1.91},
    {"bookmaker": "bovada", "line": 23.5, "over_odds": 2.10, "under_odds": 1.70},
]


def test_fair_price_is_the_no_vig_mean_of_books_on_that_line():
    f = fair.fair_price(BOOKS, 22.5)
    expected = (devig(1.9, 1.9) + devig(2.0, 1.8) + devig(1.95, 1.91)) / 3
    assert f.books == 3 and f.prob_over == pytest.approx(expected, abs=1e-4)
    assert f.pinnacle == pytest.approx(devig(1.95, 1.91), abs=1e-4)
    assert fair.fair_price(BOOKS, 24.5) is None


def test_calibration_starts_from_the_market_and_tilts_a_little_to_the_model():
    c = fair.Calibration(alpha=0.0, beta=0.1, source="test")
    assert c.prob_over(0.5, 0.5) == pytest.approx(0.5)
    tilted = c.prob_over(0.5, 0.8)
    assert 0.5 < tilted < 0.55  # el modelo dice 80 %, pero solo mueve unos puntos
    assert fair.Calibration(alpha=-0.1, beta=0.0, source="t").prob_over(0.5, 0.9) < 0.5  # alpha: sesgo al menos


def test_anchored_distribution_reproduces_the_main_line_probability():
    mu = fair.anchored_mean("pts", 6.0, 22.5, 0.47)
    assert prob_over("pts", mu, 6.0 * fair.SD_INFLATION, 22.5) == pytest.approx(0.47, abs=1e-3)
    assert fair.prob_threshold("pts", mu, 6.0, 22.5) == pytest.approx(0.47, abs=1e-3)
    # Umbrales más bajos, más probables; "20+" es lo mismo que "más de 19,5".
    assert fair.prob_threshold("pts", mu, 6.0, 19.5) > 0.47 > fair.prob_threshold("pts", mu, 6.0, 25.5)
    assert fair.prob_threshold("pts", mu, 6.0, 20) == pytest.approx(fair.prob_threshold("pts", mu, 6.0, 20.5))


def test_estimate_uses_all_books_and_falls_back_to_the_main_book():
    e = fair.estimate("pts", 22.5, 0.62, 0.5, 6.0, BOOKS)
    assert e["fair_books"] == 3 and e["pinnacle_over"] is not None
    assert abs(e["prob_over"] - e["fair_over"]) < 0.03  # la estimación se queda cerca del mercado
    assert e["calibration"] == fair.CALIBRATION.source
    alone = fair.estimate("pts", 30.5, 0.62, 0.48, 6.0, BOOKS)
    assert alone["fair_books"] == 1 and alone["fair_over"] == 0.48


def test_published_lines_keep_their_estimate_but_do_not_show_it_yet(api):
    import main
    from propdeep.db import Prediction

    api.c.post("/admin/board?game_date=2026-11-20", headers={"x-admin-token": "secreto"})
    with main.session_factory()() as s:
        p = s.query(Prediction).filter_by(stat="pts").first()
        e = p.analysis["estimate"]
    assert e["fair_books"] == 2 and 0 < e["prob_over"] < 1 and e["anchored_mean"] > 0
    # Hasta el feed (bloque 2) la estimación no sale de la API pública.
    assert "estimate" not in api.c.get(f"/board/lines/{p.id}").text
