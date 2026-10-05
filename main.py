"""API de PropDeep: análisis de player props de la NBA con datos reales e historial público."""
from __future__ import annotations

from datetime import date
from functools import lru_cache

from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from propdeep import accounts, billing, board
from propdeep.clients.balldontlie import BalldontlieClient
from propdeep.clients.odds import OddsClient
from propdeep.config import Settings, get_settings
from propdeep.db import Prediction, all_predictions, make_session_factory, publish
from propdeep.mailer import send_login_link
from propdeep.narrative import template_report, write_report
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
    allow_methods=["GET", "POST", "DELETE"],
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
    """Historial público completo, ganadas y perdidas.

    Las líneas de la zona de partidos que aún no han empezado salen con su hash pero sin
    el veredicto (es lo que paga el suscriptor); al empezar el partido se ve todo."""
    with session_factory()() as session:
        return [_public(p) for p in all_predictions(session, limit)]


@app.get("/track-record")
def track_record():
    with session_factory()() as session:
        return {**summary(all_predictions(session, limit=100_000)), "disclaimer": DISCLAIMER}


def _public(p) -> dict:
    if p.event_id and not board.is_unlocked(p, subscriber=False):
        return {
            "id": p.id,
            "published_at": p.published_at.isoformat(),
            "game_date": p.game_date,
            "player": p.player_name,
            "stat": p.stat,
            "line": p.line,
            "bookmaker": p.bookmaker,
            "hidden": True,
            "status": p.status,
            "content_hash": p.content_hash,
        }
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


# --- Cuentas (solo correo, enlace mágico) -------------------------------------------------

class LoginRequest(BaseModel):
    email: str = Field(max_length=254)


class VerifyRequest(BaseModel):
    token: str = Field(max_length=200)


def _bearer(authorization: str = Header(default="")) -> str:
    scheme, _, token = authorization.partition(" ")
    return token.strip() if scheme.lower() == "bearer" else ""


def current_user(token: str = Depends(_bearer)):
    """Usuario de la sesión, o None si no ha entrado. Se lee en su propia sesión de BD."""
    if not token:
        return None
    with session_factory()() as session:
        return accounts.user_from_token(session, token)


def require_user(user=Depends(current_user)):
    if user is None:
        raise HTTPException(401, "Tienes que entrar con tu correo")
    return user


@app.post("/auth/login", status_code=202)
def login(req: LoginRequest, background: BackgroundTasks):
    """Manda el enlace de acceso. Responde igual exista o no la cuenta."""
    email = accounts.normalize_email(req.email)
    if not email:
        raise HTTPException(422, "Correo no válido")
    with session_factory()() as session:
        try:
            token = accounts.request_login(session, email)
        except accounts.RateLimited:
            raise HTTPException(429, "Demasiados intentos. Espera un rato y vuelve a probar.") from None
    background.add_task(send_login_link, settings(), email, f"{settings().web_url}/entrar?token={token}")
    return {"ok": True}


class WaitlistRequest(BaseModel):
    email: str = Field(max_length=254)
    source: str | None = Field(default=None, max_length=40)


@app.post("/waitlist", status_code=201)
def waitlist(req: WaitlistRequest):
    """Lista de aviso de la landing: solo guarda el correo."""
    email = accounts.normalize_email(req.email)
    if not email:
        raise HTTPException(422, "Correo no válido")
    with session_factory()() as session:
        accounts.join_waitlist(session, email, req.source)
    return {"ok": True}


@app.get("/admin/metrics", dependencies=[Depends(require_admin)])
def admin_metrics():
    """Cuántos empiezan la prueba de 7 días y cuántos pasan a pago."""
    with session_factory()() as session:
        return accounts.metrics(session)


@app.post("/auth/verify")
def verify(req: VerifyRequest):
    with session_factory()() as session:
        result = accounts.verify_login(session, req.token)
        if result is None:
            raise HTTPException(400, "El enlace no es válido o ha caducado. Pide otro.")
        user, session_token = result
        return {"token": session_token, "user": accounts.public_user(user)}


@app.post("/auth/logout")
def do_logout(token: str = Depends(_bearer)):
    with session_factory()() as session:
        accounts.logout(session, token)
    return {"ok": True}


@app.get("/me")
def me(user=Depends(require_user)):
    return accounts.public_user(user)


