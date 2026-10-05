"""Redacción del informe en español con la API de Claude.

Los números los calcula el modelo; Claude solo los explica. Si no hay clave de API
o la llamada falla, se usa una plantilla para que el informe no dependa de Claude.
"""
from __future__ import annotations

import json
import logging

from .model import STAT_LABELS, Analysis

log = logging.getLogger(__name__)

SYSTEM_PROMPT = """Eres el analista de PropDeep, una herramienta en español de análisis \
estadístico de player props de la NBA para España y Latinoamérica.

Recibes un JSON con los datos de una línea. Escribe un informe de análisis:
- 4 a 6 frases en español neutro, claras, sin jerga innecesaria.
- Cubre, si hay datos: la proyección frente a la línea, cuántas veces superó la línea \
(últimos 5, últimos 10, temporada), en casa y fuera, contra este rival, minutos y rol, \
rival y contexto (back-to-back, lesiones), y si las casas ofrecen líneas distintas.
- Usa solo los números del JSON. No inventes estadísticas, lesiones ni noticias.
- Es información orientativa, no una recomendación: no digas qué apostar, no hables de \
"valor", "ventaja", "pick" ni "confianza", y nunca digas "seguro", "fijo" ni \
"ganancia garantizada". Señala también los datos que van en contra de la tendencia.
Devuelve solo el texto del informe, sin títulos ni listas."""

# Campos internos del modelo que no salen al público: el backtest no mostró ventaja.
VERDICT_FIELDS = ("side", "edge", "odds_taken", "expected_value", "confidence",
                  "prob_over_model", "prob_over_market", "prob_over_final", "reasons")


def facts(analysis: Analysis, books: list[dict] | None = None) -> dict:
    data = {k: v for k, v in analysis.to_dict().items() if k not in VERDICT_FIELDS}
    if books:
        data["books"] = books
    return data


def write_report(analysis: Analysis, client=None, model: str = "claude-opus-5-5",
                 books: list[dict] | None = None) -> str:
    if client is None:
        return template_report(analysis)
    payload = json.dumps(facts(analysis, books), ensure_ascii=False, sort_keys=True)
    try:
        response = client.beta.messages.create(
            model=model,
            max_tokens=2000,
            system=SYSTEM_PROMPT,
            output_config={"effort": "medium"},
            # Si un clasificador de seguridad rechaza la petición, la API reintenta
            # con el modelo de respaldo que corresponda en la misma llamada.
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            messages=[{"role": "user", "content": f"Datos:\n{payload}"}],
        )
    except Exception as exc:  # noqa: BLE001 - el informe nunca debe romper el análisis
        log.warning("Fallo al redactar con Claude, uso plantilla: %s", exc)
        return template_report(analysis)
    if response.stop_reason == "refusal":
        return template_report(analysis)
    text = "".join(b.text for b in response.content if b.type == "text").strip()
    return text or template_report(analysis)


def _n(x: float, digits: int = 1) -> str:
    """Número con coma decimal, como se escribe en español."""
    return f"{round(x, digits):g}".replace(".", ",")


def _pct(x: float) -> str:
    return f"{round(x * 100)} %"


def template_report(a: Analysis) -> str:
    label = STAT_LABELS.get(a.stat, a.stat)
    t = a.trends
    parts = [f"{a.player}: línea de {_n(a.line)} {label}. Nuestra proyección es de {_n(a.projection)}."]
    rates = [(f"los últimos {min(n, t.games)}", r) for n, r in ((5, t.hit_rate_last5), (10, t.hit_rate_last10)) if r is not None]
    if t.hit_rate_season is not None and t.season_games >= 5:
        rates.append((f"los {t.season_games} de esta temporada", t.hit_rate_season))
    if rates:
        texto = ", ".join(f"el {_pct(r)} de {w}" for w, r in rates)
        parts.append(f"Superó la línea en {texto}.")
    if t.last10 is not None:
        parts.append(f"Promedia {_n(t.last10)} en sus últimos {min(t.games, 10)} partidos.")
    s = t.splits or {}
    home, away, vs = s.get("home") or {}, s.get("away") or {}, s.get("vs_opponent") or {}
    if home.get("games") and away.get("games"):
        parts.append(f"En casa promedia {_n(home['avg'])} y fuera {_n(away['avg'])}.")
    if a.context.opponent:
        where = "en casa" if a.context.home else "fuera" if a.context.home is False else ""
        b2b = ", en back-to-back" if a.context.back_to_back else ""
        parts.append(f"Juega {where} contra {a.context.opponent}{b2b}.".replace("Juega  ", "Juega "))
    if vs.get("games"):
        n = vs["games"]
        parts.append(f"Contra este rival promedia {_n(vs['avg'])} en {n} {'partido' if n == 1 else 'partidos'} recientes.")
    if t.minutes_last5 and t.minutes_season:
        parts.append(f"Minutos: {_n(t.minutes_last5)} en los últimos 5 frente a {_n(t.minutes_season)} de media.")
    parts.extend(a.reasons)
    parts.append("Es información orientativa, no una recomendación de apuesta.")
    return " ".join(parts)
