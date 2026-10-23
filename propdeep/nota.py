"""Nota de 0 a 100 de una línea, el lado que la lleva y sus razones (feed y combinadas).

Por qué así (PLAN-PLATAFORMA §2.2):
- El lado nunca contradice a la probabilidad estimada: solo se puntúa el lado que la estimación
  (fair.py) ve igual o mejor que el precio justo del mercado.
- La nota resume cuatro cosas, cada una de 0 a 1: valor (cuánto se separa la estimación del
  mercado y si alguna casa paga por encima del precio justo), forma (veces que superó la línea),
  matchup (rival, casa/fuera) y fiabilidad (muestra y minutos estables).
- Los pesos salen de validarla con el backtest (`python -m scripts.validar_nota`): lo que no
  predice nada no puntúa, aunque se siga enseñando como razón.

No es una recomendación: es un resumen de los datos de la línea.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

from .model import STAT_LABELS

NOTA_VERSION = "2026.10.24"

# Peso de cada parte en la nota (suman 1). Ver la validación en PLAN-PLATAFORMA §2.5.
WEIGHTS = {"valor_modelo": 0.20, "valor_precio": 0.20, "forma": 0.25, "matchup": 0.20, "fiabilidad": 0.15}

# Escalas: con esto una parte llega a 1.
FULL_MODEL_GAP = 0.02  # la estimación 2 pp por encima del precio justo
FULL_PRICE_EV = 0.04  # alguna casa paga un 4 % por encima del precio justo
FULL_HIT_EDGE = 0.30  # superó la línea en el 80 % de los partidos (50 % + 30 pp)
FULL_OPP_FACTOR = 0.06  # el rival concede un 6 % más (o menos) que la media
MIN_SPLIT_GAMES = 2


@dataclass
class Nota:
    side: str  # "over" o "under"
    score: int  # 0-100
    prob: float  # probabilidad estimada del lado
    fair: float  # precio justo del lado (sin margen)
    parts: dict
    reasons: list[str]
    version: str = NOTA_VERSION

    def to_dict(self) -> dict:
        return asdict(self)


def nota(a: dict) -> Nota | None:
    """Nota de una línea a partir de su análisis guardado (con `estimate`). None si no se puede
    puntuar: sin estimación o con un bloqueo (lesión, muestra corta, traspaso…)."""
    est = a.get("estimate")
    if not est or a.get("reasons"):
        return None
    p_over, fair_over = est["prob_over"], est["fair_over"]
    side = "over" if p_over >= fair_over else "under"
    sign = 1 if side == "over" else -1
    prob = p_over if side == "over" else 1 - p_over
    fair = fair_over if side == "over" else 1 - fair_over
    trends, ctx = a.get("trends") or {}, a.get("context") or {}

    parts = {
        "valor_modelo": _clip((prob - fair) / FULL_MODEL_GAP),
        "valor_precio": _clip(_best_ev(a, side, prob) / FULL_PRICE_EV),
        "forma": _form(trends, side),
        "matchup": _matchup(trends, ctx, side, sign),
        "fiabilidad": _reliability(trends, ctx),
    }
    score = round(100 * sum(WEIGHTS[k] * v for k, v in parts.items()))
    return Nota(side=side, score=score, prob=round(prob, 4), fair=round(fair, 4),
                parts={k: round(v, 3) for k, v in parts.items()}, reasons=_reasons(a, trends, ctx, side))


def _clip(x: float) -> float:
    return max(0.0, min(1.0, x))


def _side_rate(rate: float | None, side: str) -> float | None:
    """% de partidos en los que ganó ese lado (el "menos" es lo contrario del "más")."""
    if rate is None:
        return None
    return rate if side == "over" else 1 - rate


def _best_ev(a: dict, side: str, prob: float) -> float:
    """Valor esperado con la mejor cuota de ese lado en la misma línea (casas de The Odds API)."""
    key = "over_odds" if side == "over" else "under_odds"
    odds = [b[key] for b in a.get("books") or [] if b.get("line") == a.get("line") and (b.get(key) or 0) > 1]
    return max(odds) * prob - 1 if odds else 0.0


def _form(t: dict, side: str) -> float:
    rates = [_side_rate(t.get("hit_rate_last10"), side)]
    if (t.get("season_games") or 0) >= 5:
        rates.append(_side_rate(t.get("hit_rate_season"), side))
    rates = [r for r in rates if r is not None]
    return _clip((sum(rates) / len(rates) - 0.5) / FULL_HIT_EDGE) if rates else 0.0


def _matchup(t: dict, ctx: dict, side: str, sign: int) -> float:
    scores = []
    splits = t.get("splits") or {}
    venue = {True: "home", False: "away"}.get(ctx.get("home"))
    for key in ("vs_opponent", venue):
        s = splits.get(key) if key else None
        if s and (s.get("games") or 0) >= MIN_SPLIT_GAMES and s.get("hit_rate") is not None:
            scores.append(_clip((_side_rate(s["hit_rate"], side) - 0.5) / FULL_HIT_EDGE))
    factor = ctx.get("opponent_factor")
    if factor and factor != 1.0:
        scores.append(_clip(sign * (factor - 1) / FULL_OPP_FACTOR))
    return sum(scores) / len(scores) if scores else 0.0


def _reliability(t: dict, ctx: dict) -> float:
    games = _clip((t.get("games") or 0) / 20)
    season = _clip((t.get("season_games") or 0) / 10)
    m5, ms = t.get("minutes_last5"), t.get("minutes_season")
    minutes = 1 - _clip(abs(m5 / ms - 1) / 0.3) if m5 and ms else 0.5
    health = 0.5 if str(ctx.get("injury_status") or "").lower() in ("questionable", "day-to-day") else 1.0
    return games * season * (0.5 + 0.5 * minutes) * health


def _reasons(a: dict, t: dict, ctx: dict, side: str) -> list[str]:
    """Hasta tres frases cortas con los datos que apoyan el lado (para la tarjeta)."""
    stat = STAT_LABELS.get(a.get("stat"), a.get("stat", ""))
    line = _num(a.get("line"))
    verb = "Superó" if side == "over" else "Se quedó por debajo de"
    out = []
    r10 = _side_rate(t.get("hit_rate_last10"), side)
    if r10 is not None and len(t.get("recent_values") or []) >= 10:
        out.append(f"{verb} {line} en {round(r10 * 10)} de sus últimos 10 partidos.")
    if t.get("last10") is not None:
        out.append(f"Media de {_num(t['last10'])} {stat} en los últimos 10.")
    venue = {True: ("home", "En casa"), False: ("away", "Fuera")}.get(ctx.get("home"))
    if venue:
        s = (t.get("splits") or {}).get(venue[0]) or {}
        if (s.get("games") or 0) >= MIN_SPLIT_GAMES and s.get("avg") is not None:
            out.append(f"{venue[1]}, {_num(s['avg'])} de media en {s['games']} partidos.")
    factor = ctx.get("opponent_factor")
    if factor and abs(factor - 1) >= 0.02 and ctx.get("opponent"):
        more = "más" if factor > 1 else "menos"
        out.append(f"{ctx['opponent']} concede un {abs(round((factor - 1) * 100))} % {more} de puntos que la media.")
    return out[:3]


def _num(x) -> str:
    if x is None:
        return "-"
    return f"{x:.1f}".replace(".", ",").replace(",0", "") if isinstance(x, float) else str(x)
