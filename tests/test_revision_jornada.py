from types import SimpleNamespace

from scripts.revision_jornada import row_for, summarize


def _pred(stat="pts", line=20.5, side="over", proj=22.0):
    analysis = {
        "projection": proj, "prob_over_model": 0.6, "prob_over_market": 0.5, "prob_over_final": 0.52,
        "trends": {"season_games": 0, "minutes_season": 30.0, "minutes_last5": 32.0, "sd": 6.0},
        "context": {"home": True, "back_to_back": False, "opponent": "X"},
    }
    return SimpleNamespace(id=1, away_team="A", home_team="B", player_name="Jugador", stat=stat, line=line,
                           side=side, odds=1.9, bookmaker="b", edge=0.04, confidence="baja", status="won",
                           analysis=analysis)


BOX = {"pts": 25, "min": "36:30", "team": {"id": 1, "abbreviation": "BBB"},
       "game": {"home_team_id": 1, "home_team_score": 120, "visitor_team_score": 100}}


def test_row_for_uses_box_score():
    r = row_for(_pred(), BOX)
    assert r["real"] == 25 and r["min_reales"] == 36.5 and r["margen_final"] == 20
    assert r["min_esperados"] == 30.0  # sin partidos de esta temporada: minutos de la anterior


def test_row_for_without_box_and_summary(capsys):
    rows = [row_for(_pred(), BOX), row_for(_pred(line=30.5), BOX), row_for(_pred(), None)]
    summarize(rows)
    out = capsys.readouterr().out
    assert "2 con el jugador en pista" in out and "minutos explican" in out
