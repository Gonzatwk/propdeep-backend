"""Calibración de la probabilidad estimada (propdeep/fair.py) con el backtest guardado. No gasta créditos.

Por qué: la probabilidad que verá el usuario parte del precio justo del mercado y se tuerce un
poco hacia el modelo. Cuánto se tuerce (alpha, beta) lo deciden los datos con una regresión
logística sobre la temporada 2025-26, evaluada mes a mes solo con los meses anteriores.

Uso (con el venv activado, desde la raíz):

    python -m scripts.calibracion                    # líneas principales: alpha y beta
    python -m scripts.calibracion --alternativas     # líneas alternativas: inflado de la desviación

Necesita el backtest con todas las casas (`--todas-casas --sin-companeros`) y, para las
alternativas, la caché de Balldontlie y The Odds API (`backtest_cache/`).
"""
from __future__ import annotations

import argparse
import glob
import json
import math
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

DEFAULT_CSV = "backtest_out/2026-10-24/odds-api-casas/lineas.csv"


def _logit(p):
    p = np.clip(p, 1e-4, 1 - 1e-4)
    return np.log(p / (1 - p))


def logloss(p, y) -> float:
    p = np.clip(np.asarray(p, float), 1e-6, 1 - 1e-6)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def main_lines(csv: str) -> pd.DataFrame:
    """Una fila por jugador y partido: la línea que ofrecen más casas, con el consenso sin margen."""
    d = pd.read_csv(csv)
    d = d[d.real != d.linea]
    g = d.groupby(["fecha", "jugador", "estadistica", "linea"]).agg(
        casas=("casa", "size"), p_mercado=("p_mercado", "mean"), p_modelo=("p_modelo_base", "first"),
        real=("real", "first")).reset_index()
    g["equilibrio"] = (g.p_mercado - 0.5).abs()
    g = g.sort_values(["fecha", "jugador", "estadistica", "casas", "equilibrio"],
                      ascending=[True, True, True, False, True])
    g = g.drop_duplicates(["fecha", "jugador", "estadistica"]).copy()
    g["y"] = (g.real > g.linea).astype(float)
    g["mes"] = g.fecha.str[:7]
    return g


def fit(df: pd.DataFrame) -> tuple[float, float]:
    import statsmodels.api as sm

    lm = _logit(df.p_mercado.values)
    x = _logit(df.p_modelo.values) - lm
    res = sm.GLM(df.y.values, sm.add_constant(x), family=sm.families.Binomial(), offset=lm).fit()
    return float(res.params[0]), float(res.params[1])


def calibrated(df: pd.DataFrame, alpha: float, beta: float) -> np.ndarray:
    lm = _logit(df.p_mercado.values)
    z = alpha + lm + beta * (_logit(df.p_modelo.values) - lm)
    return 1 / (1 + np.exp(-z))


