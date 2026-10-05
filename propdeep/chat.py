"""Chat en español sobre los datos de la jornada (para suscriptores).

Claude responde con herramientas que leen la zona de partidos: no inventa números y no
ve el veredicto interno del modelo. Es información orientativa, nunca un pick.
No se guardan las conversaciones; solo cuántos mensajes manda cada usuario al día.
"""
from __future__ import annotations

import json
import logging
import unicodedata
from datetime import date, datetime, timezone

from sqlalchemy import Date, ForeignKey, Integer
from sqlalchemy.orm import Mapped, Session, mapped_column

from . import board
from .db import Base, Prediction

log = logging.getLogger(__name__)

MAX_TURNS = 12  # mensajes previos que se reenvían (usuario + asistente)
MAX_TEXT = 2000  # caracteres por mensaje
MAX_TOOL_ROUNDS = 6
MAX_LINES = 40

STATS = {"pts": "puntos", "reb": "rebotes", "ast": "asistencias", "fg3m": "triples"}

SYSTEM_PROMPT = """Eres el asistente de PropDeep, una herramienta en español de análisis estadístico \
de player props de la NBA para España y Latinoamérica. Respondes preguntas sobre los partidos \
y las líneas de la jornada con los datos de PropDeep.

Cómo trabajas:
- Consulta siempre las herramientas antes de dar un número. Usa solo lo que devuelven; si un \
dato no está, dilo. No inventes estadísticas, lesiones, noticias ni cuotas.
- Datos que tienes de cada línea: la línea y las cuotas de cada casa, nuestra proyección, el % de \
partidos por encima de la línea (últimos 5, últimos 10, esta temporada y la anterior), el \
desglose en casa, fuera y contra el rival, medias, minutos, rival, back-to-back, lesiones y el \
informe escrito.
- Para comparar casas: para el más es mejor la línea más baja (a igualdad, la cuota más alta); \
para el menos, la línea más alta. Recuerda que las cuotas cambian.

Límites que no se negocian:
- Es información orientativa, no una recomendación. No digas qué apostar ni elijas un lado por \
el usuario, no hables de "valor", "ventaja", "pick", "fijo", "seguro" ni "ganancia \
garantizada". Si te piden una apuesta, explica qué dicen los datos a favor y en contra y \
recuerda que la decisión y el riesgo son suyos.
- Apostar implica riesgo de perder dinero y a largo plazo es muy difícil ganar a la casa. Si \
alguien habla de recuperar pérdidas, apostar más de lo que puede o perder el control, responde \
con tacto y recomienda jugarbien.es.
- Solo hablas de la NBA y de los datos de PropDeep.

Formato: español neutro, frases cortas, sin títulos ni tablas. Para listas usa líneas que \
empiecen por "- ". Números con coma decimal (27,5). Sé breve: 2 a 6 frases salvo que pidan más."""

