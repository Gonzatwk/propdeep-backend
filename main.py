"""API de PropDeep: análisis de player props de la NBA con datos reales (información orientativa)."""
from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import date, datetime
from functools import lru_cache

from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from propdeep import accounts, auto, billing, board, chat, moneyline, paper, picks, tipsters
from propdeep.clients.balldontlie import BalldontlieClient
from propdeep.clients.odds import OddsClient
from propdeep.config import Settings, get_settings
from propdeep.db import Prediction, all_predictions, make_session_factory, publish
from propdeep.mailer import send_login_link, send_trial_reminder
from propdeep.narrative import template_report, write_report
from propdeep.pipeline import Analyzer, scan_day
from propdeep.track_record import settle, summary

DISCLAIMER = (
    "Información estadística orientativa para mayores de 18 años. No es una recomendación de "
    "apuesta ni garantiza ganar: apostar implica riesgo de perder dinero."
)

@asynccontextmanager
async def lifespan(_app):
    start_auto_jornada()
    yield


app = FastAPI(title="PropDeep API", version="2.0.0", lifespan=lifespan)
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


@app.post("/admin/analyze", dependencies=[Depends(require_admin)])
def analyze_prop(req: PropRequest, an: Analyzer = Depends(analyzer)):
    """Analiza una prop sin publicarla en el historial. Solo admin: devuelve el veredicto interno
    y cada llamada gasta Balldontlie y Claude."""
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
    """Liquida predicciones del modelo y picks con el resultado final de Balldontlie."""
    with session_factory()() as session:
        done = settle(session, bdl_client())
        out = []
        for p in done:
            if isinstance(p, picks.Parlay):
                out.append(picks.public_parlay(p, picks.legs_of(session, p.id)))
            else:
                out.append(picks.public(p) if isinstance(p, picks.Pick) else _public(p))
        return {"settled": out}


@app.get("/admin/predictions", dependencies=[Depends(require_admin)])
def predictions(limit: int = 200):
    """Veredictos internos del modelo, para seguir midiéndolo. No se enseñan al público:
    el backtest de 2025-26 no mostró ventaja y la web no los presenta como picks."""
    with session_factory()() as session:
        return [_public(p) for p in all_predictions(session, limit)]


@app.get("/admin/track-record", dependencies=[Depends(require_admin)])
def track_record():
    with session_factory()() as session:
        return summary(all_predictions(session, limit=100_000))


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
    """Manda el enlace de acceso. Responde igual exista o no la cuenta.

    En el PC (LOCAL_LOGIN con WEB_URL en localhost), a los correos de ADMIN_EMAILS les
    devuelve el token directamente para entrar sin correo."""
    email = accounts.normalize_email(req.email)
    if not email:
        raise HTTPException(422, "Correo no válido")
    with session_factory()() as session:
        try:
            token = accounts.request_login(session, email)
        except accounts.RateLimited:
            raise HTTPException(429, "Demasiados intentos. Espera un rato y vuelve a probar.") from None
    if settings().local_login_enabled and email in _admin_emails():
        return {"ok": True, "token": token}
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
        return {"token": session_token, "user": _me(user)}


@app.post("/auth/logout")
def do_logout(token: str = Depends(_bearer)):
    with session_factory()() as session:
        accounts.logout(session, token)
    return {"ok": True}


def _admin_emails() -> set[str]:
    return {e.strip().lower() for e in settings().admin_emails.split(",") if e.strip()}


def _is_admin(user) -> bool:
    return user is not None and user.email in _admin_emails()


def _me(user) -> dict:
    return {**accounts.public_user(user), "admin": _is_admin(user)}


@app.get("/me")
def me(user=Depends(require_user)):
    return _me(user)


@app.delete("/me")
def delete_me(user=Depends(require_user)):
    """Borra la cuenta (RGPD). Con una suscripción activa, primero hay que cancelarla."""
    if accounts.has_subscription(user) and not user.cancel_at_period_end:
        raise HTTPException(409, "Cancela antes la suscripción desde «Gestionar suscripción».")
    with session_factory()() as session:
        accounts.delete_user(session, session.merge(user))
    return {"ok": True}


