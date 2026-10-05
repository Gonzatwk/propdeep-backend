"""Modelo candidato para comparar en el backtest. NO es el de producción.

Corrige dos fallos que el backtest de la temporada 2025-26 encontró en propdeep/model.py:

1. Ajuste por minutos sin tope: con pocos partidos en la temporada (o con minutos de la temporada
   anterior mezclados en "últimos 5"), la proporción de minutos se disparaba y salían proyecciones
   absurdas (p. ej. 123 puntos con línea 11,5). Aquí solo se usa con 5 o más partidos de esta
   temporada, solo con minutos de esta temporada y con tope de +-15 %.
2. Sesgo al over: la normal simétrica alrededor de la media da demasiado over, porque en la NBA
   los puntos, rebotes y asistencias tienen cola a la derecha (la mediana queda por debajo de la
   media). Aquí se usa una binomial negativa, que respeta esa asimetría.

Si mejora la calibración en el backtest, se pasa a propdeep/model.py en un PR aparte.
"""
from __future__ import annotations

import math
from dataclasses import replace
from statistics import mean

from propdeep.model import MAX_CONTEXT_ADJ, MIN_SD, Context, Trends, compute_trends

MIN_SEASON_GAMES_FOR_MINUTES = 5
MAX_MINUTES_ADJ = 0.15


def trends_candidato(values, minutes, line, season_games) -> Trends:
    t = compute_trends(values, minutes, line, season_games)
    if season_games < MIN_SEASON_GAMES_FOR_MINUTES:
        return replace(t, minutes_last5=None)
    season_mins = minutes[:season_games]
    return replace(t, minutes_last5=round(mean(season_mins[:5]), 2),
                   minutes_season=round(mean(season_mins), 2))


def project(stat: str, trends: Trends, context: Context) -> float:
    parts = [(trends.last5, 0.25), (trends.last10, 0.35), (trends.last20, 0.25), (trends.season, 0.15)]
    used = [(v, w) for v, w in parts if v is not None]
    if not used:
        raise ValueError("Sin partidos suficientes para proyectar")
    base = sum(v * w for v, w in used) / sum(w for _, w in used)
    if trends.minutes_last5 and trends.minutes_season:
        ratio = trends.minutes_last5 / trends.minutes_season
        base *= 1 + max(-MAX_MINUTES_ADJ, min(MAX_MINUTES_ADJ, (ratio - 1) * 0.5))
    adj = (context.opponent_factor - 1) + (-0.02 if context.back_to_back else 0.0)
    adj = max(-MAX_CONTEXT_ADJ, min(MAX_CONTEXT_ADJ, adj))
    return round(base * (1 + adj), 2)


def prob_over(stat: str, projection: float, sd: float, line: float) -> float:
    """P(X > línea) con binomial negativa (Poisson si no hay sobredispersión)."""
    mu = max(projection, 0.05)
    var = max(sd, MIN_SD.get(stat, 2.0)) ** 2
    k = math.floor(line)
    if k < 0:
        return 1.0
    if var <= mu * 1.0001:
        log_p = -mu
        cdf = term = math.exp(log_p)
        for i in range(1, k + 1):
            term *= mu / i
            cdf += term
        return max(0.0, min(1.0, 1 - cdf))
    r = mu * mu / (var - mu)
    p = r / (r + mu)
    cdf = 0.0
    for i in range(k + 1):
        cdf += math.exp(math.lgamma(i + r) - math.lgamma(r) - math.lgamma(i + 1)
                        + r * math.log(p) + i * math.log(1 - p))
    return max(0.0, min(1.0, 1 - cdf))
