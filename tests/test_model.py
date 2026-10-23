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


def test_minutes_adjustment_is_capped_and_ignores_last_season():
    # 1 partido esta temporada con 3 minutos y 4 de la anterior con 30: antes daba más de 50 puntos.
    values = [2.0, 20.0, 22.0, 18.0, 21.0]
    mins = [3.0, 30.0, 30.0, 30.0, 30.0]
    t = compute_trends(values, mins, 11.5, season_games=1)
    assert t.minutes_last5 is None
    from propdeep.model import project

    assert project("pts", t, Context()) < 20

    # Con temporada suficiente, un salto de minutos sube la proyección como mucho un 15 %.
    values = [20.0] * 10
    mins = [40.0] * 5 + [10.0] * 5
    t = compute_trends(values, mins, 19.5, season_games=10)
    assert project("pts", t, Context()) == pytest.approx(20.0 * 1.15)


def test_prob_over_accounts_for_right_skew():
    # Proyección 20 con mucha dispersión: pasar de 19,5 es algo menos probable que el 50 % de la normal.
    assert prob_over("pts", 20.0, 8.0, 19.5) < 0.5
    assert prob_over("reb", 8.0, 3.0, 7.5) == pytest.approx(prob_over("reb", 8.0, 3.0, 7.0))
    assert 0 < prob_over("ast", 2.0, 1.0, 1.5) < 1


def test_hit_rates_and_last_season():
    from propdeep.model import compute_splits

    values = [30.0, 20.0, 30.0, 20.0, 30.0, 10.0, 10.0, 10.0, 10.0, 10.0, 40.0, 40.0]
    t = compute_trends(values, [34.0] * len(values), 25.5, season_games=10, last_season_games=2)
    assert t.hit_rate_last5 == 0.6 and t.hit_rate_last10 == 0.3 and t.hit_rate_season == 0.3
    assert t.hit_rate_last_season == 1.0 and t.last_season_games == 2

    s = compute_splits([30.0, 20.0, 10.0], [True, False, True], [14, 3, 14], 25.5, opponent_id=14)
    assert s["home"] == {"games": 2, "avg": 20.0, "hit_rate": 0.5}
    assert s["away"]["games"] == 1 and s["vs_opponent"]["games"] == 2
    assert compute_splits([30.0], [None], [None], 25.5, None)["vs_opponent"]["games"] == 0


def test_side_of_reads_home_and_opponent():
    from propdeep.pipeline import _side_of

    row = {"team": {"id": 7}, "game": {"home_team_id": 7, "visitor_team_id": 14}}
    assert _side_of(row) == (True, 14)
    assert _side_of({"team": {"id": 14}, "game": {"home_team_id": 7, "visitor_team_id": 14}}) == (False, 7)
    assert _side_of({"team": {"id": 7}, "game": {}}) == (None, None)


def test_main_line_is_the_one_most_books_offer():
    from propdeep.clients.odds import PropLine, main_lines

    mk = lambda line, o, u, book: PropLine("ev1", "", "", "", "Luka Doncic", "player_points", line, o, u, book)
    rows = [mk(28.5, 1.9, 1.9, "a"), mk(28.5, 1.85, 1.95, "b"), mk(27.5, 1.7, 2.1, "c")]
    [(main, books)] = main_lines(rows)
    assert main.line == 28.5 and main.bookmaker == "a" and len(books) == 3


