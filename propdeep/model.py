"""Modelo estadístico de PropDeep. Funciones puras, sin red, fáciles de probar.

Idea: estimamos la probabilidad del over con el historial del jugador, la mezclamos
con la probabilidad del mercado sin margen (los mercados de props no son tontos) y
solo hablamos de "ventaja" cuando la diferencia con la cuota supera un umbral.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from statistics import mean, pstdev

STAT_LABELS = {"pts": "puntos", "reb": "rebotes", "ast": "asistencias", "fg3m": "triples"}

# Desviación mínima por estadística: evita probabilidades extremas con muestras cortas.
MIN_SD = {"pts": 4.0, "reb": 2.0, "ast": 1.8, "fg3m": 1.0}

# Ajuste por contexto acotado: el contexto matiza, no manda.
MAX_CONTEXT_ADJ = 0.05


@dataclass
class Trends:
    games: int
    last5: float | None
    last10: float | None
    last20: float | None
    season: float | None
    sd: float
    minutes_last5: float | None
    minutes_season: float | None
    hit_rate_last10: float | None  # % de los últimos 10 por encima de la línea
    recent_values: list[float]


@dataclass
class Context:
    home: bool | None = None
    back_to_back: bool = False
    opponent: str | None = None
    # Factor del rival: 1.05 = concede un 5 % más que la media de la liga en esa estadística.
    opponent_factor: float = 1.0
    injury_status: str | None = None
    injury_note: str | None = None


@dataclass
class Analysis:
    player: str
    stat: str
    line: float
    over_odds: float
    under_odds: float
    projection: float
    prob_over_model: float
    prob_over_market: float  # sin margen
    prob_over_final: float
    side: str | None  # "over", "under" o None si no hay ventaja
    edge: float  # puntos de probabilidad a favor del lado elegido (0-1)
    odds_taken: float | None
    expected_value: float | None  # por unidad apostada
    confidence: str  # "alta", "media", "baja" o "sin ventaja"
    reasons: list[str]
    trends: Trends
    context: Context

    def to_dict(self) -> dict:
        return asdict(self)


def compute_trends(values: list[float], minutes: list[float], line: float, season_games: int) -> Trends:
    """values y minutes ordenados del partido más reciente al más antiguo."""

    def avg(xs: list[float]) -> float | None:
        return round(mean(xs), 2) if xs else None

    last10 = values[:10]
    return Trends(
        games=len(values),
        last5=avg(values[:5]),
        last10=avg(last10),
        last20=avg(values[:20]),
        season=avg(values[:season_games]) if season_games else None,
        sd=round(pstdev(values[:20]), 2) if len(values) >= 2 else 0.0,
        minutes_last5=avg(minutes[:5]),
        minutes_season=avg(minutes[:season_games]) if season_games else avg(minutes),
        hit_rate_last10=round(sum(v > line for v in last10) / len(last10), 3) if last10 else None,
        recent_values=values[:10],
    )


def project(stat: str, trends: Trends, context: Context) -> float:
    """Proyección ponderada: pesa más lo reciente, ajusta por minutos y contexto."""
    parts = [(trends.last5, 0.25), (trends.last10, 0.35), (trends.last20, 0.25), (trends.season, 0.15)]
    used = [(v, w) for v, w in parts if v is not None]
    if not used:
        raise ValueError("Sin partidos suficientes para proyectar")
    base = sum(v * w for v, w in used) / sum(w for _, w in used)

    # Si su rol ha cambiado (más o menos minutos), lo reflejamos a medias.
    if trends.minutes_last5 and trends.minutes_season:
        ratio = trends.minutes_last5 / trends.minutes_season
        base *= 1 + (ratio - 1) * 0.5

    adj = (context.opponent_factor - 1) + (-0.02 if context.back_to_back else 0.0)
    adj = max(-MAX_CONTEXT_ADJ, min(MAX_CONTEXT_ADJ, adj))
    return round(base * (1 + adj), 2)


def prob_over(stat: str, projection: float, sd: float, line: float) -> float:
    if stat == "fg3m":
        # Los triples son conteos pequeños: Poisson se ajusta mejor que la normal.
        return 1 - _poisson_cdf(math.floor(line), projection)
    sigma = max(sd, MIN_SD.get(stat, 2.0))
    return 1 - _normal_cdf((line - projection) / sigma)


def devig(over_odds: float, under_odds: float) -> float:
    """Probabilidad implícita del over quitando el margen de la casa."""
    p_over, p_under = 1 / over_odds, 1 / under_odds
    return p_over / (p_over + p_under)


def analyze(
    player: str,
    stat: str,
    line: float,
    over_odds: float,
    under_odds: float,
    trends: Trends,
    context: Context,
    min_edge: float = 0.03,
    model_weight: float = 0.5,
) -> Analysis:
    projection = project(stat, trends, context)
    p_model = prob_over(stat, projection, trends.sd, line)
    p_market = devig(over_odds, under_odds)
    p_final = model_weight * p_model + (1 - model_weight) * p_market

    # Ventaja frente a la probabilidad implícita CON margen: es lo que de verdad pagas.
    edge_over = p_final - 1 / over_odds
    edge_under = (1 - p_final) - 1 / under_odds
    side, edge, odds = (("over", edge_over, over_odds) if edge_over >= edge_under
                        else ("under", edge_under, under_odds))

    reasons: list[str] = []
    blocked = _blocking_reason(context, trends)
    if blocked:
        reasons.append(blocked)
    if blocked or edge < min_edge:
        confidence, side_out, odds_out, ev = "sin ventaja", None, None, None
    else:
        confidence = _confidence(edge, trends)
        side_out, odds_out = side, odds
        p_side = p_final if side == "over" else 1 - p_final
        ev = round(p_side * odds - 1, 4)

    return Analysis(
        player=player,
        stat=stat,
        line=line,
        over_odds=over_odds,
        under_odds=under_odds,
        projection=projection,
        prob_over_model=round(p_model, 4),
        prob_over_market=round(p_market, 4),
        prob_over_final=round(p_final, 4),
        side=side_out,
        edge=round(max(edge, 0.0), 4),
        odds_taken=odds_out,
        expected_value=ev,
        confidence=confidence,
        reasons=reasons,
        trends=trends,
        context=context,
    )


def _blocking_reason(context: Context, trends: Trends) -> str | None:
    status = (context.injury_status or "").lower()
    if status in ("out", "doubtful"):
        return f"Estado de lesión: {context.injury_status}. No analizamos jugadores en duda."
    if trends.games < 5:
        return "Menos de 5 partidos con minutos: muestra insuficiente."
    return None


def _confidence(edge: float, trends: Trends) -> str:
    stable = trends.games >= 15
    if edge >= 0.06 and stable:
        return "alta"
    if edge >= 0.04 and trends.games >= 10:
        return "media"
    return "baja"


def _normal_cdf(z: float) -> float:
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def _poisson_cdf(k: int, lam: float) -> float:
    if k < 0:
        return 0.0
    term = total = math.exp(-lam)
    for i in range(1, k + 1):
        term *= lam / i
        total += term
    return min(total, 1.0)
