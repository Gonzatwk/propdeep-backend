"""Genera los 3 informes de ejemplo de la landing con datos reales.

Uso (con las claves en .env):
    python -m scripts.informes_ejemplo 2026-10-21 --max-events 3

Elige uno con ventaja, uno sin ventaja y uno de confianza baja, y los escribe en
web/src/data/informes_ejemplo.json, que es lo que lee la landing. Consume créditos de The Odds API
(mercados x regiones por partido).
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import date

from propdeep.clients.balldontlie import BalldontlieClient
from propdeep.clients.odds import OddsClient
from propdeep.config import get_settings
from propdeep.narrative import write_report
from propdeep.pipeline import Analyzer, scan_day


def pick_examples(results):
    with_edge = [r for r in results if r[0].side and r[0].confidence in ("alta", "media")]
    no_edge = [r for r in results if r[0].side is None and not r[0].reasons]
    low = [r for r in results if r[0].confidence == "baja"]
    chosen = []
    for group in (with_edge, no_edge, low):
        if group:
            chosen.append(group[0])
    return chosen


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("game_date", type=date.fromisoformat)
    parser.add_argument("--max-events", type=int, default=3)
    parser.add_argument("--out", default="web/src/data/informes_ejemplo.json")
    parser.add_argument("--regions", help="Regiones de casas en The Odds API (eu, us, uk, au). Por defecto ODDS_REGIONS.")
    args = parser.parse_args()

    s = get_settings()
    analyzer = Analyzer(BalldontlieClient(s.balldontlie_api_key), s.current_season, s.min_edge, s.model_weight)
    odds = OddsClient(s.odds_api_key, args.regions or s.odds_regions)
    results = scan_day(analyzer, odds, args.game_date, args.max_events, log=print)
    if not results:
        print("Sin props que analizar. En pretemporada las casas casi no ofrecen props de jugadores;"
              " prueba con --regions us o con una fecha de temporada regular.")
        return

    claude = None
    if os.getenv("ANTHROPIC_API_KEY"):
        import anthropic

        claude = anthropic.Anthropic()

    examples = []
    for analysis, meta, prop in pick_examples(results):
        examples.append({
            "partido": f"{prop.away_team} @ {prop.home_team}",
            "casa": prop.bookmaker,
            "informe": write_report(analysis, claude, s.anthropic_model),
            "analisis": analysis.to_dict(),
        })
        print(f"- {analysis.player} {analysis.stat} {analysis.line}: {analysis.confidence}")
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(examples, fh, ensure_ascii=False, indent=2)
    print(f"{len(results)} props analizadas, {len(examples)} ejemplos en {args.out}")


if __name__ == "__main__":
    main()
