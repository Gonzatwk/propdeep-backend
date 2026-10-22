"""Planes (Pro y pase), pausa, aviso del día 5, muro con curiosidad y auditoría de tipsters."""
from datetime import datetime, timedelta, timezone

import main
from propdeep import accounts, billing
from propdeep.accounts import User
from tests.test_board import ADMIN, DAY, _login, _subscribe, _webhook


def _user():
    with main.session_factory()() as s:
        return s.query(User).one()


def _set(monkeypatch, api, **kw):
    s = main.settings()
    new = type(s)(**{**s.__dict__, **kw})
    monkeypatch.setattr(main, "settings", lambda: new)
    return new


def test_locked_lines_say_how_many_games_but_not_the_number(api):
    api.c.post(f"/admin/board?game_date={DAY}", headers=ADMIN)
    lines = api.c.get("/board/games/ev1").json()["lines"]
    locked = [l for l in lines if l["locked"]]
    assert locked and all(l["teaser_games"] == 10 and "hit_rates" not in l for l in locked)
    assert all("teaser_games" not in l for l in lines if not l["locked"])


def test_pass_gives_seven_days_and_stacks(api):
    h = _login(api)
    uid = _user().id
    event = {"type": "checkout.session.completed", "data": {"object": {
        "mode": "payment", "payment_status": "paid", "customer": "cus_9",
        "metadata": {"user_id": str(uid), "plan": "pass"}}}}
    _webhook(api, event)
    me = api.c.get("/me", headers=h).json()
    assert me["subscriber"] and me["pass_until"] and me["status"] is None
    first = datetime.fromisoformat(me["pass_until"])
    _webhook(api, event)
    second = datetime.fromisoformat(api.c.get("/me", headers=h).json()["pass_until"])
    assert timedelta(days=6, hours=23) < second - first <= timedelta(days=7)
    # Un pago sin cobrar todavía no da nada.
    unpaid = {"type": "checkout.session.completed", "data": {"object": {**event["data"]["object"], "payment_status": "unpaid"}}}
    with main.session_factory()() as s:
        assert billing.apply_event(s, unpaid) is False


def test_expired_pass_is_not_access():
    u = User(email="x@x.es", pass_until=datetime.now(timezone.utc) - timedelta(minutes=1))
    assert not accounts.is_subscriber(u)


def test_plan_comes_from_the_price_and_pause_removes_access(api, monkeypatch):
    _set(monkeypatch, api, stripe_price_pro="price_pro", stripe_price_monthly="price_m", stripe_secret_key="sk_test")
    h = _login(api)
    uid = _user().id
    end = int((datetime.now(timezone.utc) + timedelta(days=30)).timestamp())
    sub = {"id": "sub_1", "customer": "cus_1", "status": "active", "metadata": {"user_id": str(uid), "plan": "monthly"},
           "items": {"data": [{"price": {"id": "price_pro"}, "current_period_end": end}]}}
    _webhook(api, {"type": "customer.subscription.updated", "data": {"object": sub}})
    me = api.c.get("/me", headers=h).json()
    assert me["plan"] == "pro" and me["subscriber"]

    _webhook(api, {"type": "customer.subscription.updated", "data": {"object": {**sub, "pause_collection": {"behavior": "void"}}}})
    me = api.c.get("/me", headers=h).json()
    assert me["status"] == "paused" and not me["subscriber"]
    # En pausa no se puede abrir otra suscripción por encima.
    assert api.c.post("/billing/checkout", json={"plan": "monthly"}, headers=h).status_code == 409


def test_pause_calls_stripe_only_for_active_paid_subscriptions(api, monkeypatch):
    _set(monkeypatch, api, stripe_secret_key="sk_test")
    calls = []
    monkeypatch.setattr(billing, "pause", lambda user, **kw: calls.append(user.stripe_subscription_id) or datetime.now(timezone.utc))
    h = _login(api)
    _subscribe(api, h)  # en prueba
    with main.session_factory()() as s:
        u = s.query(User).one()
        u.stripe_subscription_id = "sub_1"
        s.commit()
    assert api.c.post("/billing/pause", headers=h).status_code == 409
    _subscribe(api, h, status="active")
    assert api.c.post("/billing/pause", headers=h).status_code == 200
    assert calls == ["sub_1"]


