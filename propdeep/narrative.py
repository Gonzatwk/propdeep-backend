"""Redacción del informe en español con la API de Claude.

Los números los calcula el modelo; Claude solo los explica. Si no hay clave de API
o la llamada falla, se usa una plantilla para que el informe no dependa de Claude.
"""
from __future__ import annotations

import json
import logging

from .model import STAT_LABELS, Analysis

log = logging.getLogger(__name__)

SYSTEM_PROMPT = """Eres el analista de PropDeep, un servicio en español de análisis estadístico \
de player props de la NBA para apostadores de España y Latinoamérica.

Recibes un JSON con un análisis ya calculado. Escribe el informe para el suscriptor:
- 4 a 6 frases en español neutro, claras, sin jerga innecesaria.
- Cubre, si hay datos: tendencia reciente frente a la línea, minutos y rol, rival y \
contexto (local/visitante, back-to-back, lesiones), y la comparación entre nuestra \
probabilidad y la que implica la cuota.
- Usa solo los números del JSON. No inventes estadísticas, lesiones ni noticias.
- Si "side" es null, di claramente que no vemos ventaja y que no recomendamos jugarla.
- Nunca digas "pick seguro", "fijo", "ganancia garantizada" ni nada parecido. Habla de \
probabilidades y riesgo.
- Termina con una frase con el nivel de confianza y su porqué.
Devuelve solo el texto del informe, sin títulos ni listas."""


def write_report(analysis: Analysis, client=None, model: str = "claude-opus-5-5") -> str:
    if client is None:
        return template_report(analysis)
    facts = json.dumps(analysis.to_dict(), ensure_ascii=False, sort_keys=True)
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
            messages=[{"role": "user", "content": f"Análisis:\n{facts}"}],
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


def template_report(a: Analysis) -> str:
    label = STAT_LABELS.get(a.stat, a.stat)
    t = a.trends
    parts = [
        f"{a.player}: línea de {_n(a.line)} {label}. Proyectamos {_n(a.projection)}.",
    ]
    if t.last10 is not None:
        hit = f" y superó la línea en el {round((t.hit_rate_last10 or 0) * 100)} % de ellos" if t.hit_rate_last10 is not None else ""
        parts.append(f"Promedia {_n(t.last10)} en sus últimos {min(t.games, 10)} partidos{hit}.")
    if a.context.opponent:
        where = "en casa" if a.context.home else "fuera" if a.context.home is False else ""
        b2b = ", en back-to-back" if a.context.back_to_back else ""
        parts.append(f"Juega {where} contra {a.context.opponent}{b2b}.".replace("Juega  ", "Juega "))
    p_over = _n(a.prob_over_final * 100)
    p_market = _n(a.prob_over_market * 100)
    parts.append(f"Estimamos un {p_over} % para el más frente al {p_market} % que marca el mercado sin margen.")
    if a.side is None:
        parts.extend(a.reasons)
        parts.append("Sin ventaja: no recomendamos jugar esta prop.")
    else:
        parts.append(
            f"Vemos valor en el {'más' if a.side == 'over' else 'menos'} a cuota {f'{a.odds_taken:.2f}'.replace('.', ',')} "
            f"(ventaja de {_n(a.edge * 100)} puntos). Confianza {a.confidence}."
        )
    return " ".join(parts)
