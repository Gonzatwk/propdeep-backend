"""Backtest del modelo de PropDeep sobre una temporada pasada (por defecto, la 2025-26).

Repite partido a partido lo que haría el backend en producción, usando solo lo que se sabía
antes de cada partido: tendencias con partidos anteriores, factor del rival con sus partidos
anteriores y back-to-back por calendario. Usa la misma función `analyze` de producción, sin tocarla.

Dos modos de líneas:

  proxy     Gratis. No hay cuotas históricas: se inventa una línea "de casa ingenua"
            (media de los 10 partidos previos, al ,5 más cercano) con cuota 1,87 a cada lado. Mide si las
            probabilidades del modelo están bien calibradas, pero NO dice si gana al mercado real.

  odds-api  Líneas reales de The Odds API (endpoint histórico, solo planes de pago). Cada respuesta
            se guarda en disco, así que repetir el backtest no vuelve a gastar créditos.

Uso (con BALLDONTLIE_API_KEY y ODDS_API_KEY en .env):

    python -m scripts.backtest --lineas proxy
    python -m scripts.backtest --lineas odds-api --estimar          # solo calcula el coste
    python -m scripts.backtest --lineas odds-api --max-creditos 18000

Limitaciones que no se pueden evitar: el parte de lesiones histórico no existe en Balldontlie
(solo se evalúan jugadores que jugaron, igual que la casa anula la apuesta si no juega).
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import random
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from statistics import mean

from propdeep.clients.balldontlie import BASE_URL as BDL_URL, minutes, normalize_name
from propdeep.clients.odds import BASE_URL as ODDS_URL, MARKETS, SPORT, parse_props
from propdeep.model import Analysis, Context, analyze, compute_trends

MIN_OPPONENT_GAMES = 5  # igual que en propdeep/pipeline.py
PROXY_ODDS = 1.87  # cuota típica de una prop (-115 americano)
PROXY_MIN_MINUTES = 20.0  # las casas solo sacan props de jugadores de rotación
NAME_SUFFIXES = {"jr", "sr", "ii", "iii", "iv"}


# ----------------------------------------------------------------------------- datos

@dataclass
class Row:
    """Una línea de estadísticas de un jugador en un partido (forma simplificada)."""
    player_id: int
    player_name: str
    team_id: int
    game_id: int
    day: str  # AAAA-MM-DD, fecha local del partido
    season: int
    minutes: float
    stats: dict[str, float]


@dataclass
class Game:
    id: int
    day: str
    season: int
    home_id: int
    visitor_id: int
    home_name: str
    visitor_name: str
    home_score: int
    visitor_score: int
    postseason: bool = False


@dataclass
class Candidate:
    """Una línea a analizar: jugador, partido, estadística y cuotas."""
    row: Row
    stat: str
    line: float
    over_odds: float
    under_odds: float
    bookmaker: str


@dataclass
class Season:
    """Índices para responder rápido "qué se sabía antes del día D"."""
    rows: list[Row]
    games: list[Game]
    season: int
    by_player: dict[int, list[Row]] = field(default_factory=dict)
    team_days: dict[int, set[str]] = field(default_factory=dict)
    games_by_id: dict[int, Game] = field(default_factory=dict)

    def __post_init__(self):
        by_player: dict[int, list[Row]] = defaultdict(list)
        for r in self.rows:
            by_player[r.player_id].append(r)
        # Del más reciente al más antiguo, como devuelve producción.
        self.by_player = {pid: sorted(rs, key=lambda r: r.day, reverse=True) for pid, rs in by_player.items()}
        team_days: dict[int, set[str]] = defaultdict(set)
        for g in self.games:
            team_days[g.home_id].add(g.day)
            team_days[g.visitor_id].add(g.day)
        self.team_days = dict(team_days)
        self.games_by_id = {g.id: g for g in self.games}
        self._final = sorted((g for g in self.games if g.season == self.season and g.home_score),
                             key=lambda g: g.day)
        self._factor_cache: dict[tuple[int, str], float] = {}

    def history(self, player_id: int, day: str) -> list[Row]:
        """Partidos del jugador ESTRICTAMENTE anteriores a `day` (temporada y la anterior)."""
        return [r for r in self.by_player.get(player_id, [])
                if r.day < day and r.season in (self.season, self.season - 1)]

    def context(self, row: Row, stat: str) -> Context:
        g = self.games_by_id.get(row.game_id)
        ctx = Context()
        if not g:
            return ctx
        home = g.home_id == row.team_id
        opp_id = g.visitor_id if home else g.home_id
        ctx.home = home
        ctx.opponent = g.visitor_name if home else g.home_name
        yesterday = (date.fromisoformat(row.day) - timedelta(days=1)).isoformat()
        ctx.back_to_back = yesterday in self.team_days.get(row.team_id, set())
        if stat == "pts":
            ctx.opponent_factor = self._points_allowed_factor(opp_id, row.day)
        return ctx

    def _points_allowed_factor(self, team_id: int, day: str) -> float:
        key = (team_id, day)
        if key not in self._factor_cache:
            self._factor_cache[key] = self._compute_factor(team_id, day)
        return self._factor_cache[key]

    def _compute_factor(self, team_id: int, day: str) -> float:
        before = [g for g in self._final if g.day < day]
        if len(before) < 20:
            return 1.0
        league = mean(s for g in before for s in (g.home_score, g.visitor_score))
        allowed = [g.visitor_score if g.home_id == team_id else g.home_score
                   for g in before if team_id in (g.home_id, g.visitor_id)]
        if len(allowed) < MIN_OPPONENT_GAMES:
            return 1.0
        return round(mean(allowed) / league, 3)


def strip_suffix(name: str) -> str:
    parts = normalize_name(name).replace("-", " ").split()
    return " ".join(p for p in parts if p not in NAME_SUFFIXES)


# ------------------------------------------------------------------- Balldontlie

class BdlFetcher:
    """Descarga temporadas completas de Balldontlie con pausa y caché en disco."""

    def __init__(self, api_key: str, cache: Path, pause: float = 1.05):
        import httpx

        self.http = httpx.Client(base_url=BDL_URL, headers={"Authorization": api_key}, timeout=30.0)
        self.cache = cache
        self.pause = pause  # ALL-STAR: 60 peticiones por minuto

    def _all(self, path: str, params: dict) -> list[dict]:
        items, params = [], {**params, "per_page": 100}
        while True:
            for attempt in range(6):
                resp = self.http.get(path, params=params)
                if resp.status_code == 429:
                    time.sleep(10 * (attempt + 1))
                    continue
                resp.raise_for_status()
                break
            body = resp.json()
            items.extend(body.get("data", []))
            time.sleep(self.pause)
            cursor = body.get("meta", {}).get("next_cursor")
            if not cursor:
                return items
            params["cursor"] = cursor
            if len(items) % 5000 == 0:
                print(f"  {path}: {len(items)} filas…")

    def season(self, season: int) -> tuple[list[dict], list[dict]]:
        f = self.cache / f"bdl_{season}.json"
        if f.exists():
            data = json.loads(f.read_text(encoding="utf-8"))
            return data["stats"], data["games"]
        print(f"Descargando temporada {season} de Balldontlie (tarda unos minutos, solo la primera vez)")
        games = self._all("/games", {"seasons[]": season})
        stats = self._all("/stats", {"seasons[]": season})
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps({"stats": stats, "games": games}), encoding="utf-8")
        return stats, games


def to_rows(stats: list[dict]) -> list[Row]:
    rows = []
    for s in stats:
        mins = minutes(s.get("min"))
        g = s.get("game") or {}
        if mins <= 0 or g.get("postseason"):
            continue
        p = s.get("player") or {}
        rows.append(Row(
            player_id=p["id"],
            player_name=f"{p.get('first_name', '')} {p.get('last_name', '')}".strip(),
            team_id=(s.get("team") or {}).get("id"),
            game_id=g["id"],
            day=str(g["date"])[:10],
            season=g["season"],
            minutes=mins,
            stats={k: float(s.get(k) or 0) for k in ("pts", "reb", "ast", "fg3m")},
        ))
    return rows


def to_games(games: list[dict]) -> list[Game]:
    out = []
    for g in games:
        if g.get("postseason"):
            continue
        final = str(g.get("status", "")).lower() == "final"
        out.append(Game(
            id=g["id"], day=str(g["date"])[:10], season=g["season"],
            home_id=g["home_team"]["id"], visitor_id=g["visitor_team"]["id"],
            home_name=g["home_team"].get("full_name", ""), visitor_name=g["visitor_team"].get("full_name", ""),
            home_score=(g.get("home_team_score") or 0) if final else 0,
            visitor_score=(g.get("visitor_team_score") or 0) if final else 0,
        ))
    return out


# ----------------------------------------------------------------------- líneas

def proxy_candidates(season: Season, desde: str, hasta: str, stats: list[str]) -> list[Candidate]:
    """Línea de "casa ingenua": media de los 10 previos llevada al ,5 más cercano, cuota 1,87."""
    out = []
    for r in season.rows:
        if r.season != season.season or not (desde <= r.day <= hasta):
            continue
        prev = season.history(r.player_id, r.day)[:10]
        if len(prev) < 5 or mean(p.minutes for p in prev) < PROXY_MIN_MINUTES:
            continue
        for stat in stats:
            avg = mean(p.stats[stat] for p in prev)
            if stat != "pts" and avg < 1:
                continue
            line = max(0.5, round(avg - 0.5) + 0.5)
            out.append(Candidate(r, stat, line, PROXY_ODDS, PROXY_ODDS, "proxy"))
    return out


class OddsHistory:
    """Cuotas históricas de props desde The Odds API, con caché por petición."""

    def __init__(self, api_key: str, cache: Path, regions: str, markets: list[str], max_credits: int,
                 minutes_before: int = 60):
        import httpx

        self.http = httpx.Client(base_url=ODDS_URL, timeout=30.0)
        self.key = api_key
        self.cache = cache
        self.regions = regions
        self.markets = markets
        self.max_credits = max_credits
        self.minutes_before = minutes_before
        self.spent = 0
        self.remaining: str | None = None

    def _get(self, path: str, params: dict, cost_estimate: int) -> dict | None:
        key = path.strip("/").replace("/", "_") + "_" + "_".join(f"{k}={v}" for k, v in sorted(params.items()))
        f = self.cache / "odds" / (key.replace(":", "").replace(",", "+") + ".json")
        if f.exists():
            return json.loads(f.read_text(encoding="utf-8"))
        if self.spent + cost_estimate > self.max_credits:
            return None
        resp = self.http.get(path, params={**params, "apiKey": self.key})
        if resp.status_code == 422:  # sin datos para ese momento
            body = {"data": None}
        else:
            resp.raise_for_status()
            body = resp.json()
        self.spent += int(resp.headers.get("x-requests-last", cost_estimate) or 0)
        self.remaining = resp.headers.get("x-requests-remaining", self.remaining)
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(body), encoding="utf-8")
        return body

    def candidates(self, season: Season, days: list[str], stats: list[str]) -> tuple[list[Candidate], bool]:
        by_name: dict[str, list[Row]] = defaultdict(list)
        for r in season.rows:
            by_name[strip_suffix(r.player_name)].append(r)
        markets = [m for m, s in MARKETS.items() if s in stats]
        out, complete = [], True
        for day in days:
            start = datetime.fromisoformat(day).replace(hour=12, tzinfo=timezone.utc)
            events = self._get(f"/historical/sports/{SPORT}/events", {
                "date": _iso(start + timedelta(hours=4)),
                "commenceTimeFrom": _iso(start), "commenceTimeTo": _iso(start + timedelta(days=1)),
            }, 1)
            if events is None:
                complete = False
                break
            for ev in events.get("data") or []:
                tip = datetime.fromisoformat(ev["commence_time"].replace("Z", "+00:00"))
                snap = self._get(f"/historical/sports/{SPORT}/events/{ev['id']}/odds", {
                    "date": _iso(tip - timedelta(minutes=self.minutes_before)),
                    "regions": self.regions, "markets": ",".join(markets), "oddsFormat": "decimal",
                }, 10 * len(markets) * len(self.regions.split(",")))
                if snap is None:
                    complete = False
                    break
                if not snap.get("data"):
                    continue
                for prop in main_lines(parse_props(snap["data"])):
                    rows = [r for r in by_name.get(strip_suffix(prop.player or ""), []) if r.day == day]
                    if len(rows) == 1:  # si no jugó, la casa anula la apuesta: no cuenta
                        out.append(Candidate(rows[0], MARKETS[prop.market], prop.line,
                                             prop.over_odds, prop.under_odds, prop.bookmaker))
            if not complete:
                break
            print(f"  {day}: {len(out)} líneas acumuladas, {self.spent} créditos gastados")
        return out, complete


def main_lines(props):
    """De todas las líneas de un jugador y mercado, la principal: la más cercana al 50/50."""
    best = {}
    for p in props:
        k = (p.player, p.market)
        balance = abs(1 / p.over_odds - 1 / p.under_odds)
        if k not in best or balance < best[k][0]:
            best[k] = (balance, p)
    return [p for _, p in best.values()]


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


# ------------------------------------------------------------------ evaluación

@dataclass
class Result:
    cand: Candidate
    analysis: Analysis
    actual: float
    outcome_over: float | None  # 1 over, 0 under, None push
    profit: float | None  # por unidad, solo si hubo pick


def evaluate(season: Season, cands: list[Candidate], min_edge: float, model_weight: float) -> list[Result]:
    results = []
    for c in cands:
        prev = season.history(c.row.player_id, c.row.day)
        if not prev:
            continue
        values = [p.stats[c.stat] for p in prev]
        mins = [p.minutes for p in prev]
        season_games = sum(1 for p in prev if p.season == season.season)
        trends = compute_trends(values, mins, c.line, season_games)
        try:
            a = analyze(c.row.player_name, c.stat, c.line, c.over_odds, c.under_odds, trends,
                        season.context(c.row, c.stat), min_edge=min_edge, model_weight=model_weight)
        except ValueError:
            continue
        actual = c.row.stats[c.stat]
        outcome = None if actual == c.line else float(actual > c.line)
        profit = None
        if a.side and outcome is not None:
            won = (outcome == 1) == (a.side == "over")
            profit = (a.odds_taken - 1) if won else -1.0
        elif a.side:
            profit = 0.0
        results.append(Result(c, a, actual, outcome, profit))
    return results


def summarize(results: list[Result], seed: int = 7) -> dict:
    graded = [r for r in results if r.outcome_over is not None]

    def brier(key):
        return round(mean((key(r) - r.outcome_over) ** 2 for r in graded), 5) if graded else None

    def logloss(key):
        eps = 1e-6
        return round(-mean(math.log(max(eps, key(r))) if r.outcome_over else math.log(max(eps, 1 - key(r)))
                           for r in graded), 5) if graded else None

    picks = [r for r in results if r.analysis.side]
    out = {
        "lineas_analizadas": len(results),
        "lineas_con_resultado": len(graded),
        "precision_probabilidades": {
            "brier_modelo": brier(lambda r: r.analysis.prob_over_model),
            "brier_mercado": brier(lambda r: r.analysis.prob_over_market),
            "brier_final": brier(lambda r: r.analysis.prob_over_final),
            "logloss_modelo": logloss(lambda r: r.analysis.prob_over_model),
            "logloss_mercado": logloss(lambda r: r.analysis.prob_over_market),
            "logloss_final": logloss(lambda r: r.analysis.prob_over_final),
        },
        "picks": pick_stats(picks, seed),
        "por_confianza": {k: pick_stats([r for r in picks if r.analysis.confidence == k], seed)
                          for k in ("alta", "media", "baja")},
        "por_estadistica": {s: pick_stats([r for r in picks if r.cand.stat == s], seed)
                            for s in sorted({r.cand.stat for r in picks})},
        "por_lado": {s: pick_stats([r for r in picks if r.analysis.side == s], seed) for s in ("over", "under")},
        "por_mes": {m: pick_stats([r for r in picks if r.cand.row.day[:7] == m], seed)
                    for m in sorted({r.cand.row.day[:7] for r in picks})},
        "calibracion_picks": calibration(picks),
        "calibracion_modelo": calibration_all(graded),
    }
    return out


def pick_stats(picks: list[Result], seed: int = 7) -> dict:
    settled = [r for r in picks if r.profit is not None and r.outcome_over is not None]
    if not settled:
        return {"n": 0}
    profits = [r.profit for r in settled]
    wins = sum(p > 0 for p in profits)
    rng = random.Random(seed)
    boots = sorted(mean(rng.choices(profits, k=len(profits))) for _ in range(1000))
    return {
        "n": len(settled),
        "acierto": round(wins / len(settled), 4),
        "acierto_necesario": round(mean(1 / r.analysis.odds_taken for r in settled), 4),
        "roi": round(mean(profits), 4),
        "roi_ic95": [round(boots[25], 4), round(boots[974], 4)],
        "cuota_media": round(mean(r.analysis.odds_taken for r in settled), 3),
        "empujes": sum(1 for r in picks if r.outcome_over is None),
    }


def calibration(picks: list[Result]) -> list[dict]:
    """Probabilidad que dimos al lado elegido frente a la frecuencia real con que salió."""
    bins = defaultdict(list)
    for r in picks:
        if r.outcome_over is None:
            continue
        p = r.analysis.prob_over_final if r.analysis.side == "over" else 1 - r.analysis.prob_over_final
        won = (r.outcome_over == 1) == (r.analysis.side == "over")
        bins[min(int(p * 20) / 20, 0.95)].append((p, won))
    return [{"tramo": f"{b:.2f}-{b + 0.05:.2f}", "n": len(v),
             "prob_media": round(mean(p for p, _ in v), 4),
             "acierto_real": round(mean(w for _, w in v), 4)} for b, v in sorted(bins.items())]


def calibration_all(graded: list[Result]) -> list[dict]:
    """Calibración del modelo estadístico solo (sin mercado) sobre TODAS las líneas."""
    bins = defaultdict(list)
    for r in graded:
        p = r.analysis.prob_over_model
        bins[min(int(p * 10) / 10, 0.9)].append((p, r.outcome_over))
    return [{"tramo": f"{b:.1f}-{b + 0.1:.1f}", "n": len(v),
             "prob_media": round(mean(p for p, _ in v), 4),
             "frecuencia_real": round(mean(o for _, o in v), 4)} for b, v in sorted(bins.items())]


def write_outputs(results: list[Result], summary: dict, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "resumen.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    with open(out_dir / "lineas.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["fecha", "jugador", "estadistica", "linea", "cuota_over", "cuota_under", "casa",
                    "proyeccion", "p_modelo", "p_mercado", "p_final", "lado", "ventaja", "confianza",
                    "real", "beneficio"])
        for r in results:
            a = r.analysis
            w.writerow([r.cand.row.day, a.player, r.cand.stat, a.line, a.over_odds, a.under_odds,
                        r.cand.bookmaker, a.projection, a.prob_over_model, a.prob_over_market,
                        a.prob_over_final, a.side or "", a.edge, a.confidence, r.actual,
                        "" if r.profit is None else round(r.profit, 4)])


def print_summary(s: dict, mode: str) -> None:
    p = s["picks"]
    pr = s["precision_probabilidades"]
    print(f"\n=== Backtest ({mode}) ===")
    print(f"Líneas analizadas: {s['lineas_analizadas']} | picks con ventaja: {p.get('n', 0)}")
    print(f"Brier (más bajo es mejor): modelo {pr['brier_modelo']}, mercado {pr['brier_mercado']},"
          f" final {pr['brier_final']}")
    print("Calibración del modelo estadístico en todas las líneas (prob. de over -> frecuencia real):")
    for b in s["calibracion_modelo"]:
        print(f"  {b['tramo']}: n={b['n']} {b['prob_media']:.1%} -> {b['frecuencia_real']:.1%}")
    if mode == "proxy":
        print("\nEn modo proxy la línea es inventada, así que el acierto y el ROI de los picks NO dicen nada"
              " sobre el mercado real (una casa ingenua es fácil de batir). Están en resumen.json solo como"
              " referencia. Para saber si hay ventaja de verdad hace falta --lineas odds-api.")
        return
    if p.get("n"):
        print(f"Acierto {p['acierto']:.1%} (necesario para no perder: {p['acierto_necesario']:.1%})")
        print(f"ROI {p['roi']:+.1%}  (IC 95 %: {p['roi_ic95'][0]:+.1%} a {p['roi_ic95'][1]:+.1%})")
    for k, v in s["por_confianza"].items():
        if v.get("n"):
            print(f"  confianza {k}: n={v['n']} acierto {v['acierto']:.1%} ROI {v['roi']:+.1%}")
    for k, v in s["por_estadistica"].items():
        print(f"  {k}: n={v['n']} acierto {v['acierto']:.1%} ROI {v['roi']:+.1%}")
    print("Calibración de los picks (prob. que dimos al lado elegido -> acierto real):")
    for b in s["calibracion_picks"]:
        print(f"  {b['tramo']}: n={b['n']} {b['prob_media']:.1%} -> {b['acierto_real']:.1%}")


# ------------------------------------------------------------------------- main

def load_season(api_key: str, season: int, cache: Path) -> Season:
    fetcher = BdlFetcher(api_key, cache)
    stats, games = fetcher.season(season)
    prev_stats, _ = fetcher.season(season - 1)  # para las tendencias de principio de temporada
    return Season(to_rows(prev_stats) + to_rows(stats), to_games(games), season)


def main() -> None:
    from propdeep.config import get_settings

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--temporada", type=int, default=2025, help="Formato Balldontlie: 2025 = 2025-26")
    parser.add_argument("--lineas", choices=["proxy", "odds-api"], default="proxy")
    parser.add_argument("--desde", default="0000-00-00")
    parser.add_argument("--hasta", default="9999-99-99")
    parser.add_argument("--stats", default="pts,reb,ast,fg3m", help="pts,reb,ast,fg3m")
    parser.add_argument("--regiones", default="us", help="The Odds API: us tiene casi todas las props NBA")
    parser.add_argument("--minutos-antes", type=int, default=60, help="Foto de cuotas X minutos antes del inicio")
    parser.add_argument("--max-creditos", type=int, default=0, help="Tope de créditos a gastar en esta ejecución")
    parser.add_argument("--estimar", action="store_true", help="Solo calcula los créditos necesarios")
    parser.add_argument("--cache", default="backtest_cache")
    parser.add_argument("--salida", default="backtest_out")
    args = parser.parse_args()

    s = get_settings()
    stats = [x.strip() for x in args.stats.split(",") if x.strip()]
    cache = Path(args.cache)
    season = load_season(s.balldontlie_api_key, args.temporada, cache)
    days = sorted({g.day for g in season.games
                   if g.season == args.temporada and g.home_score and args.desde <= g.day <= args.hasta})
    if not days:
        raise SystemExit("No hay partidos terminados en ese rango.")
    print(f"Temporada {args.temporada}: {len(days)} jornadas, del {days[0]} al {days[-1]}")

    if args.lineas == "proxy":
        cands = proxy_candidates(season, days[0], days[-1], stats)
    else:
        n_games = sum(1 for g in season.games
                      if g.season == args.temporada and g.home_score and days[0] <= g.day <= days[-1])
        markets = [m for m, st in MARKETS.items() if st in stats]
        per_game = 10 * len(markets) * len(args.regiones.split(","))
        need = n_games * per_game + len(days)
        print(f"Coste estimado: {n_games} partidos x {per_game} + {len(days)} = {need} créditos"
              " (lo ya descargado en caché no se vuelve a pagar)")
        if args.estimar:
            return
        if not args.max_creditos:
            raise SystemExit("Pon --max-creditos para no gastar más de la cuenta.")
        hist = OddsHistory(s.odds_api_key, cache, args.regiones, markets, args.max_creditos, args.minutos_antes)
        cands, complete = hist.candidates(season, days, stats)
        print(f"Créditos gastados: {hist.spent}; quedan en la cuenta: {hist.remaining}")
        if not complete:
            print("Tope de créditos alcanzado: el backtest cubre solo las jornadas descargadas.")

    results = evaluate(season, cands, s.min_edge, s.model_weight)
    summary = summarize(results)
    summary["modo"] = args.lineas
    summary["temporada"] = args.temporada
    write_outputs(results, summary, Path(args.salida) / args.lineas)
    print_summary(summary, args.lineas)
    print(f"\nDetalle en {Path(args.salida) / args.lineas}/ (resumen.json y lineas.csv)")


if __name__ == "__main__":
    main()
