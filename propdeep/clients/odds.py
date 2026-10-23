"""Cliente de The Odds API para player props de la NBA (cuotas decimales)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone

import httpx

BASE_URL = "https://api.the-odds-api.com/v4"
SPORT = "basketball_nba"

# Mercado de The Odds API -> estadística de Balldontlie
MARKETS = {
    "player_points": "pts",
    "player_rebounds": "reb",
    "player_assists": "ast",
    "player_threes": "fg3m",
}


@dataclass
class PropLine:
    event_id: str
    commence_time: str
    home_team: str
    away_team: str
    player: str
    market: str
    line: float
    over_odds: float
    under_odds: float
    bookmaker: str


class OddsClient:
    def __init__(self, api_key: str, regions: str = "eu", http: httpx.Client | None = None):
        self._key = api_key
        self._regions = regions
        self._http = http or httpx.Client(base_url=BASE_URL, timeout=20.0)

    def events_on(self, day: date) -> list[dict]:
        # Partidos de la jornada americana: de 12:00 UTC del día a 12:00 UTC del siguiente.
        start = datetime.combine(day, time(12), tzinfo=timezone.utc)
        resp = self._http.get(
            f"/sports/{SPORT}/events",
            params={
                "apiKey": self._key,
                "commenceTimeFrom": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "commenceTimeTo": (start + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            },
        )
        resp.raise_for_status()
        return resp.json()

    def player_props(self, event: dict, markets: list[str] | None = None) -> list[PropLine]:
        """Líneas de props de un partido. Cuesta (mercados x regiones) créditos."""
        markets = markets or list(MARKETS)
        resp = self._http.get(
            f"/sports/{SPORT}/events/{event['id']}/odds",
            params={
                "apiKey": self._key,
                "regions": self._regions,
                "markets": ",".join(markets),
                "oddsFormat": "decimal",
            },
        )
        resp.raise_for_status()
        return parse_all_props(resp.json())


    def moneylines(self, day: date) -> list[dict]:
        """Cuotas a ganador de todos los partidos de la jornada en una sola llamada.
        Cuesta 1 crédito por región (no por partido)."""
        start = datetime.combine(day, time(12), tzinfo=timezone.utc)
        resp = self._http.get(
            f"/sports/{SPORT}/odds",
            params={
                "apiKey": self._key,
                "regions": self._regions,
                "markets": "h2h",
                "oddsFormat": "decimal",
                "commenceTimeFrom": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "commenceTimeTo": (start + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            },
        )
        resp.raise_for_status()
        return [parse_moneyline(ev) for ev in resp.json()]


def parse_moneyline(payload: dict) -> dict:
    """Un partido con la cuota de cada casa para el local y el visitante."""
    home, away = payload.get("home_team", ""), payload.get("away_team", "")
    books = []
    for book in payload.get("bookmakers", []):
        for market in book.get("markets", []):
            if market.get("key") != "h2h":
                continue
            prices = {o.get("name"): float(o["price"]) for o in market.get("outcomes", []) if o.get("price")}
            if home in prices and away in prices:
                books.append({"bookmaker": book["key"], "home_odds": prices[home], "away_odds": prices[away]})
    return {
        "event_id": payload.get("id", ""),
        "commence_time": payload.get("commence_time", ""),
        "home_team": home,
        "away_team": away,
        "books": sorted(books, key=lambda b: b["bookmaker"]),
    }


def parse_props(payload: dict) -> list[PropLine]:
    """Una línea por (mercado, jugador, línea): la de la casa con menos margen."""
    best: dict[tuple, PropLine] = {}
    for prop in parse_all_props(payload):
        key = (prop.market, prop.player, prop.line)
        current = best.get(key)
        # Menor margen = mercado más eficiente; es la referencia más honesta.
        if current is None or _overround(prop) < _overround(current):
            best[key] = prop
    return list(best.values())


def main_lines(props: list[PropLine]) -> list[tuple[PropLine, list[PropLine]]]:
    """Por jugador y mercado: la línea principal y todas las de cada casa (para compararlas).

    La principal es la que más casas ofrecen (a igualdad, la más cercana al 50/50) y, dentro
    de ella, la cuota de la casa con menos margen."""
    groups: dict[tuple, list[PropLine]] = {}
    for prop in props:
        groups.setdefault((prop.event_id, prop.player, prop.market), []).append(prop)
    out = []
    for rows in groups.values():
        count: dict[float, int] = {}
        for r in rows:
            count[r.line] = count.get(r.line, 0) + 1
        line = min(count, key=lambda x: (-count[x], min(abs(1 / r.over_odds - 1 / r.under_odds) for r in rows if r.line == x)))
        main = min((r for r in rows if r.line == line), key=_overround)
        out.append((main, sorted(rows, key=lambda r: (r.line, r.bookmaker))))
    return out


def book_rows(rows: list[PropLine]) -> list[dict]:
    """Líneas de cada casa en el formato que guarda el análisis."""
    return [{"bookmaker": r.bookmaker, "line": r.line, "over_odds": r.over_odds, "under_odds": r.under_odds} for r in rows]


def parse_all_props(payload: dict) -> list[PropLine]:
    """Todas las líneas: una por (casa, mercado, jugador, línea) con su más y su menos.

    Lo que venga incompleto o raro (sin casa, sin jugador, cuota no numérica) se salta: una
    cuota rota no debe tumbar un partido ya pagado."""
    pairs: dict[tuple, dict] = {}
    for book in payload.get("bookmakers") or []:
        for market in book.get("markets") or []:
            if market.get("key") not in MARKETS or not book.get("key"):
                continue
            for outcome in market.get("outcomes") or []:
                side = str(outcome.get("name", "")).lower()
                player = outcome.get("description")
                if side not in ("over", "under") or not player:
                    continue
                try:
                    point, price = float(outcome["point"]), float(outcome["price"])
                except (KeyError, TypeError, ValueError):
                    continue
                if price <= 1.0:
                    continue
                pairs.setdefault((book["key"], market["key"], player, point), {})[side] = price

    out: list[PropLine] = []
    for (bookmaker, market, player, line), prices in pairs.items():
        if "over" not in prices or "under" not in prices:
            continue
        out.append(PropLine(
            event_id=payload.get("id", ""),
            commence_time=payload.get("commence_time", ""),
            home_team=payload.get("home_team", ""),
            away_team=payload.get("away_team", ""),
            player=player,
            market=market,
            line=line,
            over_odds=prices["over"],
            under_odds=prices["under"],
            bookmaker=bookmaker,
        ))
    return out


def _overround(prop: PropLine) -> float:
    return 1 / prop.over_odds + 1 / prop.under_odds
