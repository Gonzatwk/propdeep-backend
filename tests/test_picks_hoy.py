from types import SimpleNamespace

from scripts.picks_hoy import best_at_line, evaluate

BOOKS = [
    {"bookmaker": "a", "line": 20.5, "over_odds": 1.85, "under_odds": 1.95},
    {"bookmaker": "b", "line": 20.5, "over_odds": 1.95, "under_odds": 1.85},
    {"bookmaker": "c", "line": 21.5, "over_odds": 2.30, "under_odds": 1.60},
]


def _prop():
    return SimpleNamespace(line=20.5, away_team="X", home_team="Y", commence_time="2026-10-21T23:30:00Z")


def _analysis(p, reasons=()):
    return SimpleNamespace(prob_over_final=p, prob_over_model=p, prob_over_market=0.5, projection=22.0,
                           player="Jugador", stat="pts", reasons=list(reasons))


def test_best_at_line_only_same_line():
    (o, ob), (u, ub) = best_at_line(BOOKS, 20.5, None)
    assert (o, ob, u, ub) == (1.95, "b", 1.95, "a")
    (o, ob), _ = best_at_line(BOOKS, 20.5, {"a"})
    assert (o, ob) == (1.85, "a")


def test_evaluate_uses_best_price():
    r = evaluate(_analysis(0.55), {"books": BOOKS}, _prop(), 0.03, None)
    assert r["lado"] == "más" and r["casa"] == "b" and r["jugada"] == "SÍ"
    assert r["ventaja_pp"] == round((0.55 - 1 / 1.95) * 100, 1)


def test_evaluate_blocked_or_small_edge():
    assert evaluate(_analysis(0.55, ["Out"]), {"books": BOOKS}, _prop(), 0.03, None)["jugada"] == ""
    assert evaluate(_analysis(0.51), {"books": BOOKS}, _prop(), 0.03, None)["jugada"] == ""