# --- Suscripción con Stripe ---------------------------------------------------------------

class CheckoutRequest(BaseModel):
    plan: str = Field(pattern="^(monthly|yearly|pro|pass)$")


def _prices(s: Settings) -> dict[str, str]:
    """Plan -> id de precio en Stripe, solo los configurados."""
    prices = {"monthly": s.stripe_price_monthly, "yearly": s.stripe_price_yearly,
              "pro": s.stripe_price_pro, "pass": s.stripe_price_pass}
    return {plan: price for plan, price in prices.items() if price}


@app.get("/billing/plans")
def billing_plans():
    """Qué planes se pueden contratar ahora (los que tienen precio en Stripe)."""
    s = settings()
    return {"plans": sorted(_prices(s)) if s.stripe_secret_key else []}


@app.post("/billing/checkout")
def checkout(req: CheckoutRequest, user=Depends(require_user)):
    s = settings()
    price = _prices(s).get(req.plan)
    if not (s.stripe_secret_key and price):
        raise HTTPException(503, "Este plan todavía no está activado")
    # Con un pase se puede pasar a suscripción (o comprar otro pase); con suscripción, no.
    if accounts.has_subscription(user):
        raise HTTPException(409, "Ya tienes una suscripción activa")
    if user.subscription_status == "paused":
        raise HTTPException(409, "Tu suscripción está en pausa: reanúdala desde Mi cuenta")
    url = billing.create_checkout(user, req.plan, secret_key=s.stripe_secret_key, price_id=price, web_url=s.web_url)
    return {"url": url}


@app.post("/billing/pause")
def pause_subscription(user=Depends(require_user)):
    """Pausa un mes los cobros en vez de cancelar (el botón de cancelar sigue en el portal)."""
    s = settings()
    if not (s.stripe_secret_key and user.stripe_subscription_id):
        raise HTTPException(404, "No hay ninguna suscripción que pausar")
    if user.subscription_status != "active" or user.cancel_at_period_end:
        raise HTTPException(409, "Solo se puede pausar una suscripción activa (no en la prueba gratis)")
    resumes = billing.pause(user, secret_key=s.stripe_secret_key)
    return {"ok": True, "resumes_at": resumes.isoformat()}


@app.post("/billing/resume")
def resume_subscription(user=Depends(require_user)):
    s = settings()
    if not (s.stripe_secret_key and user.stripe_subscription_id) or user.subscription_status != "paused":
        raise HTTPException(409, "Tu suscripción no está en pausa")
    billing.resume(user, secret_key=s.stripe_secret_key)
    return {"ok": True}


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
    plans_by_price = {price: plan for plan, price in _prices(settings()).items() if plan != "pass"}
    with session_factory()() as session:
        billing.apply_event(session, event, plans_by_price)
    return {"received": True}


# --- Zona de partidos ---------------------------------------------------------------------

def _sees_all(user) -> bool:
    """Suscriptores y el autor de los picks (que necesita ver todas las líneas para elegir)."""
    return accounts.is_subscriber(user) or _is_admin(user)


def _viewer(user) -> dict:
    return {"logged_in": user is not None, "subscriber": _sees_all(user)}


@app.get("/board")
def get_board(game_date: date | None = None, user=Depends(current_user)):
    """Partidos de una jornada (por defecto, la próxima con partidos por jugar)."""
    with session_factory()() as session:
        day = game_date.isoformat() if game_date else board.default_date(session)
        lines = board.board_lines(session, game_date=day) if day else []
        games = board.games(lines)
        ml = moneyline.for_events(session, [g["event_id"] for g in games])
        return {
            "game_date": day,
            "dates": board.board_dates(session),
            "free_lines_per_day": settings().free_lines_per_day,
            "viewer": _viewer(user),
            "games": [{**g, "moneyline": moneyline.public(ml.get(g["event_id"]))} for g in games],
            "disclaimer": DISCLAIMER,
        }