def test_chat_limit_depends_on_the_plan_only_when_pro_exists(api, monkeypatch):
    h = _login(api)
    _subscribe(api, h, status="active")
    with main.session_factory()() as s:
        u = s.query(User).one()
        assert main._chat_limit(u) == 30  # sin plan Pro, todos igual
    _set(monkeypatch, api, stripe_price_pro="price_pro")
    with main.session_factory()() as s:
        u = s.query(User).one()
        assert main._chat_limit(u) == 5
        u.plan = "pro"
        assert main._chat_limit(u) == 30


def test_checkout_only_offers_configured_plans(api, monkeypatch):
    assert api.c.get("/billing/plans").json() == {"plans": []}
    _set(monkeypatch, api, stripe_secret_key="sk_test", stripe_price_monthly="price_m", stripe_price_pass="price_p")
    assert api.c.get("/billing/plans").json() == {"plans": ["monthly", "pass"]}
    h = _login(api)
    assert api.c.post("/billing/checkout", json={"plan": "pro"}, headers=h).status_code == 503


def test_trial_reminder_goes_once_on_day_five(api, monkeypatch):
    sent = []
    monkeypatch.setattr(main, "send_trial_reminder", lambda s, to, **kw: sent.append((to, kw)) or True)
    h = _login(api)
    _subscribe(api, h)
    assert api.c.post("/admin/trial-reminders", headers=ADMIN).json() == {"sent": 0}  # día 1
    with main.session_factory()() as s:
        u = s.query(User).one()
        u.trial_started_at = datetime.now(timezone.utc) - timedelta(days=4, hours=1)
        s.commit()
    assert api.c.post("/admin/trial-reminders", headers=ADMIN).json() == {"sent": 1}
    assert api.c.post("/admin/trial-reminders", headers=ADMIN).json() == {"sent": 0}
    assert sent[0][0] == "ana@example.com"


def test_tipster_audit_is_private_until_published(api, monkeypatch):
    assert api.c.get("/tipsters").status_code == 404
    t = api.c.post("/tipsters", json={"name": "TipsterX", "url": "https://t.me/tipsterx"}, headers=ADMIN).json()
    now = datetime.now(timezone.utc)
    pick = {"posted_at": (now - timedelta(hours=5)).isoformat(), "event_start": (now - timedelta(hours=2)).isoformat(),
            "event": "Lakers - Celtics", "selection": "LeBron más de 24,5 puntos", "odds": 1.9,
            "evidence_url": "https://t.me/tipsterx/123"}
    p = api.c.post(f"/tipsters/{t['id']}/picks", json=pick, headers=ADMIN)
    assert p.status_code == 201
    late = {**pick, "posted_at": (now - timedelta(hours=1)).isoformat()}
    assert api.c.post(f"/tipsters/{t['id']}/picks", json=late, headers=ADMIN).status_code == 422
    no_proof = {**pick, "evidence_url": "captura.png"}
    assert api.c.post(f"/tipsters/{t['id']}/picks", json=no_proof, headers=ADMIN).status_code == 422
    pid = p.json()["id"]
    assert api.c.post(f"/tipster-picks/{pid}/settle", json={"result": "lost"}, headers=ADMIN).status_code == 200
    assert api.c.post(f"/tipster-picks/{pid}/settle", json={"result": "won"}, headers=ADMIN).status_code == 409
    assert api.c.post("/tipsters", json={"name": "Otro", "url": "https://x.com/o"}).status_code == 403

    _set(monkeypatch, api, tipsters_public=True)
    data = api.c.get("/tipsters").json()
    assert data["tipsters"][0]["summary"]["lost"] == 1 and data["tipsters"][0]["summary"]["roi"] == -1.0