@app.delete("/me")
def delete_me(user=Depends(require_user)):
    """Borra la cuenta (RGPD). Con una suscripción activa, primero hay que cancelarla."""
    if accounts.is_subscriber(user) and not user.cancel_at_period_end:
        raise HTTPException(409, "Cancela antes la suscripción desde «Gestionar suscripción».")
    with session_factory()() as session:
        accounts.delete_user(session, session.merge(user))
    return {"ok": True}


# --- Suscripción con Stripe ---------------------------------------------------------------

class CheckoutRequest(BaseModel):
    plan: str = Field(pattern="^(monthly|yearly)$")


@app.post("/billing/checkout")
def checkout(req: CheckoutRequest, user=Depends(require_user)):
    s = settings()
    price = s.stripe_price_monthly if req.plan == "monthly" else s.stripe_price_yearly
    if not (s.stripe_secret_key and price):
        raise HTTPException(503, "La suscripción todavía no está activada")
    if accounts.is_subscriber(user):
        raise HTTPException(409, "Ya tienes una suscripción activa")
    url = billing.create_checkout(user, req.plan, secret_key=s.stripe_secret_key, price_id=price, web_url=s.web_url)
    return {"url": url}


@app.post("/billing/portal")
def portal(user=Depends(require_user)):
    s = settings()
    if not (s.stripe_secret_key and user.stripe_customer_id):
        raise HTTPException(404, "No hay ninguna suscripción que gestionar")
    return {"url": billing.create_portal(user, secret_key=s.stripe_secret_key, web_url=s.web_url)}


@app.post("/stripe/webhook")
async def stripe_webhook(request: Request, stripe_signature: str = Header(default="")):
    secret = settings().stripe_webhook_secret
    if not secret:
        raise HTTPException(503, "Falta STRIPE_WEBHOOK_SECRET")
    try:
        event = billing.parse_webhook(await request.body(), stripe_signature, secret)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    with session_factory()() as session:
        billing.apply_event(session, event)
    return {"received": True}


# --- Zona de partidos ---------------------------------------------------------------------

def _viewer(user) -> dict:
    return {"logged_in": user is not None, "subscriber": accounts.is_subscriber(user)}


@app.get("/board")
def get_board(game_date: date | None = None, user=Depends(current_user)):
    """Partidos de una jornada (por defecto, la próxima con partidos por jugar)."""
    with session_factory()() as session:
        day = game_date.isoformat() if game_date else board.default_date(session)
        lines = board.board_lines(session, game_date=day) if day else []
        return {
            "game_date": day,
            "dates": board.board_dates(session),
            "free_lines_per_day": settings().free_lines_per_day,
            "viewer": _viewer(user),
            "games": board.games(lines),
            "disclaimer": DISCLAIMER,
        }


@app.get("/board/games/{event_id}")
def get_game(event_id: str, user=Depends(current_user)):
    """Jugadores del partido con sus líneas. Bloqueadas: sin veredicto ni probabilidades."""
    subscriber = accounts.is_subscriber(user)
    with session_factory()() as session:
        lines = board.board_lines(session, event_id=event_id)
        if not lines:
            raise HTTPException(404, "Partido no encontrado")
        return {
            "game": board.game_header(lines[0]),
            "viewer": _viewer(user),
            "lines": [board.line_summary(p, board.is_unlocked(p, subscriber)) for p in lines],
            "disclaimer": DISCLAIMER,
        }


@app.get("/board/lines/{line_id}")
def get_line(line_id: int, user=Depends(current_user)):
    """Informe completo de una línea. 402 si hace falta suscripción."""
    with session_factory()() as session:
        p = session.get(Prediction, line_id)
        if p is None or not p.event_id:
            raise HTTPException(404, "Línea no encontrada")
        if not board.is_unlocked(p, accounts.is_subscriber(user)):
            raise HTTPException(402, "Este informe es para suscriptores")
        return {**board.line_detail(p), "disclaimer": DISCLAIMER}


@app.post("/admin/board", dependencies=[Depends(require_admin)])
def build_board(game_date: date, max_events: int | None = None, an: Analyzer = Depends(analyzer)):
    """Analiza todas las props de la jornada y las publica en la zona de partidos.

    Consume créditos de The Odds API (4 por partido en "eu"). Claude solo redacta las
    líneas con ventaja; el resto lleva el informe de plantilla para no disparar el coste."""
    results = scan_day(an, odds_client(), game_date, max_events=max_events)

    def report(a):
        return write_report(a, claude_client(), settings().anthropic_model) if a.side else template_report(a)

    with session_factory()() as session:
        published = board.publish_board(session, results, game_date, settings().free_lines_per_day, report)
        return {"published": len(published), "free": sum(1 for p in published if p.free)}
