"""Cliente mínimo de la API de Balldontlie (NBA).

Necesita el plan ALL-STAR para /stats y /player_injuries. Paginación por cursor.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import httpx

BASE_URL = "https://api.balldontlie.io/v1"


class BalldontlieClient:
    def __init__(self, api_key: str, http: httpx.Client | None = None):
        self._http = http or httpx.Client(
            base_url=BASE_URL, headers={"Authorization": api_key}, timeout=20.0
        )

    def _get_all(self, path: str, params: dict[str, Any], limit: int = 500) -> list[dict]:
        items: list[dict] = []
        params = {**params, "per_page": 100}
        while True:
            resp = self._http.get(path, params=params)
            resp.raise_for_status()
            body = resp.json()
            items.extend(body.get("data", []))
            cursor = body.get("meta", {}).get("next_cursor")
            if not cursor or len(items) >= limit:
                return items
            params["cursor"] = cursor

    def find_player(self, name: str) -> dict | None:
        """Busca un jugador por nombre completo; devuelve el mejor candidato."""
        parts = name.strip().split()
        params = {"search": parts[-1]} if parts else {"search": name}
        candidates = self._get_all("/players", params, limit=100)
        wanted = _normalize(name)
        for player in candidates:
            if _normalize(f"{player['first_name']} {player['last_name']}") == wanted:
                return player
        return candidates[0] if len(candidates) == 1 else None

    def player_stats(self, player_id: int, seasons: list[int]) -> list[dict]:
        """Estadísticas por partido de un jugador, más recientes primero."""
        rows = self._get_all(
            "/stats", {"player_ids[]": player_id, "seasons[]": seasons}, limit=300
        )
        played = [r for r in rows if _minutes(r.get("min")) > 0]
        return sorted(played, key=lambda r: r["game"]["date"], reverse=True)

    def game(self, game_id: int) -> dict:
        resp = self._http.get(f"/games/{game_id}")
        resp.raise_for_status()
        return resp.json()["data"]

    def game_stats(self, game_id: int) -> list[dict]:
        return self._get_all("/stats", {"game_ids[]": game_id}, limit=100)

    def games_on(self, day: date) -> list[dict]:
        return self._get_all("/games", {"dates[]": day.isoformat()}, limit=100)

    def team_games(self, team_id: int, season: int) -> list[dict]:
        return self._get_all("/games", {"team_ids[]": team_id, "seasons[]": season}, limit=120)

    def played_yesterday(self, team_id: int, day: date) -> bool:
        games = self._get_all(
            "/games",
            {"team_ids[]": team_id, "dates[]": (day - timedelta(days=1)).isoformat()},
            limit=5,
        )
        return bool(games)

    def injury(self, player_id: int) -> dict | None:
        rows = self._get_all("/player_injuries", {"player_ids[]": player_id}, limit=5)
        return rows[0] if rows else None


def _normalize(text: str) -> str:
    import unicodedata

    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return " ".join(ascii_text.lower().replace(".", "").split())


def _minutes(value: Any) -> float:
    """Balldontlie devuelve los minutos como "34" o "34:12"."""
    if value in (None, "", "0", "00", "0:00"):
        return 0.0
    text = str(value)
    if ":" in text:
        mins, secs = text.split(":", 1)
        return float(mins or 0) + float(secs or 0) / 60
    return float(text)


minutes = _minutes
normalize_name = _normalize
