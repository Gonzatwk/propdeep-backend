"""Lista de la jornada para uso personal: todas las props analizadas y las que tienen ventaja.

Uso (con las claves en .env):
    python -m scripts.picks_hoy 2026-10-21
    python -m scripts.picks_hoy 2026-10-21 --regions us,eu --casas bet365,williamhill

Para cada jugador y mercado coge la línea principal, busca la mejor cuota de más y de menos entre
las casas que ofrecen esa misma línea y calcula la ventaja con esa cuota. Es "jugada" si la ventaja
llega a MIN_EDGE y el jugador no está fuera, en duda o con pocos partidos. Sin jugadas, no se apuesta.

El peso del modelo sale de MODEL_WEIGHT (o --peso). En el backtest de la 2025-26 con cuotas reales,
0,5 perdía (-2,8 %) y 0,2 quedaba en torno a +2 % sin ser significativo: es una pista, no una ventaja
demostrada. Consume créditos de The Odds API (mercados x regiones por partido).
"""
from __future__ import annotations

import argparse
import csv
from datetime import date

from propdeep.clients.balldontlie import BalldontlieClient
from propdeep.clients.odds import OddsClient
from propdeep.config import get_settings
from propdeep.pipeline import Analyzer, scan_day

NOMBRES = {"pts": "puntos", "reb": "rebotes", "ast": "asistencias", "fg3m": "triples"}


def best_at_line(books: list[dict], line: float, casas: set[str] | None) -> tuple[tuple, tuple]:
    """(cuota, casa) más alta de más y de menos entre las casas que dan esa misma línea."""
    rows = [b for b in books if b["line"] == line and (not casas or b["bookmaker"] in casas)]
    if not rows:
        return (None, None), (None, None)
    over = max(rows, key=lambda b: b["over_odds"])
    under = max(rows, key=lambda b: b["under_odds"])
    return (over["over_odds"], over["bookmaker"]), (under["under_odds"], under["bookmaker"])


def evaluate(analysis, meta, prop, min_edge: float, casas: set[str] | None) -> dict | None:
    (o_odds, o_book), (u_odds, u_book) = best_at_line(meta.get("books") or [], prop.line, casas)
    if o_odds is None:
        return None
    p = analysis.prob_over_final
    edge_o, edge_u = p - 1 / o_odds, (1 - p) - 1 / u_odds
    if edge_o >= edge_u:
        side, edge, odds, book, p_side = "más", edge_o, o_odds, o_book, p
    else:
        side, edge, odds, book, p_side = "menos", edge_u, u_odds, u_book, 1 - p
    jugada = edge >= min_edge and not analysis.reasons
    return {
        "jugada": "SÍ" if jugada else "",
        "partido": f"{prop.away_team} @ {prop.home_team}",
        "hora_utc": prop.commence_time[11:16],
        "jugador": analysis.player,
        "mercado": NOMBRES.get(analysis.stat, analysis.stat),
        "linea": prop.line,
        "proyeccion": round(analysis.projection, 1),
        "p_modelo": round(analysis.prob_over_model, 3),
        "p_mercado": round(analysis.prob_over_market, 3),
        "p_final": round(p, 3),
        "lado": side,
        "cuota": odds,
        "casa": book,
        "ventaja_pp": round(edge * 100, 1),
        "ev_pct": round((p_side * odds - 1) * 100, 1),
        "aviso": "; ".join(analysis.reasons),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("game_date", type=date.fromisoformat, help="Jornada americana, AAAA-MM-DD")
    parser.add_argument("--regions", help="Regiones de casas (us, eu, uk). Por defecto ODDS_REGIONS.")
    parser.add_argument("--casas", help="Solo estas casas (claves de The Odds API separadas por comas)")
    parser.add_argument("--peso", type=float, help="Peso del modelo frente al mercado. Por defecto MODEL_WEIGHT.")
    parser.add_argument("--max-events", type=int, help="Analizar solo los N primeros partidos")
    parser.add_argument("--out", help="CSV de salida. Por defecto picks_AAAA-MM-DD.csv")
    args = parser.parse_args()

    s = get_settings()
    peso = s.model_weight if args.peso is None else args.peso
    casas = {c.strip() for c in args.casas.split(",")} if args.casas else None
    # min_edge=1: el analizador no marca jugadas; la ventaja se mide aquí con la mejor cuota.
    analyzer = Analyzer(BalldontlieClient(s.balldontlie_api_key), s.current_season, 1.0, peso)
    odds = OddsClient(s.odds_api_key, args.regions or s.odds_regions)
    results = scan_day(analyzer, odds, args.game_date, args.max_events, log=print)

    rows = [r for r in (evaluate(a, m, p, s.min_edge, casas) for a, m, p in results) if r]
    rows.sort(key=lambda r: (r["jugada"] != "SÍ", -r["ventaja_pp"]))
    out = args.out or f"picks_{args.game_date.isoformat()}.csv"
    if rows:
        with open(out, "w", newline="", encoding="utf-8-sig") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(rows[0]), delimiter=";")
            writer.writeheader()
            writer.writerows(rows)

    jugadas = [r for r in rows if r["jugada"]]
    print(f"\nPeso del modelo {peso:.0%}, ventaja mínima {s.min_edge:.0%}. "
          f"{len(rows)} props analizadas, {len(jugadas)} con ventaja.")
    if not jugadas:
        print("Sin ventaja hoy: no se apuesta.")
    for r in jugadas:
        print(f"- {r['jugador']} {r['mercado']} {r['lado']} {r['linea']} @ {r['cuota']} ({r['casa']}) "
              f"| proyección {r['proyeccion']} | ventaja {r['ventaja_pp']} pp, EV {r['ev_pct']} % | {r['partido']}")
    if rows:
        print(f"Todo en {out} (se abre con Excel).")


if __name__ == "__main__":
    main()