def run_main(csv: str) -> None:
    g = main_lines(csv)
    meses = sorted(g.mes.unique())
    print(f"{len(g)} líneas principales ({g.estadistica.unique().tolist()}), {len(meses)} meses\n")
    print("Mes a mes, ajustando solo con los meses anteriores (log-loss, menos es mejor):")
    print("  mes       n     mercado  calibrada  mezcla_0,2   alpha    beta")
    rows = []
    for m in meses[2:]:
        train, test = g[g.mes < m], g[g.mes == m]
        a, b = fit(train)
        pc = calibrated(test, a, b)
        mix = 0.2 * test.p_modelo.values + 0.8 * test.p_mercado.values
        rows.append(test.assign(p_cal=pc, p_mix=mix))
        print(f"  {m}  {len(test):5d}   {logloss(test.p_mercado, test.y):.5f}   {logloss(pc, test.y):.5f}"
              f"   {logloss(mix, test.y):.5f}   {a:+.4f}  {b:+.4f}")
    wf = pd.concat(rows)
    corte = sorted(wf.fecha.unique())[len(wf.fecha.unique()) // 2]
    for nombre, parte in (("Total", wf), ("1.ª mitad", wf[wf.fecha < corte]), ("2.ª mitad", wf[wf.fecha >= corte])):
        lm, lc, lx = logloss(parte.p_mercado, parte.y), logloss(parte.p_cal, parte.y), logloss(parte.p_mix, parte.y)
        print(f"{nombre:10s} n={len(parte):5d}  mercado {lm:.5f}  calibrada {lc:.5f} ({lc - lm:+.5f})"
              f"  mezcla 0,2 {lx:.5f} ({lx - lm:+.5f})")
    print("\nFiabilidad de la calibrada (mes a mes): dice -> pasa")
    wf["tramo"] = pd.cut(wf.p_cal, [0, 0.4, 0.45, 0.5, 0.55, 0.6, 1])
    for tramo, t in wf.groupby("tramo", observed=True):
        print(f"  {str(tramo):13s} n={len(t):5d}  {t.p_cal.mean():.3f} -> {t.y.mean():.3f}")
    a, b = fit(g)
    print(f"\nCon toda la temporada: alpha={a:+.4f} beta={b:+.4f} (cópialos en propdeep/fair.py)")


# ------------------------------------------------------------------ alternativas

def run_alternativas(cache: str) -> None:
    """¿La distribución anclada acierta en las líneas alternativas? Se compara con el resultado y
    con la probabilidad sin margen que da la propia casa en esa línea."""
    from scripts.backtest import Season, strip_suffix, to_games, to_rows
    from propdeep.clients.balldontlie import canonical_name
    from propdeep.clients.odds import parse_all_props
    from propdeep import fair
    from propdeep.model import compute_trends, devig, project, prob_over

    def load(p):
        return json.loads(Path(p).read_text(encoding="utf-8"))

    stats, prev = [], []
    for f in sorted(glob.glob(f"{cache}/bdl/stats_2025_*.json")):
        stats += load(f)
    for f in sorted(glob.glob(f"{cache}/bdl/stats_2024_*.json")):
        prev += load(f)
    season = Season(to_rows(prev) + to_rows(stats), to_games(load(f"{cache}/bdl/games_2025.json")), 2025)
    by_name = defaultdict(list)
    for r in season.rows:
        by_name[(strip_suffix(r.player_name), r.day)].append(r)

    out = []
    for f in glob.glob(f"{cache}/odds/*_odds_date=*"):
        snap = load(f).get("data")
        if not snap:
            continue
        day = (datetime.fromisoformat(snap["commence_time"].replace("Z", "+00:00")) - timedelta(hours=12)).date().isoformat()
        per_player = defaultdict(list)
        for p in parse_all_props(snap):
            per_player[p.player].append(p)
        for name, props in per_player.items():
            rows = by_name.get((strip_suffix(canonical_name(name)), day), [])
            if len(rows) != 1:
                continue
            row = rows[0]
            hist = season.history(row.player_id, day)
            if len(hist) < 5:
                continue
            trends = compute_trends([h.stats["pts"] for h in hist], [h.minutes for h in hist], 0.5,
                                    sum(1 for h in hist if h.season == season.season))
            proj = project("pts", trends, season.context(row, "pts"))
            count = defaultdict(int)
            for p in props:
                count[p.line] += 1
            main = max(count, key=lambda x: (count[x], -min(abs(devig(q.over_odds, q.under_odds) - 0.5)
                                                            for q in props if q.line == x)))
            books = [{"bookmaker": p.bookmaker, "line": p.line, "over_odds": p.over_odds, "under_odds": p.under_odds}
                     for p in props]
            est = fair.estimate("pts", main, prob_over("pts", proj, trends.sd, main),
                                fair.fair_price(books, main).prob_over, trends.sd, books)
            actual = row.stats["pts"]
            for p in props:
                if p.line == main or actual == p.line:
                    continue
                out.append({"fecha": day, "pg": f"{day}|{name}", "gap": p.line - main, "y": float(actual > p.line),
                            "linea": p.line, "main": main, "p_est": est["prob_over"], "sd": trends.sd,
                            "p_casa": devig(p.over_odds, p.under_odds), "casa": p.bookmaker})
    alt = pd.DataFrame(out)
    print(f"{len(alt)} cuotas en líneas alternativas de {alt.pg.nunique()} jugador-partido"
          f" (casas: {alt.casa.value_counts().to_dict()})\n")
    anchors = alt.drop_duplicates("pg")[["pg", "sd", "main", "p_est"]]
    base = fair.SD_INFLATION

    def anchored_probs(k: float) -> list[float]:
        fair.SD_INFLATION = k  # el ancla se recalcula con el mismo inflado que se evalúa
        mu = {r.pg: fair.anchored_mean("pts", r.sd, r.main, r.p_est) for r in anchors.itertuples()}
        return [prob_over("pts", mu[pg], sd * k, line) for pg, sd, line in zip(alt.pg, alt.sd, alt.linea)]

    corte = sorted(alt.fecha.unique())[len(alt.fecha.unique()) // 2]
    h1, h2 = (alt.fecha < corte).values, (alt.fecha >= corte).values
    print("Inflado de la desviación -> log-loss en las alternativas (menos es mejor). Casa sin margen:",
          f"{logloss(alt.p_casa, alt.y):.5f} (1.ª mitad {logloss(alt.p_casa[h1], alt.y[h1]):.5f},"
          f" 2.ª {logloss(alt.p_casa[h2], alt.y[h2]):.5f})")
    for k in (1.0, 1.06, 1.12, 1.18, 1.24, 1.3):
        p = np.array(anchored_probs(k))
        print(f"  x{k:.2f}: {logloss(p, alt.y):.5f} (1.ª mitad {logloss(p[h1], alt.y[h1]):.5f},"
              f" 2.ª {logloss(p[h2], alt.y[h2]):.5f})")
    alt["p_anc"] = anchored_probs(base)
    fair.SD_INFLATION = base
    print("\nPor distancia a la línea principal (dice -> pasa | casa sin margen):")
    alt["tramo"] = pd.cut(alt.gap, [-99, -5.5, -2.5, -0.5, 0.5, 2.5, 5.5, 99])
    for tramo, t in alt.groupby("tramo", observed=True):
        print(f"  {str(tramo):14s} n={len(t):6d}  {t.p_anc.mean():.3f} -> {t.y.mean():.3f}  | casa {t.p_casa.mean():.3f}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("lineas", nargs="?", default=DEFAULT_CSV)
    parser.add_argument("--alternativas", action="store_true")
    parser.add_argument("--cache", default="backtest_cache")
    args = parser.parse_args()
    if args.alternativas:
        run_alternativas(args.cache)
    else:
        run_main(args.lineas)


if __name__ == "__main__":
    main()