def test_traded_player_uses_event_game_and_is_not_a_pick():
    """Historial con su equipo anterior (TEAM) pero esta noche juega con otro: partido, rival y pista
    salen del partido de la casa, y sin jugada hasta 5 partidos con el equipo nuevo."""
    from tests.fakes import OPP, PLAYER, TEAM
    new = {"id": 30, "full_name": "Miami Heat"}

    class Traded(FakeBDL):
        def find_player(self, name):
            return {**PLAYER, "team": new}

        def games_on(self, day):
            return [{"id": 998, "date": day.isoformat(), "home_team": TEAM, "visitor_team": {"id": 40, "full_name": "X"}},
                    {"id": 999, "date": day.isoformat(), "home_team": OPP, "visitor_team": new}]

    an = Analyzer(Traded([25.0] * 20, DAY), 2026, 0.03, 0.5)
    result, meta = an.analyze_prop("Luka Doncic", "pts", 15.5, 1.9, 1.9, DAY,
                                   event_teams=("Los Angeles Lakers", "Miami Heat"))
    assert meta["game_id"] == 999 and meta["team_id"] == 30
    assert result.context.opponent == "Los Angeles Lakers" and result.context.home is False
    assert result.context.traded and result.side is None
    assert "cambiado de equipo" in result.reasons[0]


def test_no_pick_before_three_games_this_season():
    values = [30.0] * 20
    t = compute_trends(values, [36.0] * 20, 20.5, season_games=2, last_season_games=18)
    a = analyze("X", "pts", 20.5, 1.90, 1.90, t, Context())
    assert a.side is None and "partidos esta temporada" in a.reasons[0]


def test_teammate_out_factor_shrinks_and_caps():
    from propdeep.model import teammate_out_factor
    values = [20.0] * 10 + [30.0] * 3
    ids = list(range(13))
    days = [f"2026-01-{i + 1:02d}" for i in range(13)]
    absent = {"Estrella": (set(range(10)), "2026-01-01")}
    f, det = teammate_out_factor(values, ids, days, [1] * 13, 1, absent)
    # ratio 1,5 encogido con 3 partidos sin él: 1 + 0,5 * 3/11
    assert f == pytest.approx(1 + 0.5 * 3 / 11, abs=1e-3)
    assert det[0]["games_without"] == 3 and det[0]["games_with"] == 10
    # con otro equipo no cuenta, y con poca muestra el factor es 1
    assert teammate_out_factor(values, ids, days, [2] * 13, 1, absent)[0] == 1.0


def test_analyzer_adjusts_for_injured_key_teammate():
    from tests.fakes import TEAM, stat_row

    star = {"id": 500, "first_name": "Kyrie", "last_name": "Irving", "team": TEAM}
    # Luka: 20 partidos; mete 35 en los 4 que no jugó Kyrie y 25 en el resto.
    base = FakeBDL([25.0] * 20, DAY)
    luka_rows = base.rows
    for r in luka_rows[2:16:4]:
        r["pts"] = 35.0
    star_rows = [{**r, "player": {"id": 500}, "pts": 22} for i, r in enumerate(luka_rows) if i not in (2, 6, 10, 14)]

    class WithInjury(FakeBDL):
        def player_stats(self, player_id, seasons):
            rows = star_rows if player_id == 500 else luka_rows
            return sorted(rows, key=lambda r: r["game"]["date"], reverse=True)

        def _get_all(self, path, params, limit=500):
            if path == "/player_injuries":
                return [{"player": star, "status": "Out"}]
            return []

        def team_games(self, team_id, season):
            return [{**r["game"], "status": "Final", "home_team_score": 100} for r in luka_rows[-5:]]

    bdl = WithInjury([25.0] * 20, DAY)
    bdl.rows = luka_rows
    an = Analyzer(bdl, 2026, 0.03, 0.2, teammate_adjust=True)
    result, _ = an.analyze_prop("Luka Doncic", "pts", 26.5, 1.9, 1.9, DAY)
    ctx = result.context
    assert ctx.teammates_out and ctx.teammates_out[0]["teammate"] == "Kyrie Irving"
    assert ctx.teammates_out[0]["games_without"] == 4 and ctx.teammate_factor > 1.1
    # Apagado: se ve el desglose, pero la proyección no cambia.
    off, _ = Analyzer(bdl, 2026, 0.03, 0.2, teammate_adjust=False).analyze_prop("Luka Doncic", "pts", 26.5, 1.9, 1.9, DAY)
    assert off.context.teammates_out and off.context.teammate_factor == 1.0
    assert off.projection < result.projection


