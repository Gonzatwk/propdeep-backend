"""Revisión de una jornada ya jugada: proyección frente a resultado y de dónde viene el error.

Uso (en el PC donde está la base de datos de la jornada, con las claves en .env):
    python -m scripts.revision_jornada 2026-10-21

Lee todas las líneas publicadas ese día (también las "sin ventaja"), descarga el box score de cada
partido de Balldontlie (una petición por partido) y escribe revision_AAAA-MM-DD.csv con proyección,
línea, resultado, minutos jugados frente a los esperados y marcador final. En pantalla saca el resumen:
error de la proyección frente al de la línea de la casa, calibración de las probabilidades y cuánto
del error se explica por minutos (cambios de rol, blowouts, lesiones en el partido).
"""
from __future__ import annotations

import argparse
import csv
from datetime import date
from statistics import mean

from sqlalchemy import select

from propdeep.clients.balldontlie import BalldontlieClient, minutes
from propdeep.config import get_settings
from propdeep.db import Prediction, make_session_factory


def expected_minutes(trends: dict) -> float | None:
    """Minutos que el modelo daba por hechos: los recientes si hay partidos de esta temporada."""
    if (trends.get("season_games") or 0) >= 3 and trends.get("minutes_last5"):
        return trends["minutes_last5"]
    return trends.get("minutes_season") or trends.get("minutes_last5")


def row_for(p: Prediction, box: dict | None) -> dict:
    a = p.analysis or {}
    t, c = a.get("trends") or {}, a.get("context") or {}
    proj = a.get("projection")
    out = {
        "id": p.id, "partido": f"{p.away_team} @ {p.home_team}", "jugador": p.player_name, "stat": p.stat,
        "linea": p.line, "proyeccion": proj,
        "p_modelo": a.get("prob_over_model"), "p_mercado": a.get("prob_over_market"), "p_final": a.get("prob_over_final"),
        "lado": p.side or "", "cuota": p.odds, "casa": p.bookmaker, "ventaja": p.edge, "confianza": p.confidence,
        "estado": p.status,
        "partidos_temporada": t.get("season_games"), "partidos_temp_anterior": t.get("last_season_games"),
        "media_l5": t.get("last5"), "media_l10": t.get("last10"), "media_temporada": t.get("season"), "sd": t.get("sd"),
        "min_esperados": expected_minutes(t), "min_l5": t.get("minutes_last5"), "min_temporada": t.get("minutes_season"),
        "local": c.get("home"), "b2b": c.get("back_to_back"), "rival": c.get("opponent"),
        "factor_rival": c.get("opponent_factor"), "lesion": c.get("injury_status") or "",
        "real": None, "min_reales": None, "equipo_jugador": None, "margen_final": None,
    }
    if box is not None:
        g, team = box.get("game") or {}, (box.get("team") or {}).get("id")
        out["real"] = float(box.get(p.stat) or 0)
        out["min_reales"] = round(minutes(box.get("min")), 1)
        out["equipo_jugador"] = (box.get("team") or {}).get("abbreviation")
        hs, vs = g.get("home_team_score"), g.get("visitor_team_score")
        if hs is not None and vs is not None and team is not None:
            out["margen_final"] = (hs - vs) if team == g.get("home_team_id") else (vs - hs)
    return out


