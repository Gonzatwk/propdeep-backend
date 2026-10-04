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
    # Temporada en formato Balldontlie: 2026 = temporada 2026-27.
    current_season: int = field(default_factory=lambda: int(os.getenv("NBA_SEASON", "2026")))
    # Ventaja mínima (en puntos de probabilidad) para considerar una jugada.
    min_edge: float = field(default_factory=lambda: _float("MIN_EDGE", 0.03))
    # Peso del modelo estadístico frente a la probabilidad del mercado (sin margen).
    model_weight: float = field(default_factory=lambda: _float("MODEL_WEIGHT", 0.5))
    cors_origins: str = field(default_factory=lambda: os.getenv("CORS_ORIGINS", "*"))


def get_settings() -> Settings:
    return Settings()
