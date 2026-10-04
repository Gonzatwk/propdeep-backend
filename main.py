"""API de PropDeep: análisis de player props de la NBA con datos reales e historial público."""
from __future__ import annotations

from datetime import date
from functools import lru_cache

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from propdeep.clients.balldontlie import BalldontlieClient
from propdeep.clients.odds import OddsClient
from propdeep.config import Settings, get_settings
from propdeep.db import all_predictions, make_session_factory, publish
from propdeep.narrative import write_report
from propdeep.pipeline import Analyzer, scan_day
from propdeep.track_record import settle, summary

DISCLAIMER = (
    "Análisis estadístico con fines informativos para mayores de 18 años. "
    "No es una apuesta segura: apostar implica riesgo de perder dinero."
)

app = FastAPI(title="PropDeep API", version="2.0.0")
_settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _settings.cors_origins.split(",")],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@lru_cache
def settings() -> Settings:
    return get_settings()


@lru_cache
def session_factory():
    return make_session_factory(settings().database_url)


@lru_cache
def bdl_client() -> BalldontlieClient:
    s = settings()
    if not s.balldontlie_api_key:
        raise HTTPException(503, "Falta BALLDONTLIE_API_KEY")
    return BalldontlieClient(s.balldontlie_api_key)


@lru_cache
def odds_client() -> OddsClient:
    s = settings()
    if not s.odds_api_key:
        raise HTTPException(503, "Falta ODDS_API_KEY")
    return OddsClient(s.odds_api_key, s.odds_regions)


@lru_cache
def claude_client():
    import os

    if not (os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN")):
        return None  # sin clave: informe con plantilla
    import anthropic

    return anthropic.Anthropic()


def analyzer() -> Analyzer:
    s = settings()
    return Analyzer(bdl_client(), s.current_season, s.min_edge, s.model_weight)


def require_admin(x_admin_token: str = Header(default="")) -> None:
    token = settings().admin_token
    if not token or x_admin_token != token:
        raise HTTPException(401, "Token de administración no válido")


class PropRequest(BaseModel):
    player: str = Field(examples=["Luka Doncic"])
    stat: str = Field(pattern="^(pts|reb|ast|fg3m)$", examples=["pts"])
    line: float = Field(examples=[28.5])
    over_odds: float = Field(gt=1.0, examples=[1.87])
    under_odds: float = Field(gt=1.0, examples=[1.95])
    game_date: date
    bookmaker: str | None = None


def _run(req: PropRequest, an: Analyzer) -> tuple[dict, str, dict]:
    try:
        result, meta = an.analyze_prop(
            req.player, req.stat, req.line, req.over_odds, req.under_odds, req.game_date
        )
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    report = write_report(result, claude_client(), settings().anthropic_model)
    meta["bookmaker"] = req.bookmaker
    return result.to_dict(), report, meta


@app.get("/")
def home():
    return {"service": "PropDeep API", "version": app.version, "disclaimer": DISCLAIMER}


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/analyze")
def analyze_prop(req: PropRequest, an: Analyzer = Depends(analyzer)):
    """Analiza una prop sin publicarla en el historial."""
    analysis, report, _ = _run(req, an)
    return {"analysis": analysis, "report": report, "disclaimer": DISCLAIMER}


@app.post("/admin/publish", dependencies=[Depends(require_admin)])
def publish_prop(req: PropRequest, an: Analyzer = Depends(analyzer)):
    """Analiza y publica en el historial. Lo publicado ya no se puede editar."""
    analysis, report, meta = _run(req, an)
    with session_factory()() as session:
        pred = publish(session, analysis=analysis, report=report, meta=meta)
        return _public(pred)


@app.get("/admin/scan", dependencies=[Depends(require_admin)])
def scan(game_date: date, max_events: int = 3, top: int = 10, an: Analyzer = Depends(analyzer)):
    """Analiza las props de la jornada (consume créditos de The Odds API) y devuelve las mejores."""
    results = scan_day(an, odds_client(), game_date, max_events=max_events)
    return [
        {"analysis": a.to_dict(), "bookmaker": prop.bookmaker, "event": f"{prop.away_team} @ {prop.home_team}"}
        for a, _, prop in results[:top]
    ]


@app.post("/admin/settle", dependencies=[Depends(require_admin)])
def settle_pending():
    with session_factory()() as session:
        done = settle(session, bdl_client())
        return {"settled": [_public(p) for p in done]}


@app.get("/predictions")
def predictions(limit: int = 200):
    """Historial público completo, ganadas y perdidas."""
    with session_factory()() as session:
        return [_public(p) for p in all_predictions(session, limit)]


@app.get("/track-record")
def track_record():
    with session_factory()() as session:
        return {**summary(all_predictions(session, limit=100_000)), "disclaimer": DISCLAIMER}


def _public(p) -> dict:
    return {
        "id": p.id,
        "published_at": p.published_at.isoformat(),
        "game_date": p.game_date,
        "player": p.player_name,
        "stat": p.stat,
        "line": p.line,
        "side": p.side,
        "odds": p.odds,
        "bookmaker": p.bookmaker,
        "probability": round(p.prob, 4),
        "edge": p.edge,
        "confidence": p.confidence,
        "report": p.report,
        "status": p.status,
        "actual": p.actual,
        "content_hash": p.content_hash,
    }