@app.get("/board/games/{event_id}")
def get_game(event_id: str, user=Depends(current_user)):
    """Jugadores del partido con sus líneas. Bloqueadas: sin veredicto ni probabilidades."""
    subscriber = _sees_all(user)
    with session_factory()() as session:
        lines = board.board_lines(session, event_id=event_id)
        if not lines:
            raise HTTPException(404, "Partido no encontrado")
        return {
            "game": {**board.game_header(lines[0]),
                     "moneyline": moneyline.public(session.get(moneyline.GameOdds, event_id), full=True)},
            "viewer": _viewer(user),
            "lines": [board.line_summary(p, board.is_unlocked(p, subscriber)) for p in lines],
            "disclaimer": DISCLAIMER,
        }


@app.get("/board/top")
def get_top(game_date: date | None = None, limit: int = 40, user=Depends(current_user)):
    """Mejores proyecciones de la noche: las líneas por jugar más alejadas de la proyección."""
    with session_factory()() as session:
        day = game_date.isoformat() if game_date else board.default_date(session)
        lines = board.board_lines(session, game_date=day) if day else []
        return {
            "game_date": day,
            "viewer": _viewer(user),
            "lines": board.top_lines(lines, _sees_all(user), limit=min(max(limit, 1), 100)),
            "disclaimer": DISCLAIMER,
        }


@app.get("/board/lines/{line_id}")
def get_line(line_id: int, user=Depends(current_user)):
    """Informe completo de una línea. 402 si hace falta suscripción."""
    with session_factory()() as session:
        p = session.get(Prediction, line_id)
        if p is None or not p.event_id:
            raise HTTPException(404, "Línea no encontrada")
        if not board.is_unlocked(p, _sees_all(user)):
            raise HTTPException(402, "Este informe es para suscriptores")
        return {**board.line_detail(p), "disclaimer": DISCLAIMER}


def board_report(a, meta) -> str:
    """Para no disparar el coste, Claude redacta los puntos de cada jugador y las líneas
    gratis; el resto, plantilla."""
    if a.stat == "pts" or meta.get("free"):
        return write_report(a, claude_client(), settings().anthropic_model, books=meta.get("books"))
    return template_report(a)


@app.post("/admin/board", dependencies=[Depends(require_admin)])
def build_board(game_date: date, max_events: int | None = None, an: Analyzer = Depends(analyzer)):
    """Analiza todas las props de la jornada y las publica en la zona de partidos.

    Consume créditos de The Odds API (mercados x regiones por partido)."""
    results = scan_day(an, odds_client(), game_date, max_events=max_events)
    with session_factory()() as session:
        published = board.publish_board(session, results, game_date, settings().free_lines_per_day, board_report)
        try:
            moneyline.refresh(session, odds_client(), game_date, force=True)
        except Exception:  # noqa: BLE001 - las cuotas a ganador son un extra
            session.rollback()
        out = {"published": len(published), "free": sum(1 for p in published if p.free)}
    # Se publica la jornada una vez al día: aprovechamos para mandar los avisos de la prueba.
    out["trial_reminders"] = trial_reminders()["sent"]
    return out


@app.post("/admin/trial-reminders", dependencies=[Depends(require_admin)])
def trial_reminders():
    """Correo del día 5 de la prueba: cuándo se cobra y cómo cancelar. Uno por cuenta."""
    s = settings()
    sent = 0
    with session_factory()() as session:
        for user in accounts.trials_to_remind(session):
            since = accounts._aware(user.trial_started_at)
            lines = [p for p in board.board_lines(session) if accounts._aware(p.published_at) >= since]
            ends = accounts._aware(user.current_period_end)
            ok = send_trial_reminder(
                s, user.email, plan=user.plan,
                ends=ends.strftime("%d/%m/%Y") if ends else "final de la semana",
                lines=len(lines), games=len({p.event_id for p in lines}),
            )
            if ok:
                user.trial_reminder_sent = True
                sent += 1
        session.commit()
    return {"sent": sent}


