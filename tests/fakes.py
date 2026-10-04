"""Clientes falsos con la forma de las respuestas reales de Balldontlie."""
from datetime import date, timedelta

TEAM = {"id": 7, "full_name": "Dallas Mavericks"}
OPP = {"id": 14, "full_name": "Los Angeles Lakers"}
PLAYER = {"id": 132, "first_name": "Luka", "last_name": "Doncic", "team": TEAM}


def stat_row(day: date, pts: float, season: int = 2026, mins: str = "36", game_id: int | None = None,
             status: str = "Final"):
    return {
        "min": mins, "pts": pts, "reb": 9, "ast": 8, "fg3m": 3,
        "player": {"id": PLAYER["id"]}, "team": {"id": TEAM["id"]},
        "game": {"id": game_id or int(day.strftime("%Y%m%d")), "date": day.isoformat(),
                 "season": season, "status": status},
    }


class FakeBDL:
    def __init__(self, points: list[float], game_day: date, injury=None, b2b=False):
        start = game_day - timedelta(days=2 * len(points))
        # points: del más antiguo al más reciente
        self.rows = [stat_row(start + timedelta(days=2 * i), p) for i, p in enumerate(points)]
        self.game_day = game_day
        self._injury = injury
        self._b2b = b2b
        self.final_stats: dict[int, list[dict]] = {}

    def find_player(self, name):
        return PLAYER if "doncic" in name.lower() else None

    def player_stats(self, player_id, seasons):
        return sorted(self.rows, key=lambda r: r["game"]["date"], reverse=True)

    def games_on(self, day):
        return [{"id": 999, "date": day.isoformat(), "home_team": TEAM, "visitor_team": OPP}]

    def played_yesterday(self, team_id, day):
        return self._b2b

    def injury(self, player_id):
        return self._injury

    def team_games(self, team_id, season):
        return []

    def _get_all(self, path, params, limit=500):
        return []

    def game(self, game_id):
        return {"id": game_id, "status": "Final" if game_id in self.final_stats else "7:30 pm ET"}

    def game_stats(self, game_id):
        return self.final_stats.get(game_id, [])
