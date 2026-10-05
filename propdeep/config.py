"""Configuración leída de variables de entorno (ver .env.example)."""
import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


def _float(name: str, default: float) -> float:
    value = os.getenv(name)
    return float(value) if value else default


@dataclass(frozen=True)
class Settings:
    balldontlie_api_key: str = field(default_factory=lambda: os.getenv("BALLDONTLIE_API_KEY", ""))
    odds_api_key: str = field(default_factory=lambda: os.getenv("ODDS_API_KEY", ""))
    # Regiones de casas en The Odds API: "eu" cubre las europeas.
    odds_regions: str = field(default_factory=lambda: os.getenv("ODDS_REGIONS", "eu"))
    anthropic_model: str = field(default_factory=lambda: os.getenv("ANTHROPIC_MODEL", "claude-opus-5-5"))
    database_url: str = field(default_factory=lambda: os.getenv("DATABASE_URL", "sqlite:///./propdeep.db"))
    # Protege los endpoints que publican o liquidan predicciones.
    admin_token: str = field(default_factory=lambda: os.getenv("ADMIN_TOKEN", ""))
    # Correos (separados por comas) que pueden publicar picks desde la web tras entrar.
    admin_emails: str = field(default_factory=lambda: os.getenv("ADMIN_EMAILS", ""))
    # Temporada en formato Balldontlie: 2026 = temporada 2026-27.
    current_season: int = field(default_factory=lambda: int(os.getenv("NBA_SEASON", "2026")))
    # Ventaja mínima (en puntos de probabilidad) para considerar una jugada.
    min_edge: float = field(default_factory=lambda: _float("MIN_EDGE", 0.03))
    # Peso del modelo estadístico frente a la probabilidad del mercado (sin margen).
    model_weight: float = field(default_factory=lambda: _float("MODEL_WEIGHT", 0.5))
    cors_origins: str = field(default_factory=lambda: os.getenv("CORS_ORIGINS", "*"))
    # Dirección pública de la web: para el enlace de acceso y las vueltas de Stripe.
    web_url: str = field(default_factory=lambda: os.getenv("WEB_URL", "https://propdeep.pages.dev").rstrip("/"))
    # Líneas por jornada que se ven gratis con su análisis; el resto, con suscripción.
    free_lines_per_day: int = field(default_factory=lambda: int(os.getenv("FREE_LINES_PER_DAY", "3")))
    # Chat para suscriptores: mensajes por usuario y día, y esfuerzo de Claude (low/medium/high).
    chat_messages_per_day: int = field(default_factory=lambda: int(os.getenv("CHAT_MESSAGES_PER_DAY", "30")))
    chat_effort: str = field(default_factory=lambda: os.getenv("CHAT_EFFORT", "medium"))
    # Modelo del chat; vacío = el mismo que los informes (ANTHROPIC_MODEL).
    chat_model: str = field(default_factory=lambda: os.getenv("CHAT_MODEL", ""))
    stripe_secret_key: str = field(default_factory=lambda: os.getenv("STRIPE_SECRET_KEY", ""))
    stripe_webhook_secret: str = field(default_factory=lambda: os.getenv("STRIPE_WEBHOOK_SECRET", ""))
    stripe_price_monthly: str = field(default_factory=lambda: os.getenv("STRIPE_PRICE_MONTHLY", ""))
    stripe_price_yearly: str = field(default_factory=lambda: os.getenv("STRIPE_PRICE_YEARLY", ""))
    # Plan Pro (25 €/mes, con el chat completo). Sin él no hay plan Pro y el chat es igual para todos.
    stripe_price_pro: str = field(default_factory=lambda: os.getenv("STRIPE_PRICE_PRO", ""))
    # Pase de 7 días (5 €, pago único sin renovación).
    stripe_price_pass: str = field(default_factory=lambda: os.getenv("STRIPE_PRICE_PASS", ""))
    # Mensajes de chat al día en los planes que no son Pro (solo cuenta si existe el plan Pro).
    chat_messages_per_day_basic: int = field(default_factory=lambda: int(os.getenv("CHAT_MESSAGES_PER_DAY_BASIC", "5")))
    # Auditoría de tipsters: se ve en la web solo cuando esto vale "true".
    tipsters_public: bool = field(default_factory=lambda: os.getenv("TIPSTERS_PUBLIC", "").lower() == "true")
    smtp_host: str = field(default_factory=lambda: os.getenv("SMTP_HOST", ""))
    smtp_port: int = field(default_factory=lambda: int(os.getenv("SMTP_PORT", "587")))
    smtp_user: str = field(default_factory=lambda: os.getenv("SMTP_USER", ""))
    smtp_password: str = field(default_factory=lambda: os.getenv("SMTP_PASSWORD", ""))
    mail_from: str = field(default_factory=lambda: os.getenv("MAIL_FROM", ""))


def get_settings() -> Settings:
    return Settings()