def start_auto_jornada():
    s = settings()
    if s.local_login and not s.local_login_enabled:
        import logging

        logging.getLogger("propdeep").warning("LOCAL_LOGIN se ignora: WEB_URL no es localhost")
    if s.auto_jornada:
        auto.start(session_factory(), lambda: (analyzer(), odds_client(), bdl_client(), board_report), s)


# --- Ejemplo de mis picks con ayuda de la página ------------------------------------------

PICKS_WARNING = "Resultados pasados no garantizan nada; a largo plazo es muy difícil ganar a la casa."


def require_pick_admin(user=Depends(current_user), x_admin_token: str = Header(default="")):
    token = settings().admin_token
    if _is_admin(user) or (token and x_admin_token == token):
        return
    raise HTTPException(403, "Solo el autor puede publicar picks")


class PickRequest(BaseModel):
    line_id: int | None = None
    player_name: str | None = Field(default=None, max_length=120)
    stat: str | None = Field(default=None, pattern="^(pts|reb|ast|fg3m|ml)$")
    line: float | None = None
    side: str = Field(pattern="^(over|under)$")
    odds: float = Field(gt=1.0, le=50)
    bookmaker: str = Field(max_length=60)
    stake: float = Field(default=1.0, gt=0, le=10)
    note: str | None = Field(default=None, max_length=280)
    commence_time: datetime | None = None
    home_team: str | None = Field(default=None, max_length=60)
    away_team: str | None = Field(default=None, max_length=60)
    # Moneyline (stat "ml"): el partido de las cuotas a ganador y el equipo elegido.
    event_id: str | None = Field(default=None, max_length=64)
    team: str | None = Field(default=None, max_length=60)


class ParlayLeg(BaseModel):
    line_id: int | None = None
    player_name: str | None = Field(default=None, max_length=120)
    stat: str | None = Field(default=None, pattern="^(pts|reb|ast|fg3m|ml)$")
    line: float | None = None
    side: str = Field(pattern="^(over|under)$")
    odds: float = Field(gt=1.0, le=50)
    commence_time: datetime | None = None
    home_team: str | None = Field(default=None, max_length=60)
    away_team: str | None = Field(default=None, max_length=60)
    # Moneyline (stat "ml"): el partido de las cuotas a ganador y el equipo elegido.
    event_id: str | None = Field(default=None, max_length=64)
    team: str | None = Field(default=None, max_length=60)


class ParlayRequest(BaseModel):
    legs: list[ParlayLeg] = Field(min_length=2, max_length=12)
    odds: float | None = Field(default=None, gt=1.0, le=10000)
    bookmaker: str = Field(max_length=60)
    stake: float = Field(default=1.0, gt=0, le=10)
    note: str | None = Field(default=None, max_length=280)


class SettleRequest(BaseModel):
    actual: float | None = None
    void: bool = False


@app.get("/picks")
def list_picks():
    """Todos los picks de Gonza, ganados y perdidos, con su resumen. Público."""
    with session_factory()() as session:
        ps = picks.all_picks(session)
        parlays = picks.all_parlays(session)
        return {
            "summary": picks.summary(ps),
            "picks": [picks.public(p) for p in ps],
            "parlay_summary": picks.summary([p for p, _ in parlays]),
            "parlays": [picks.public_parlay(p, legs) for p, legs in parlays],
            "total": picks.summary([*ps, *(p for p, _ in parlays)]),
            "warning": PICKS_WARNING,
            "disclaimer": DISCLAIMER,
        }


@app.post("/picks", status_code=201, dependencies=[Depends(require_pick_admin)])
def create_pick(req: PickRequest):
    """Publica un pick antes del partido. Después no se puede editar ni borrar."""
    with session_factory()() as session:
        try:
            return picks.public(picks.create(session, req.model_dump()))
        except picks.PickError as exc:
            raise HTTPException(422, str(exc)) from exc


