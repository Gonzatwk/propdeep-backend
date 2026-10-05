"""Une datos reales (Balldontlie + The Odds API) con el modelo y la redacción."""
from __future__ import annotations

from datetime import date
from typing import Callable
from statistics import mean

from .clients.balldontlie import BalldontlieClient, minutes
from .clients.odds import MARKETS, OddsClient, PropLine, book_rows, main_lines
from .model import Analysis, Context, analyze, compute_splits, compute_trends

MIN_OPPONENT_GAMES = 5


class Analyzer:
    def __init__(self, bdl: BalldontlieClient, season: int, min_edge: float, model_weight: float):
        self.bdl = bdl
        self.season = season
        self.min_edge = min_edge
        self.model_weight = model_weight
        self._league_ppg_cache: dict[int, float | None] = {}

    def analyze_prop(
        self,
        player_name: str,
        stat: str,
        line: float,
        over_odds: float,
        under_odds: float,
        game_day: date,
        opponent_name: str | None = None,
    ) -> tuple[Analysis, dict]:
        """Devuelve el análisis y los metadatos del partido (ids) para el historial."""
        if stat not in MARKETS.values():
            raise ValueError(f"Estadística no soportada: {stat}")
        player = self.bdl.find_player(player_name)
        if not player:
            raise LookupError(f"No encuentro al jugador '{player_name}' en Balldontlie")

        logs = self.bdl.player_stats(player["id"], [self.season, self.season - 1])
        # Solo partidos anteriores al del análisis: nunca usamos información futura.
        logs = [r for r in logs if r["game"]["date"][:10] < game_day.isoformat()]
        values = [float(r.get(stat) or 0) for r in logs]
        mins = [minutes(r.get("min")) for r in logs]
        season_games = sum(1 for r in logs if r["game"]["season"] == self.season)
        last_season_games = sum(1 for r in logs if r["game"]["season"] == self.season - 1)
        trends = compute_trends(values, mins, line, season_games, last_season_games)

        team_id = (logs[0]["team"]["id"] if logs else (player.get("team") or {}).get("id"))
        game = self._find_game(team_id, game_day)
        context = self._context(player, stat, team_id, game, game_day, opponent_name)
        opponent_id = None
        if game and team_id is not None:
            opponent_id = game["visitor_team"]["id"] if game["home_team"]["id"] == team_id else game["home_team"]["id"]
        home, opponents = zip(*(_side_of(r) for r in logs)) if logs else ((), ())
        trends.splits = compute_splits(values, list(home), list(opponents), line, opponent_id)

        full_name = f"{player['first_name']} {player['last_name']}"
        result = analyze(
            full_name, stat, line, over_odds, under_odds, trends, context,
            min_edge=self.min_edge, model_weight=self.model_weight,
        )
        meta = {
            "player_id": player["id"],
            "team_id": team_id,
            "game_id": game["id"] if game else None,
            "game_date": game_day.isoformat(),
        }
        return result, meta

    def _find_game(self, team_id: int | None, day: date) -> dict | None:
        if team_id is None:
            return None
        for game in self.bdl.games_on(day):
            if team_id in (game["home_team"]["id"], game["visitor_team"]["id"]):
                return game
        return None

    def _context(self, player, stat, team_id, game, day, opponent_name) -> Context:
        ctx = Context()
        injury = self.bdl.injury(player["id"])
        if injury:
            ctx.injury_status = injury.get("status")
            ctx.injury_note = injury.get("description")
        if not game or team_id is None:
            ctx.opponent = opponent_name
            return ctx
        home = game["home_team"]["id"] == team_id
        opponent = game["visitor_team"] if home else game["home_team"]
        ctx.home = home
        ctx.opponent = opponent.get("full_name") or opponent_name
        ctx.back_to_back = self.bdl.played_yesterday(team_id, day)
        if stat == "pts":
            ctx.opponent_factor = self._points_allowed_factor(opponent["id"], day)
        return ctx

    def _points_allowed_factor(self, team_id: int, day: date) -> float:
        games = [g for g in self.bdl.team_games(team_id, self.season)
                 if g["date"][:10] < day.isoformat() and _final(g)]
        league = self._league_ppg()
        if len(games) < MIN_OPPONENT_GAMES or not league:
            return 1.0
        allowed = mean(
            g["visitor_team_score"] if g["home_team"]["id"] == team_id else g["home_team_score"]
            for g in games
        )
        return round(allowed / league, 3)

    def _league_ppg(self) -> float | None:
        if self.season not in self._league_ppg_cache:
            games = [g for g in self.bdl._get_all("/games", {"seasons[]": self.season}, limit=1400)
                     if _final(g)]
            scores = [s for g in games for s in (g["home_team_score"], g["visitor_team_score"])]
            self._league_ppg_cache[self.season] = mean(scores) if len(scores) >= 40 else None
        return self._league_ppg_cache[self.season]


def _side_of(row: dict) -> tuple[bool | None, int | None]:
    """(jugó en casa, id del rival) de una fila de /stats; None si faltan los ids."""
    game, team = row.get("game") or {}, (row.get("team") or {}).get("id")
    home_id, visitor_id = game.get("home_team_id"), game.get("visitor_team_id")
    if team is None or home_id is None or visitor_id is None:
        return None, None
    return team == home_id, visitor_id if team == home_id else home_id


def _final(game: dict) -> bool:
    return str(game.get("status", "")).lower() == "final" and bool(game.get("home_team_score"))


def scan_day(
    analyzer: Analyzer,
    odds: OddsClient,
    day: date,
    max_events: int | None = None,
    log: Callable[[str], None] | None = None,
) -> list[tuple[Analysis, dict, PropLine]]:
    """Analiza la línea principal de cada jugador y mercado, con las de todas las casas."""
    log = log or (lambda _msg: None)
    results = []
    events = odds.events_on(day)
    log(f"{len(events)} partidos en The Odds API para {day}")
    for event in events[:max_events]:
        grouped = main_lines(odds.player_props(event))
        log(f"{event.get('away_team')} @ {event.get('home_team')}: {len(grouped)} props")
        for prop, rows in grouped:
            stat = MARKETS[prop.market]
            try:
                analysis, meta = analyzer.analyze_prop(
                    prop.player, stat, prop.line, prop.over_odds, prop.under_odds, day,
                )
            except (LookupError, ValueError) as exc:
                log(f"  descartada {prop.player} {stat} {prop.line}: {exc}")
                continue
            meta.update(bookmaker=prop.bookmaker, event_id=prop.event_id, books=book_rows(rows))
            results.append((analysis, meta, prop))
    results.sort(key=lambda r: r[0].edge, reverse=True)
    return results


__all__ = ["Analyzer", "scan_day"]
