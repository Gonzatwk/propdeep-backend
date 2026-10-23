"""Nota de 0 a 100 de una línea (propdeep/nota.py)."""
from propdeep.nota import nota


def _analysis(**kw) -> dict:
    a = {
        "player": "Luka Doncic", "stat": "pts", "line": 27.5, "reasons": [],
        "estimate": {"prob_over": 0.55, "fair_over": 0.53},
        "books": [{"bookmaker": "bk", "line": 27.5, "over_odds": 1.9, "under_odds": 1.9}],
        "trends": {"games": 30, "season_games": 12, "hit_rate_last10": 0.7, "hit_rate_season": 0.6,
                   "recent_values": [30.0] * 10, "last10": 29.4, "minutes_last5": 36.0, "minutes_season": 35.0,
                   "splits": {"home": {"games": 6, "avg": 31.0, "hit_rate": 0.67},
                              "away": {"games": 6, "avg": 26.0, "hit_rate": 0.33},
                              "vs_opponent": {"games": 2, "avg": 33.0, "hit_rate": 1.0}}},
        "context": {"home": True, "opponent": "Los Angeles Lakers", "opponent_factor": 1.04},
    }
    a.update(kw)
    return a


def test_side_follows_the_estimate_never_against_it():
    over = nota(_analysis())
    assert over.side == "over" and over.prob == 0.55 and over.fair == 0.53
    under = nota(_analysis(estimate={"prob_over": 0.48, "fair_over": 0.50}))
    assert under.side == "under" and under.prob == 0.52 and under.fair == 0.5


def test_no_nota_without_estimate_or_with_a_block():
    assert nota(_analysis(estimate=None)) is None
    assert nota(_analysis(reasons=["Menos de 5 partidos con minutos: muestra insuficiente."])) is None


def test_score_rises_with_the_data_supporting_the_side():
    strong = nota(_analysis())
    weak_trends = {**_analysis()["trends"], "hit_rate_last10": 0.4, "hit_rate_season": 0.4}
    weak = nota(_analysis(trends=weak_trends))
    assert 0 <= weak.score < strong.score <= 100
    assert strong.parts["forma"] > weak.parts["forma"] == 0.0


def test_under_reads_hit_rates_the_other_way():
    a = _analysis(estimate={"prob_over": 0.47, "fair_over": 0.5})
    a["trends"] = {**a["trends"], "hit_rate_last10": 0.2, "hit_rate_season": 0.3}
    n = nota(a)
    assert n.side == "under" and n.parts["forma"] > 0.5
    assert n.reasons[0] == "Se quedó por debajo de 27,5 en 8 de sus últimos 10 partidos."


def test_reasons_are_short_spanish_sentences():
    n = nota(_analysis())
    assert n.reasons == [
        "Superó 27,5 en 7 de sus últimos 10 partidos.",
        "Media de 29,4 puntos en los últimos 10.",
        "En casa, 31 de media en 6 partidos.",
    ]
