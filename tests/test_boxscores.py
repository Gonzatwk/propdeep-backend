"""Boxscores guardados: solo partidos terminados, sin duplicados y sin información futura."""
from datetime import date

from propdeep import boxscores
from propdeep.db import make_session_factory
from tests.fakes import FakeBDL

DAY = date(2026, 11, 20)


def row(game_id, player_id, team_id, pts=20, mins="30", status="Final", day="2026-11-18", home=1, visitor=2,
        position="G"):
    return {"min": mins, "pts": pts, "reb": 5, "ast": 4, "fg3m": 2, "fga": 15, "fta": 4, "oreb": 1, "turnover": 2,
            "player": {"id": player_id, "first_name": "Ju", "last_name": f"Gador{player_id}", "position": position},
            "team": {"id": team_id},
            "game": {"id": game_id, "date": day, "season": 2026, "status": status, "postseason": False,
                     "home_team_id": home, "visitor_team_id": visitor}}


def _session(tmp_path):
    return make_session_factory(f"sqlite:///{tmp_path}/t.db")()


def test_only_finished_games_and_players_with_minutes(tmp_path):
    s = _session(tmp_path)
    rows = [row(1, 10, 1), row(1, 11, 2), row(1, 12, 1, mins="0"), row(2, 13, 1, status="3rd Qtr")]
    assert boxscores.store(s, rows) == 2
    b = {x.player_id: x for x in s.query(boxscores.BoxScore)}
    assert b[10].home and b[10].opponent_id == 2
    assert not b[11].home and b[11].opponent_id == 1
    assert b[10].tov == 2 and b[10].position == "G"


def test_storing_twice_does_not_duplicate(tmp_path):
    s = _session(tmp_path)
    assert boxscores.store(s, [row(1, 10, 1)]) == 1
    assert boxscores.store(s, [row(1, 10, 1), row(1, 11, 2)]) == 1
    assert s.query(boxscores.BoxScore).count() == 2


def test_sync_fills_missing_days_and_then_only_rechecks_the_last_ones(tmp_path):
    s = _session(tmp_path)
    bdl = FakeBDL([30.0] * 5, DAY)
    asked = []
    bdl.stats_on = lambda d: asked.append(d) or ([row(int(d.strftime("%m%d")), 10, 1, day=d.isoformat())]
                                                 if d.day % 2 else [])
    boxscores.sync(s, bdl, 2026, DAY, start=date(2026, 11, 10))
    assert asked[0] == date(2026, 11, 10) and asked[-1] == date(2026, 11, 19)  # hasta ayer
    asked.clear()
    boxscores.sync(s, bdl, 2026, DAY)
    assert asked == [date(2026, 11, 17), date(2026, 11, 18), date(2026, 11, 19)]


def test_rows_between_never_includes_the_day_or_later(tmp_path):
    s = _session(tmp_path)
    boxscores.store(s, [row(1, 10, 1, day="2026-11-18"), row(2, 10, 1, day="2026-11-20")])
    assert [b.game_date for b in boxscores.rows_between(s, 2026, "2026-11-20")] == ["2026-11-18"]