@app.post("/parlays", status_code=201, dependencies=[Depends(require_pick_admin)])
def create_parlay(req: ParlayRequest):
    """Publica una combinada antes de que empiece ninguno de sus partidos. No se edita."""
    with session_factory()() as session:
        try:
            p = picks.create_parlay(session, [leg.model_dump() for leg in req.legs], req.bookmaker,
                                    req.odds, req.stake, req.note)
        except picks.PickError as exc:
            raise HTTPException(422, str(exc)) from exc
        return picks.public_parlay(p, picks.legs_of(session, p.id))


@app.post("/picks/{pick_id}/settle", dependencies=[Depends(require_pick_admin)])
def settle_pick(pick_id: int, req: SettleRequest):
    """Resultado de un pick que no sale de la zona de partidos (los demás se liquidan solos)."""
    with session_factory()() as session:
        try:
            return picks.public(picks.settle_manual(session, pick_id, req.actual, req.void))
        except LookupError as exc:
            raise HTTPException(404, str(exc)) from exc
        except picks.PickError as exc:
            raise HTTPException(409, str(exc)) from exc


# --- Paper bets: bank simulado en euros (solo el autor) ------------------------------------

class PaperBankRequest(BaseModel):
    initial: float = Field(gt=0, le=1_000_000)
    reset: bool = False


class PaperBetRequest(PickRequest):
    stake: float = Field(gt=0, le=100_000)  # euros


class PaperParlayRequest(ParlayRequest):
    stake: float = Field(gt=0, le=100_000)


@app.get("/paper", dependencies=[Depends(require_pick_admin)])
def paper_state():
    with session_factory()() as session:
        return {**paper.state(session), "disclaimer": DISCLAIMER}


@app.post("/paper/bank", dependencies=[Depends(require_pick_admin)])
def paper_bank(req: PaperBankRequest):
    """Cambia el bank inicial; con `reset`, empieza de cero (lo anterior no se borra)."""
    with session_factory()() as session:
        paper.set_bank(session, req.initial, req.reset)
        return paper.state(session)


@app.post("/paper/bets", status_code=201, dependencies=[Depends(require_pick_admin)])
def paper_bet(req: PaperBetRequest):
    with session_factory()() as session:
        try:
            picks.create(session, {**req.model_dump(), "paper": True})
        except picks.PickError as exc:
            raise HTTPException(422, str(exc)) from exc
        return paper.state(session)


@app.post("/paper/parlays", status_code=201, dependencies=[Depends(require_pick_admin)])
def paper_parlay(req: PaperParlayRequest):
    with session_factory()() as session:
        try:
            picks.create_parlay(session, [leg.model_dump() for leg in req.legs], req.bookmaker,
                                req.odds, req.stake, req.note, paper=True)
        except picks.PickError as exc:
            raise HTTPException(422, str(exc)) from exc
        return paper.state(session)