TOOLS = [
    {
        "name": "partidos",
        "description": "Partidos de una jornada con su hora (UTC), equipos y cuántas líneas hay. "
                       "Sin fecha, la jornada actual.",
        "input_schema": {
            "type": "object",
            "properties": {"fecha": {"type": "string", "description": "AAAA-MM-DD (opcional)"}},
            "additionalProperties": False,
        },
    },
    {
        "name": "buscar_lineas",
        "description": "Busca líneas de la jornada por jugador, equipo, partido o estadística. "
                       "Devuelve por cada una: id, jugador, partido, línea, cuotas de referencia, "
                       "proyección, % por encima de la línea y la mejor línea de cada lado entre casas.",
        "input_schema": {
            "type": "object",
            "properties": {
                "jugador": {"type": "string", "description": "Nombre o parte del nombre"},
                "equipo": {"type": "string", "description": "Nombre o parte del nombre del equipo, p. ej. Lakers"},
                "partido_id": {"type": "string"},
                "estadistica": {"type": "string", "enum": list(STATS)},
                "orden": {
                    "type": "string",
                    "enum": ["hora", "mas_veces_por_encima", "menos_veces_por_encima"],
                    "description": "Por % de los últimos 10 partidos por encima de la línea, o por hora",
                },
                "fecha": {"type": "string", "description": "AAAA-MM-DD (opcional)"},
                "limite": {"type": "integer", "minimum": 1, "maximum": MAX_LINES,
                           "description": "Cuántas líneas devolver (10 por defecto)"},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "detalle_linea",
        "description": "Todo el análisis de una línea por su id: líneas y cuotas de cada casa, "
                       "desglose casa/fuera/rival, medias, minutos, contexto, últimos partidos e informe.",
        "input_schema": {
            "type": "object",
            "properties": {"id": {"type": "integer"}},
            "required": ["id"],
            "additionalProperties": False,
        },
    },
]


class ChatUsage(Base):
    """Mensajes de chat por usuario y día (para el límite diario). Sin el contenido."""

    __tablename__ = "chat_usage"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    day: Mapped[date] = mapped_column(Date, primary_key=True)
    count: Mapped[int] = mapped_column(Integer, default=0)


class LimitReached(Exception):
    pass


def take_message(session: Session, user_id: int, limit: int, today: date | None = None) -> int:
    """Cuenta un mensaje; LimitReached si ya llegó al tope de hoy. Devuelve los que quedan."""
    today = today or datetime.now(timezone.utc).date()
    row = session.get(ChatUsage, (user_id, today))
    if row is None:
        row = ChatUsage(user_id=user_id, day=today, count=0)
        session.add(row)
    if row.count >= limit:
        raise LimitReached
    row.count += 1
    session.commit()
    return limit - row.count


def give_back(session: Session, user_id: int) -> None:
    """Devuelve el mensaje si la respuesta falló por nuestra parte."""
    row = session.get(ChatUsage, (user_id, datetime.now(timezone.utc).date()))
    if row and row.count > 0:
        row.count -= 1
        session.commit()


def remaining(session: Session, user_id: int, limit: int) -> int:
    row = session.get(ChatUsage, (user_id, datetime.now(timezone.utc).date()))
    return max(0, limit - (row.count if row else 0))


# --- Herramientas -------------------------------------------------------------------------

def _norm(text: str | None) -> str:
    ascii_text = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode()
    return " ".join(ascii_text.lower().replace(".", "").split())


def _day(session: Session, fecha: str | None) -> str | None:
    if fecha:
        try:
            return date.fromisoformat(fecha).isoformat()
        except ValueError:
            return None
    return board.default_date(session)


def _line_row(p: Prediction) -> dict:
    s = board.line_summary(p, True)
    g = board.game_header(p)
    return {
        "id": p.id,
        "jugador": p.player_name,
        "estadistica": STATS.get(p.stat, p.stat),
        "partido": f"{g['away_team']} @ {g['home_team']}",
        "partido_id": p.event_id,
        "hora_utc": g["commence_time"],
        "linea": p.line,
        "cuotas_referencia": {"mas": s["over_odds"], "menos": s["under_odds"], "casa": p.bookmaker},
        "casas": s["books_count"],
        "proyeccion": s["projection"],
        "por_encima": s["hit_rates"],
        "mejor_entre_casas": s["best"],
    }


def run_tool(session: Session, name: str, args: dict) -> dict:
    if name == "partidos":
        day = _day(session, args.get("fecha"))
        if not day:
            return {"error": "No hay jornadas publicadas todavía (la temporada empieza el 20 de octubre)."}
        return {"fecha": day, "partidos": board.games(board.board_lines(session, game_date=day))}

    if name == "buscar_lineas":
        day = _day(session, args.get("fecha"))
        if not day and not args.get("partido_id"):
            return {"error": "No hay jornadas publicadas todavía."}
        lines = board.board_lines(session, game_date=None if args.get("partido_id") else day,
                                  event_id=args.get("partido_id"))
        if args.get("estadistica"):
            lines = [p for p in lines if p.stat == args["estadistica"]]
        if args.get("jugador"):
            wanted = _norm(args["jugador"])
            lines = [p for p in lines if wanted in _norm(p.player_name)]
        if args.get("equipo"):
            wanted = _norm(args["equipo"])
            lines = [p for p in lines if wanted in _norm(p.home_team) or wanted in _norm(p.away_team)]
        rows = [_line_row(p) for p in lines]
        orden = args.get("orden")
        if orden in ("mas_veces_por_encima", "menos_veces_por_encima"):
            rows = [r for r in rows if r["por_encima"]["last10"] is not None]
            rows.sort(key=lambda r: r["por_encima"]["last10"], reverse=orden == "mas_veces_por_encima")
        limit = min(int(args.get("limite") or 10), MAX_LINES)
        return {"fecha": day, "total": len(rows), "lineas": rows[:limit]}

    if name == "detalle_linea":
        p = session.get(Prediction, args.get("id"))
        if p is None or not p.event_id:
            return {"error": "No existe esa línea."}
        d = board.line_detail(p)
        d.pop("content_hash", None)
        return d

    return {"error": f"Herramienta desconocida: {name}"}


# --- Conversación -------------------------------------------------------------------------

def clean_history(messages: list[dict]) -> list[dict]:
    """Solo texto, roles alternos, empezando por el usuario y acabando en él."""
    out: list[dict] = []
    for m in messages[-MAX_TURNS:]:
        role, text = m.get("role"), str(m.get("content") or "").strip()[:MAX_TEXT]
        if role not in ("user", "assistant") or not text:
            continue
        if out and out[-1]["role"] == role:
            out[-1]["content"] += "\n\n" + text
        else:
            out.append({"role": role, "content": text})
    while out and out[0]["role"] != "user":
        out.pop(0)
    return out


def answer(session: Session, history: list[dict], client, model: str, effort: str = "medium") -> str:
    """Bucle de herramientas: Claude consulta los datos y responde en español."""
    messages = clean_history(history)
    if not messages or messages[-1]["role"] != "user":
        raise ValueError("Falta la pregunta")
    for _ in range(MAX_TOOL_ROUNDS):
        response = client.beta.messages.create(
            model=model,
            max_tokens=16000,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
            output_config={"effort": effort},
            # Cachea el prefijo estable (herramientas y sistema) entre preguntas.
            cache_control={"type": "ephemeral"},
            # Si un clasificador rechaza la petición, la API reintenta con el modelo de
            # respaldo que corresponda en la misma llamada.
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
        if response.stop_reason == "refusal":
            return "No puedo ayudarte con eso. Pregúntame por los partidos y las líneas de la jornada."
        if response.stop_reason != "tool_use":
            text = "".join(b.text for b in response.content if b.type == "text").strip()
            return text or "No he encontrado una respuesta. Prueba a preguntarlo de otra forma."
        messages.append({"role": "assistant", "content": response.content})
        results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            try:
                data = run_tool(session, block.name, dict(block.input or {}))
                results.append({"type": "tool_result", "tool_use_id": block.id,
                                "content": json.dumps(data, ensure_ascii=False, default=str)})
            except Exception as exc:  # noqa: BLE001 - un fallo de datos no debe tumbar el chat
                log.warning("Fallo en la herramienta %s: %s", block.name, exc)
                results.append({"type": "tool_result", "tool_use_id": block.id,
                                "content": "No se pudieron leer esos datos.", "is_error": True})
        messages.append({"role": "user", "content": results})
    return "La pregunta necesita demasiadas consultas. Prueba a concretar el partido o el jugador."
