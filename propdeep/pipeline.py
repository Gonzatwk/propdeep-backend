"""Une datos reales (Balldontlie + The Odds API) con el modelo y la redacción."""
from __future__ import annotations

from datetime import date
from typing import Callable
from statistics import mean

from .clients.balldontlie import BalldontlieClient, minutes
from .clients.odds import MARKETS, OddsClient, PropLine, book_rows, main_lines
from .model import Analysis, Context, analyze, compute_splits, compute_trends, is_key_teammate, teammate_out_factor

MIN_OPPONENT_GAMES = 5
# Estados del parte de lesiones que cuentan como "no juega" para el ajuste por compañeros.
OUT_STATUSES = ("out", "doubtful")


class Analyzer:
    def __init__(self, bdl: BalldontlieClient, season: int, min_edge: float, model_weight: float,
                 teammate_adjust: bool | None = None):
        if teammate_adjust is None:
            from .config import get_settings

            teammate_adjust = get_settings().teammate_adjust
        self.teammate_adjust = teammate_adjust
        self.bdl = bdl
        self.season = season
        self.min_edge = min_edge
        self.model_weight = model_weight
        self._league_ppg_cache: dict[int, float | None] = {}
        self._absent_cache: dict[tuple[int, str], dict[int, tuple[str, set[int], str]]] = {}

    def analyze_prop(
        self,
        player_name: str,
        stat: str,
        line: float,
        over_odds: float,
        under_odds: float,
        game_day: date,
        opponent_name: str | None = None,
        event_teams: tuple[str, str] | None = None,
    ) -> tuple[Analysis, dict]:
        """Devuelve el análisis y los metadatos del partido (ids) para el historial.

        `event_teams` son los equipos del partido según la casa: con ellos se encuentra el partido
        aunque el jugador haya cambiado de equipo y su historial sea del anterior."""
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

        last_team = logs[0]["team"]["id"] if logs else None
        team_id, game = self._team_and_game(player, last_team, game_day, event_teams)
        context = self._context(player, stat, team_id, game, game_day, opponent_name)
        if last_team is not None and team_id is not None and last_team != team_id:
            context.traded = True
            context.games_with_team = sum(1 for r in logs if r["team"]["id"] == team_id)
        elif game is not None and team_id is None and logs:
            # Juega este partido pero ninguno de sus equipos conocidos está en él: traspaso reciente.
            context.traded, context.games_with_team = True, 0
        if game and team_id is not None:
            absent = {name: (played, since) for pid, (name, played, since)
                      in self._teammates_out(team_id, game_day).items() if pid != player["id"]}
            if absent:
                factor, context.teammates_out = teammate_out_factor(
                    values, [r["game"]["id"] for r in logs], [r["game"]["date"][:10] for r in logs],
                    [r["team"]["id"] for r in logs], team_id, absent)
                context.teammate_factor = factor if self.teammate_adjust else 1.0
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

    def _team_and_game(self, player: dict, last_team: int | None, day: date,
                       event_teams: tuple[str, str] | None) -> tuple[int | None, dict | None]:
        """Equipo actual del jugador y su partido del día.

        El equipo del último partido jugado no vale tras un traspaso: el 21-oct-2026 un 23 % de las
        líneas salieron con el rival, la pista y el partido del equipo anterior."""
        current = (player.get("team") or {}).get("id")
        candidates = [t for t in (current, last_team) if t is not None]
        if event_teams:
            names = {_norm_team(n) for n in event_teams}
            for game in self.bdl.games_on(day):
                teams = (game["home_team"], game["visitor_team"])
                if {_norm_team(t.get("full_name")) for t in teams} == names:
                    ids = [t["id"] for t in teams]
                    team = next((t for t in candidates if t in ids), None)
                    return team, game
        for team in candidates:
            game = self._find_game(team, day)
            if game:
                return team, game
        return (candidates[0] if candidates else None), None

    def _teammates_out(self, team_id: int, day: date) -> dict[int, tuple[str, set[int], str]]:
        """Jugadores importantes del equipo que el parte de lesiones da fuera o en duda.

        Devuelve id -> (nombre, partidos que jugó con el equipo, fecha del primero). "Importante" se
        mide en los 5 últimos partidos del equipo, como en el backtest. Una consulta al parte por
        equipo y día, y una por cada lesionado."""
        key = (team_id, day.isoformat())
        if key in self._absent_cache:
            return self._absent_cache[key]
        out: dict[int, tuple[str, set[int], str]] = {}
        injuries = [i for i in self.bdl._get_all("/player_injuries", {"team_ids[]": team_id}, limit=50)
                    if str(i.get("status", "")).lower() in OUT_STATUSES]
        if injuries:
            games = []
            for season in (self.season, self.season - 1):
                games += [g for g in self.bdl.team_games(team_id, season)
                          if g["date"][:10] < day.isoformat() and _final(g)]
                if len(games) >= 5:
                    break
            last5 = [g["id"] for g in sorted(games, key=lambda g: g["date"])[-5:]]
            for inj in injuries:
                p = inj.get("player") or {}
                if not p.get("id"):
                    continue
                rows = [r for r in self.bdl.player_stats(p["id"], [self.season, self.season - 1])
                        if (r.get("team") or {}).get("id") == team_id]
                played = {r["game"]["id"]: minutes(r.get("min")) for r in rows}
                if rows and is_key_teammate(last5, played):
                    since = min(r["game"]["date"][:10] for r in rows)
                    out[p["id"]] = (f"{p.get('first_name', '')} {p.get('last_name', '')}".strip(), set(played), since)
        self._absent_cache[key] = out
        return out

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


def _norm_team(name: str | None) -> str:
    # The Odds API y Balldontlie escriben igual los nombres salvo "LA Clippers"/"Los Angeles Clippers".
    return (name or "").lower().replace("los angeles clippers", "la clippers").strip()


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
                    event_teams=(prop.home_team, prop.away_team),
                )
            except (LookupError, ValueError) as exc:
                log(f"  descartada {prop.player} {stat} {prop.line}: {exc}")
                continue
            meta.update(bookmaker=prop.bookmaker, event_id=prop.event_id, books=book_rows(rows))
            results.append((analysis, meta, prop))
    results.sort(key=lambda r: r[0].edge, reverse=True)
    return results


__all__ = ["Analyzer", "scan_day"]