@app.delete("/paper/bets/{kind}/{bet_id}", dependencies=[Depends(require_pick_admin)])
def paper_cancel(kind: str, bet_id: int):
    if kind not in ("single", "parlay"):
        raise HTTPException(404, "Apuesta no encontrada")
    with session_factory()() as session:
        try:
            paper.cancel(session, kind, bet_id)
        except LookupError as exc:
            raise HTTPException(404, str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc
        return paper.state(session)


# --- Auditoría de tipsters ----------------------------------------------------------------

TIPSTERS_NOTE = ("Picks publicados en abierto por cada tipster antes del partido, registrados todos los que "
                 "vimos con el enlace a su publicación. Se cuenta 1 unidad si el tipster no indica otra cosa.")


class TipsterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    url: str = Field(pattern="^https?://", max_length=300)


class TipsterPickRequest(BaseModel):
    posted_at: datetime
    event_start: datetime
    event: str = Field(min_length=1, max_length=160)
    selection: str = Field(min_length=1, max_length=200)
    odds: float = Field(gt=1.0, le=1000)
    stake: float = Field(default=1.0, gt=0, le=100)
    evidence_url: str = Field(max_length=500)


class TipsterSettleRequest(BaseModel):
    result: str = Field(pattern="^(won|lost|push|void)$")


@app.get("/tipsters")
def list_tipsters(user=Depends(current_user)):
    """Público solo con TIPSTERS_PUBLIC=true; antes, solo el autor."""
    admin = _is_admin(user)
    if not (settings().tipsters_public or admin):
        raise HTTPException(404, "No disponible")
    with session_factory()() as session:
        return {"tipsters": tipsters.report(session), "public": settings().tipsters_public,
                "admin": admin, "note": TIPSTERS_NOTE, "disclaimer": DISCLAIMER}


@app.post("/tipsters", status_code=201, dependencies=[Depends(require_pick_admin)])
def create_tipster(req: TipsterRequest):
    with session_factory()() as session:
        try:
            t = tipsters.add_tipster(session, req.name, req.url)
        except tipsters.TipsterError as exc:
            raise HTTPException(409, str(exc)) from exc
        return {"id": t.id, "name": t.name, "url": t.url}


@app.post("/tipsters/{tipster_id}/picks", status_code=201, dependencies=[Depends(require_pick_admin)])
def create_tipster_pick(tipster_id: int, req: TipsterPickRequest):
    with session_factory()() as session:
        try:
            return tipsters.public_pick(tipsters.add_pick(session, tipster_id, req.model_dump()))
        except LookupError as exc:
            raise HTTPException(404, str(exc)) from exc
        except tipsters.TipsterError as exc:
            raise HTTPException(422, str(exc)) from exc


@app.post("/tipster-picks/{pick_id}/settle", dependencies=[Depends(require_pick_admin)])
def settle_tipster_pick(pick_id: int, req: TipsterSettleRequest):
    with session_factory()() as session:
        try:
            return tipsters.public_pick(tipsters.settle(session, pick_id, req.result))
        except LookupError as exc:
            raise HTTPException(404, str(exc)) from exc
        except tipsters.TipsterError as exc:
            raise HTTPException(409, str(exc)) from exc


# --- Chat en español sobre los datos del día ----------------------------------------------

class ChatMessage(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(max_length=4000)


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1, max_length=40)


def _chat_user(user=Depends(require_user)):
    if not _sees_all(user):
        raise HTTPException(402, "El chat es para suscriptores")
    return user


def _chat_limit(user) -> int:
    """Con plan Pro en marcha, el chat completo es del Pro (y del autor); el resto, el básico."""
    s = settings()
    if not s.stripe_price_pro or _is_admin(user) or (user.plan == "pro" and accounts.has_subscription(user)):
        return s.chat_messages_per_day
    return s.chat_messages_per_day_basic


@app.get("/chat")
def chat_status(user=Depends(_chat_user)):
    limit = _chat_limit(user)
    s = settings()
    with session_factory()() as session:
        return {"enabled": claude_client() is not None, "limit": limit,
                "remaining": chat.remaining(session, user.id, limit),
                "pro_limit": s.chat_messages_per_day if s.stripe_price_pro and limit < s.chat_messages_per_day else None}


@app.post("/chat")
def chat_message(req: ChatRequest, user=Depends(_chat_user)):
    """Responde una pregunta sobre la jornada. No se guarda la conversación."""
    import anthropic

    client = claude_client()
    if client is None:
        raise HTTPException(503, "El chat todavía no está activado")
    s = settings()
    limit = _chat_limit(user)
    with session_factory()() as session:
        try:
            left = chat.take_message(session, user.id, limit)
        except chat.LimitReached:
            more = (f" Con el plan Pro tienes {s.chat_messages_per_day} al día."
                    if limit < s.chat_messages_per_day else "")
            raise HTTPException(429, f"Has llegado a los {limit} mensajes de hoy. Mañana más.{more}") from None
        try:
            reply = chat.answer(session, [m.model_dump() for m in req.messages], client,
                                s.chat_model or s.anthropic_model, s.chat_effort)
        except ValueError as exc:
            chat.give_back(session, user.id)
            raise HTTPException(422, str(exc)) from exc
        except anthropic.APIError as exc:
            chat.give_back(session, user.id)
            raise HTTPException(502, "El chat no responde ahora. Vuelve a intentarlo en un rato.") from exc
    return {"reply": reply, "remaining": left, "disclaimer": DISCLAIMER}
