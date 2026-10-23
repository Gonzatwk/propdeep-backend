"""Precio justo del mercado y probabilidad estimada (calibrada) de cada línea.

Por qué: en el backtest de 2025-26 (AUDIT §3.2-3.3) el mercado sin margen está bien calibrado y el
modelo solo añade una pizca de información (peso 0,06-0,08). Lo honesto es partir del precio justo
del mercado y torcerlo un poco hacia el modelo, con la inclinación ajustada con datos (Platt) y no
a ojo. Esa es la "probabilidad estimada" que verá el usuario.

Con la probabilidad del más en la línea principal se ancla una binomial negativa (su media se
ajusta para dar esa probabilidad), y con ella sale la de cualquier umbral: "25+ puntos", "más de
19,5"... Es lo que necesita el creador de combinadas.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import mean

from .model import devig, prob_at_least, prob_over

SHARP_BOOK = "pinnacle"


@dataclass(frozen=True)
class Calibration:
    """logit(p) = alpha + logit(p_mercado) + beta * (logit(p_modelo) - logit(p_mercado))."""
    alpha: float
    beta: float
    source: str

    def prob_over(self, p_market: float, p_model: float) -> float:
        lm = _logit(p_market)
        return _sigmoid(self.alpha + lm + self.beta * (_logit(p_model) - lm))


# Ajustada con `python -m scripts.calibracion` sobre el backtest de 2025-26 (17.549 líneas de
# puntos: es lo único con cuotas reales). Mes a mes y solo con meses anteriores, mejora el log-loss
# del mercado por poco (0,69156 frente a 0,69190); la mezcla al 20 % lo empeoraba (0,69225).
# Para rebotes, asistencias y triples se usa la misma hasta tener datos.
CALIBRATION = Calibration(alpha=-0.0315, beta=0.0623, source="2026-10-24 pts 2025-26")

# La desviación del modelo se queda algo corta. Ajustado con 112.886 cuotas de líneas alternativas
# de la caché (`python -m scripts.calibracion --alternativas`): x1,06 es lo mejor en las dos mitades
# de la temporada, y así la distribución anclada acierta más que las propias casas sin margen en
# esas líneas (log-loss 0,6634 frente a 0,6646).
SD_INFLATION = 1.06


@dataclass
class FairPrice:
    line: float
    prob_over: float  # consenso sin margen de las casas con esa línea
    books: int
    pinnacle: float | None = None  # Pinnacle sin margen, si la trae: se guarda para compararla


def fair_price(books: list[dict], line: float) -> FairPrice | None:
    """Precio justo de una línea: la media sin margen de las casas que la ofrecen."""
    rows = [b for b in books if b.get("line") == line
            and (b.get("over_odds") or 0) > 1 and (b.get("under_odds") or 0) > 1]
    if not rows:
        return None
    pin = next((devig(b["over_odds"], b["under_odds"]) for b in rows if b.get("bookmaker") == SHARP_BOOK), None)
    return FairPrice(line=line, prob_over=round(mean(devig(b["over_odds"], b["under_odds"]) for b in rows), 4),
                     books=len(rows), pinnacle=round(pin, 4) if pin is not None else None)


def anchored_mean(stat: str, sd: float, line: float, p_over: float) -> float:
    """Media de la binomial negativa que da `p_over` de pasar `line` (con la desviación inflada)."""
    target = min(max(p_over, 0.001), 0.999)
    lo, hi = 0.05, max(3 * line, line + 30)
    for _ in range(40):
        mid = (lo + hi) / 2
        if prob_over(stat, mid, sd * SD_INFLATION, line) < target:
            lo = mid
        else:
            hi = mid
    return round((lo + hi) / 2, 3)


def prob_threshold(stat: str, mean_value: float, sd: float, line: float) -> float:
    """P(más de `line`) con la distribución anclada (línea ,5 o entera; para "X+" usar X - 0,5)."""
    if line != math.floor(line):
        return prob_over(stat, mean_value, sd * SD_INFLATION, line)
    return prob_at_least(stat, mean_value, sd * SD_INFLATION, int(line) + 1)


def estimate(stat: str, line: float, p_model: float, p_market_main: float, sd: float,
             books: list[dict]) -> dict:
    """Precio justo, probabilidad estimada del más y media anclada de una línea.

    `p_market_main` (la casa con menos margen) solo se usa si no hay más casas en esa línea."""
    fair = fair_price(books, line)
    p_market = fair.prob_over if fair else p_market_main
    p = CALIBRATION.prob_over(p_market, p_model)
    return {
        "fair_over": round(p_market, 4),
        "fair_books": fair.books if fair else 1,
        "pinnacle_over": fair.pinnacle if fair else None,
        "prob_over": round(p, 4),
        "anchored_mean": anchored_mean(stat, sd, line, p),
        "calibration": CALIBRATION.source,
    }


def _logit(p: float) -> float:
    p = min(max(p, 1e-4), 1 - 1e-4)
    return math.log(p / (1 - p))


def _sigmoid(z: float) -> float:
    return 1 / (1 + math.exp(-z))
