import random
from datetime import date, timedelta

import pytest

from propdeep.clients.odds import PropLine
from scripts.backtest import (
    Candidate, Game, Row, Season, evaluate, main_lines, proxy_candidates, strip_suffix, summarize,
)

START = date(2025, 10, 22)


def synthetic_season(seed=1, n_days=60):
    """Dos equipos que juegan cada dos días; jugadores con media fija y ruido."""
    rng = random.Random(seed)
    players = {pid: (team, rng.uniform(8, 30)) for pid, team in
               [(i, 1 if i < 5 else 2) for i in range(10)]}
    rows, games = [], []
    for k in range(n_days // 2):
        day = (START + timedelta(days=2 * k)).isoformat()
        gid = 1000 + k
        games.append(Game(gid, day, 2025, 1, 2, "Home", "Away", 110, 105))
        for pid, (team, mu) in players.items():
            pts = max(0.0, round(rng.gauss(mu, 6)))
            rows.append(Row(pid, f"Jugador {pid}", team, gid, day, 2025, 32.0,
                            {"pts": pts, "reb": 5.0, "ast": 4.0, "fg3m": 2.0}))
    return Season(rows, games, 2025)


def test_history_never_includes_the_game_or_later():
    season = synthetic_season()
    day = (START + timedelta(days=20)).isoformat()
    hist = season.history(3, day)
    assert hist and all(r.day < day for r in hist)


def test_future_games_do_not_change_the_analysis():
    season = synthetic_season()
    target = next(r for r in season.rows if r.player_id == 2 and r.day == (START + timedelta(days=30)).isoformat())
    cand = Candidate(target, "pts", 18.5, 1.90, 1.90, "x")
    before = evaluate(season, [cand], 0.03, 0.5)[0].analysis

    # Cambiamos todo lo que pasa después (y el propio partido): el análisis no debe moverse.
    tampered = [Row(r.player_id, r.player_name, r.team_id, r.game_id, r.day, r.season, r.minutes,
                    {**r.stats, "pts": 99.0}) if r.day >= target.day else r for r in season.rows]
    season2 = Season(tampered, season.games, 2025)
    target2 = next(r for r in season2.rows if r.player_id == 2 and r.day == target.day)
    after = evaluate(season2, [Candidate(target2, "pts", 18.5, 1.90, 1.90, "x")], 0.03, 0.5)[0].analysis
    assert after.prob_over_final == before.prob_over_final
    assert after.side == before.side


def test_settlement_and_roi():
    season = synthetic_season()
    row = season.rows[-1]
    row.stats["pts"] = 40.0
    res = evaluate(season, [Candidate(row, "pts", 5.5, 2.0, 2.0, "x")], 0.03, 0.5)[0]
    assert res.analysis.side == "over"
    assert res.profit == pytest.approx(1.0)
    s = summarize([res])
    assert s["picks"]["n"] == 1 and s["picks"]["roi"] == pytest.approx(1.0)


def test_proxy_lines_use_only_previous_games():
    season = synthetic_season()
    cands = proxy_candidates(season, "0000", "9999", ["pts"])
    assert cands and all(c.line % 1 == 0.5 for c in cands)
    # Solo a partir del 6.º partido (hacen falta 5 previos).
    first_day = min(c.row.day for c in cands)
    assert first_day == (START + timedelta(days=10)).isoformat()


def test_random_noise_has_no_edge_against_fair_line():
    """Con línea justa (la media real) y ruido puro, el modelo no debe "encontrar" dinero."""
    season = synthetic_season(seed=3, n_days=160)
    means = {}
    for r in season.rows:
        means.setdefault(r.player_id, []).append(r.stats["pts"])
    cands = [Candidate(r, "pts", round(sum(means[r.player_id]) / len(means[r.player_id])) + 0.5, 1.87, 1.87, "x")
             for r in season.rows if r.day >= (START + timedelta(days=20)).isoformat()]
    s = summarize(evaluate(season, cands, 0.03, 0.5))
    if s["picks"]["n"]:
        assert s["picks"]["roi_ic95"][0] < 0.05


def test_main_line_and_names():
    def p(line, o, u):
        return PropLine("e", "t", "h", "a", "Jaren Jackson Jr.", "player_points", line, o, u, "b")

    lines = main_lines([p(20.5, 1.5, 2.6), p(22.5, 1.9, 1.9), p(24.5, 2.5, 1.5)])
    assert len(lines) == 1 and lines[0].line == 22.5
    assert strip_suffix("Jaren Jackson Jr.") == strip_suffix("Jaren Jackson")


def test_odds_history_uses_cache_and_respects_budget(tmp_path):
    import httpx

    from scripts.backtest import OddsHistory

    season = synthetic_season()
    day = (START + timedelta(days=20)).isoformat()
    calls = []

    def handler(request):
        calls.append(request.url.path)
        if request.url.path.endswith("/events"):
            return httpx.Response(200, json={"data": [{"id": "ev1", "commence_time": f"{day}T23:30:00Z"}]},
                                  headers={"x-requests-last": "1"})
        book = {"key": "dk", "markets": [{"key": "player_points", "outcomes": [
            {"name": "Over", "description": "Jugador 2", "point": 15.5, "price": 1.9},
            {"name": "Under", "description": "Jugador 2", "point": 15.5, "price": 1.9}]}]}
        return httpx.Response(200, json={"data": {"id": "ev1", "commence_time": f"{day}T23:30:00Z",
                                                  "home_team": "Home", "away_team": "Away",
                                                  "bookmakers": [book]}},
                              headers={"x-requests-last": "10"})

    def make(budget):
        h = OddsHistory("k", tmp_path, "us", ["player_points"], budget)
        h.http = httpx.Client(base_url="https://x", transport=httpx.MockTransport(handler))
        return h

    cands, complete = make(5).candidates(season, [day], ["pts"])
    assert not complete and cands == []  # el tope corta antes de pagar las props

    h = make(100)
    cands, complete = h.candidates(season, [day], ["pts"])
    assert complete and h.spent == 10  # la lista de partidos ya estaba en caché
    assert len(cands) == 1 and cands[0].row.player_id == 2 and cands[0].line == 15.5

    n = len(calls)
    h2 = make(100)
    assert h2.candidates(season, [day], ["pts"])[0] and h2.spent == 0 and len(calls) == n


def test_bdl_fetcher_retries_timeouts_and_resumes(tmp_path, monkeypatch):
    import httpx

    import scripts.backtest as bt

    monkeypatch.setattr(bt.time, "sleep", lambda _s: None)
    state = {"timeouts": 2, "stats_calls": 0}
    games = [{"id": 1, "date": "2025-10-21"}, {"id": 2, "date": "2025-11-02"}]

    def handler(request):
        if request.url.path.endswith("/games"):
            return httpx.Response(200, json={"data": games, "meta": {}})
        if state["timeouts"]:
            state["timeouts"] -= 1
            raise httpx.ReadTimeout("lento", request=request)
        state["stats_calls"] += 1
        return httpx.Response(200, json={"data": [{"week": request.url.params["start_date"]}], "meta": {}})

    def make():
        f = bt.BdlFetcher("k", tmp_path)
        f.http = httpx.Client(base_url="https://x", transport=httpx.MockTransport(handler))
        return f

    stats, _ = make().season(2025)
    assert [s["week"] for s in stats] == ["2025-10-21", "2025-10-28"]
    calls = state["stats_calls"]
    make().season(2025)  # segunda vez: todo de la caché
    assert state["stats_calls"] == calls
