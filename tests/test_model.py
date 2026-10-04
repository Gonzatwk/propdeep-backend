from datetime import date

import pytest

from propdeep.clients.balldontlie import minutes
from propdeep.clients.odds import parse_props
from propdeep.model import Context, analyze, compute_trends, devig, prob_over
from propdeep.pipeline import Analyzer
from tests.fakes import FakeBDL

DAY = date(2026, 11, 20)


def test_devig_removes_margin():
    p = devig(1.90, 1.90)
    assert p == pytest.approx(0.5)
    assert devig(1.70, 2.20) > 0.5


def test_minutes_formats():
    assert minutes("34") == 34
    assert minutes("34:30") == 34.5
    assert minutes("0:00") == 0
    assert minutes(None) == 0


def test_prob_over_monotonic_in_line():
    assert prob_over("pts", 28, 6, 25.5) > prob_over("pts", 28, 6, 30.5)
    # Triples con Poisson: media 3, línea 2.5 -> P(X>=3) ~ 0.577
    assert prob_over("fg3m", 3.0, 1.5, 2.5) == pytest.approx(0.5768, abs=1e-3)


def _trends(values, line):
    return compute_trends(values, [36.0] * len(values), line, season_games=len(values))


def test_no_edge_when_market_agrees():
    values = [28.0] * 20
    a = analyze("X", "pts", 27.5, 1.87, 1.95, _trends(values, 27.5), Context())
    # Mercado y modelo cerca: con margen de la casa no hay ventaja real.
    assert a.side is None
    assert a.confidence == "sin ventaja"


def test_clear_edge_on_over():
    values = [34.0, 33.0, 35.0, 32.0, 36.0] * 4
    a = analyze("X", "pts", 27.5, 1.90, 1.90, _trends(values, 27.5), Context())
    assert a.side == "over"
    assert a.edge >= 0.06
    assert a.confidence == "alta"
    assert a.expected_value > 0


def test_injured_player_is_never_a_pick():
    values = [34.0] * 20
    ctx = Context(injury_status="Out")
    a = analyze("X", "pts", 27.5, 1.90, 1.90, _trends(values, 27.5), ctx)
    assert a.side is None
    assert "lesión" in a.reasons[0]


def test_small_sample_is_never_a_pick():
    a = analyze("X", "pts", 20.5, 1.90, 1.90, _trends([30.0, 31.0, 29.0], 20.5), Context())
    assert a.side is None


def test_analyzer_ignores_games_on_or_after_game_day():
    bdl = FakeBDL([25.0] * 20, DAY)
    # Un partido "futuro" con 60 puntos no debe colarse en el análisis.
    from tests.fakes import stat_row
    bdl.rows.append(stat_row(DAY, 60.0))
    an = Analyzer(bdl, season=2026, min_edge=0.03, model_weight=0.5)
    result, meta = an.analyze_prop("Luka Doncic", "pts", 24.5, 1.9, 1.9, DAY)
    assert max(result.trends.recent_values) == 25.0
    assert meta["game_id"] == 999
    assert result.context.opponent == "Los Angeles Lakers"
    assert result.context.home is True


def test_unknown_player_raises():
    an = Analyzer(FakeBDL([25.0] * 20, DAY), 2026, 0.03, 0.5)
    with pytest.raises(LookupError):
        an.analyze_prop("Nadie", "pts", 24.5, 1.9, 1.9, DAY)


def test_parse_props_pairs_and_picks_lowest_margin():
    payload = {
        "id": "ev1", "home_team": "Dallas Mavericks", "away_team": "Los Angeles Lakers",
        "commence_time": "2026-11-21T01:30:00Z",
        "bookmakers": [
            {"key": "bookA", "markets": [{"key": "player_points", "outcomes": [
                {"name": "Over", "description": "Luka Doncic", "price": 1.80, "point": 28.5},
                {"name": "Under", "description": "Luka Doncic", "price": 1.85, "point": 28.5},
            ]}]},
            {"key": "bookB", "markets": [{"key": "player_points", "outcomes": [
                {"name": "Over", "description": "Luka Doncic", "price": 1.92, "point": 28.5},
                {"name": "Under", "description": "Luka Doncic", "price": 1.92, "point": 28.5},
                {"name": "Over", "description": "Solo Over", "price": 1.9, "point": 10.5},
            ]}]},
        ],
    }
    props = parse_props(payload)
    assert len(props) == 1
    assert props[0].bookmaker == "bookB"
    assert props[0].over_odds == 1.92