def summarize(rows: list[dict]) -> None:
    played = [r for r in rows if r["real"] is not None and (r["min_reales"] or 0) > 0 and r["proyeccion"] is not None]
    dnp = [r for r in rows if r["real"] is None or not r["min_reales"]]
    print(f"\n{len(rows)} líneas, {len(played)} con el jugador en pista, {len(dnp)} sin jugar o sin box score.")
    if not played:
        return
    for stat in sorted({r["stat"] for r in played}) + ["todas"]:
        g = [r for r in played if stat == "todas" or r["stat"] == stat]
        e_proj = [r["real"] - r["proyeccion"] for r in g]
        e_line = [r["real"] - r["linea"] for r in g]
        over = [r["real"] > r["linea"] for r in g if r["real"] != r["linea"]]
        print(f"\n[{stat}] n={len(g)} | error medio de la proyección {mean(abs(x) for x in e_proj):.2f} "
              f"(sesgo {mean(e_proj):+.2f}) | de la línea {mean(abs(x) for x in e_line):.2f} (sesgo {mean(e_line):+.2f}) "
              f"| over {mean(over):.0%}")
        for key in ("p_modelo", "p_mercado", "p_final"):
            pts = [(r[key], r["real"] > r["linea"]) for r in g if r[key] is not None and r["real"] != r["linea"]]
            if pts:
                print(f"   Brier {key}: {mean((p - y) ** 2 for p, y in pts):.4f}")

    # Minutos: cuánto del fallo viene de jugar más o menos de lo esperado
    m = [r for r in played if r["min_esperados"]]
    if m:
        print("\nPor minutos jugados frente a los esperados (todas las estadísticas):")
        tramos = [("-8 o menos", -99, -8), ("-8 a -3", -8, -3), ("-3 a +3", -3, 3), ("+3 a +8", 3, 8), ("+8 o más", 8, 99)]
        for name, lo, hi in tramos:
            g = [r for r in m if lo <= r["min_reales"] - r["min_esperados"] < hi]
            if g:
                print(f"   {name:>10} min: n={len(g):3d} | real - proyección {mean(r['real'] - r['proyeccion'] for r in g):+.2f}"
                      f" | over {mean(r['real'] > r['linea'] for r in g):.0%}")
        # error de la proyección si hubiéramos acertado los minutos (escalado por minutos reales)
        ok = [r for r in m if r["min_esperados"] > 0]
        e_raw = mean(abs(r["real"] - r["proyeccion"]) for r in ok)
        e_min = mean(abs(r["real"] - r["proyeccion"] * r["min_reales"] / r["min_esperados"]) for r in ok)
        print(f"   Error medio {e_raw:.2f}; con los minutos reales sería {e_min:.2f} "
              f"-> los minutos explican un {1 - e_min / e_raw:.0%} del error.")

    b = [r for r in played if r["margen_final"] is not None]
    if b:
        print("\nPor marcador final (margen del equipo del jugador):")
        for name, cond in (("paliza a favor (>=15)", lambda x: x >= 15), ("ajustado (<15)", lambda x: abs(x) < 15),
                           ("paliza en contra (<=-15)", lambda x: x <= -15)):
            g = [r for r in b if cond(r["margen_final"])]
            if g:
                print(f"   {name:>26}: n={len(g):3d} | min reales - esperados "
                      f"{mean(r['min_reales'] - (r['min_esperados'] or r['min_reales']) for r in g):+.1f}"
                      f" | real - proyección {mean(r['real'] - r['proyeccion'] for r in g):+.2f}")

    nuevos = [r for r in played if (r["partidos_temporada"] or 0) < 3]
    if nuevos:
        print(f"\nCon menos de 3 partidos esta temporada: {len(nuevos)} líneas; la proyección sale casi entera de la "
              f"anterior (cambios de equipo y de rol no se ven).")

    bets = [r for r in rows if r["lado"] and r["real"] is not None and r["real"] != r["linea"] and r["cuota"]]
    if bets:
        win = [(r["real"] > r["linea"]) == (r["lado"] == "over") for r in bets]
        pnl = sum((r["cuota"] - 1) if w else -1 for r, w in zip(bets, win))
        print(f"\nLíneas con ventaja del modelo: {len(bets)}, aciertos {sum(win)} ({mean(win):.0%}), "
              f"resultado {pnl:+.2f} u, ROI {pnl / len(bets):+.1%}. Con una sola jornada esto es ruido.")

    print("\nMayores fallos de la proyección:")
    for r in sorted(played, key=lambda r: -abs(r["real"] - r["proyeccion"]))[:12]:
        print(f"   {r['jugador']:<24} {r['stat']:<4} proy {r['proyeccion']:>5} línea {r['linea']:>5} real {r['real']:>4.0f}"
              f" | min {r['min_reales']} (esperados {r['min_esperados'] and round(r['min_esperados'], 1)})"
              f" | margen {r['margen_final']}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("game_date", help="Jornada, AAAA-MM-DD")
    parser.add_argument("--out", help="CSV de salida. Por defecto revision_AAAA-MM-DD.csv")
    args = parser.parse_args()

    s = get_settings()
    session = make_session_factory(s.database_url)()
    preds = list(session.scalars(select(Prediction).where(Prediction.game_date == args.game_date)))
    if not preds:
        print(f"No hay líneas publicadas el {args.game_date} en {s.database_url}")
        return
    bdl = BalldontlieClient(s.balldontlie_api_key)
    # Todos los partidos del día, no solo los guardados en la línea: a los traspasados se les
    # guardaba el partido de su equipo anterior. Cada jugador juega un partido al día.
    boxes: dict[int, dict] = {}
    game_ids = sorted({g["id"] for g in bdl.games_on(date.fromisoformat(args.game_date))}
                      | {p.game_id for p in preds if p.game_id})
    print(f"{len(preds)} líneas; {len(game_ids)} partidos ese día. Descargando box scores...")
    for gid in game_ids:
        for r in bdl.game_stats(gid):
            boxes[(r.get("player") or {}).get("id")] = r

    rows = [row_for(p, boxes.get(p.player_id)) for p in preds]
    out = args.out or f"revision_{args.game_date}.csv"
    with open(out, "w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]), delimiter=";")
        writer.writeheader()
        writer.writerows(rows)
    summarize(rows)
    print(f"\nTodo en {out}")


if __name__ == "__main__":
    main()