def test_broken_odds_entries_are_skipped_not_fatal():
    from propdeep.clients.odds import parse_all_props

    payload = {"id": "e", "bookmakers": [
        {"markets": [{"key": "player_points", "outcomes": []}]},  # casa sin nombre
        {"key": "bk", "markets": [{"key": "player_points", "outcomes": [
            {"name": "Over", "description": "Luka Doncic", "point": 27.5, "price": 1.9},
            {"name": "Under", "description": "Luka Doncic", "point": 27.5, "price": 1.9},
            {"name": "Over", "description": "Sin Cuota", "point": 10.5},
            {"name": "Under", "description": "Sin Cuota", "point": 10.5, "price": "n/a"},
            {"name": "Over", "point": 5.5, "price": 1.9},  # sin jugador
        ]}]},
    ]}
    props = parse_all_props(payload)
    assert [(p.player, p.line) for p in props] == [("Luka Doncic", 27.5)]


def test_scan_day_survives_an_unexpected_error_on_one_prop():
    from datetime import date

    from propdeep.clients.odds import PropLine
    from propdeep.pipeline import scan_day

    class Odds:
        def events_on(self, day):
            return [{"id": "e1"}]

        def player_props(self, event):
            mk = lambda name: PropLine("e1", "t", "h", "a", name, "player_points", 20.5, 1.9, 1.9, "bk")  # noqa: E731
            return [mk("Raro"), mk("Bueno")]

    class Analyzer:
        def analyze_prop(self, player, *args, **kwargs):
            if player == "Raro":
                raise TypeError("dato inesperado")
            return type("A", (), {"edge": 0.0})(), {}

    results = scan_day(Analyzer(), Odds(), date(2026, 11, 20))
    assert len(results) == 1 and results[0][2].player == "Bueno"


def test_half_point_lines_keep_their_probabilities():
    # Valores de antes de tratar las líneas enteras: en las líneas ,5 no debe cambiar nada.
    assert prob_over("pts", 25.0, 6.0, 24.5) == pytest.approx(0.5124344067898262, abs=1e-12)
    assert prob_over("reb", 7.2, 2.5, 7.5) == pytest.approx(0.4310587611178477, abs=1e-12)
    assert prob_over("fg3m", 2.1, 0.8, 2.5) == pytest.approx(0.3503686481179309, abs=1e-12)


def test_integer_lines_do_not_count_the_push_as_an_under():
    from propdeep.model import prob_push

    push = prob_push("reb", 8.0, 3.0, 8.0)
    assert push > 0.1  # con media 8, sacar exactamente 8 rebotes pasa a menudo
    assert prob_push("reb", 8.0, 3.0, 7.5) == 0.0
    # El análisis compara el más con el mercado sin empuje: P(más | no empuje).
    a = analyze("Luka Doncic", "reb", 8.0, 1.9, 1.9, compute_trends([8.0] * 20, [34.0] * 20, 8.0, 20),
                Context(), model_weight=1.0)
    o, p = prob_over("reb", a.projection, a.trends.sd, 8.0), prob_push("reb", a.projection, a.trends.sd, 8.0)
    assert a.prob_over_model == pytest.approx(o / (1 - p), abs=1e-4)
    assert a.prob_over_model > o  # sin repartir el empuje, el más salía infravalorado


def test_milestones_are_the_half_line_below():
    from propdeep.model import prob_at_least

    assert prob_at_least("pts", 25.0, 6.0, 25) == pytest.approx(prob_over("pts", 25.0, 6.0, 24.5))
    assert prob_at_least("pts", 25.0, 6.0, 20) > prob_at_least("pts", 25.0, 6.0, 25) > prob_at_least("pts", 25.0, 6.0, 30)
