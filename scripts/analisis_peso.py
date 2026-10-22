"""¿Cuánto peso merece el modelo frente al mercado? Análisis del lineas.csv del backtest con todas las casas.

Uso:
    python -m scripts.backtest --lineas odds-api --stats pts,reb,ast,fg3m --todas-casas
    python -m scripts.analisis_peso backtest_out/odds-api-casas/lineas.csv

Para cada estadística:
1. Regresión logística con la probabilidad del mercado como base: el coeficiente del modelo, ajustado
   solo con los meses anteriores a cada mes de prueba, es el peso que de verdad le dan los datos.
2. ROI de la regla de producción (mezcla con MODEL_WEIGHT, ventaja >= MIN_EDGE con la mejor cuota
   entre casas, una apuesta por jugador y día) para varios pesos, con IC 95 % por bootstrap de jornadas
   y por mitades de temporada. Si el ROI no aguanta en las dos mitades, no hay ventaja.
"""
from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

PESOS = (0.5, 0.3, 0.2, 0.1)
VENTAJAS = (0.03, 0.04, 0.05)


def load(path: str) -> pd.DataFrame:
    d = pd.read_csv(path)
    d = d[d.real != d.linea].copy()
    d["over"] = (d.real > d.linea).astype(int)
    d["mes"] = d.fecha.str[:7]
    return d


def model_coef(d: pd.DataFrame) -> list[tuple[str, float]]:
    import statsmodels.api as sm

    lm = np.log(d.p_mercado / (1 - d.p_mercado))
    pm = d.p_modelo.clip(0.02, 0.98)
    x = np.log(pm / (1 - pm)) - lm  # lo que el modelo añade sobre el mercado
    out = []
    for m in sorted(d.mes.unique())[2:]:
        tr = d.mes < m
        X = sm.add_constant(x[tr].rename("modelo"))
        fit = sm.GLM(d.over[tr], X, family=sm.families.Binomial(), offset=lm[tr]).fit()
        out.append((m, float(fit.params["modelo"])))
    return out


def bets(d: pd.DataFrame, w: float, edge: float) -> pd.DataFrame:
    p = w * d.p_modelo + (1 - w) * d.p_mercado
    eo, eu = p - 1 / d.cuota_over, (1 - p) - 1 / d.cuota_under
    r = d.assign(ev=np.maximum(eo, eu), lado=np.where(eo >= eu, "o", "u"))
    r = r.sort_values("ev", ascending=False).drop_duplicates(["fecha", "jugador"])
    b = r[r.ev >= edge].copy()
    win = np.where(b.lado == "o", b.over == 1, b.over == 0)
    b["pnl"] = np.where(win, np.where(b.lado == "o", b.cuota_over, b.cuota_under) - 1, -1.0)
    return b


def ci(b: pd.DataFrame, n: int = 2000, seed: int = 7) -> tuple[float, float]:
    if len(b) < 20:
        return float("nan"), float("nan")
    days = b.groupby("fecha").pnl.agg(["sum", "count"])
    idx = np.random.default_rng(seed).integers(0, len(days), (n, len(days)))
    roi = days["sum"].values[idx].sum(1) / days["count"].values[idx].sum(1)
    lo, hi = np.percentile(roi, [2.5, 97.5])
    return float(lo), float(hi)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("lineas", help="lineas.csv de backtest_out/odds-api-casas/")
    args = parser.parse_args()
    d = load(args.lineas)
    corte = sorted(d.fecha.unique())[len(d.fecha.unique()) // 2]
    for stat, g in d.groupby("estadistica"):
        print(f"\n=== {stat}: {len(g)} líneas, {g.casa.nunique()} casas ===")
        coefs = ", ".join(f"{m} {c:.2f}" for m, c in model_coef(g))
        print(f"Peso del modelo según los datos (por mes, solo con meses anteriores): {coefs}")
        for w in PESOS:
            for e in VENTAJAS:
                b = bets(g, w, e)
                if b.empty:
                    print(f"peso {w:.1f} ventaja {e:.0%}: sin apuestas")
                    continue
                lo, hi = ci(b)
                h1, h2 = b[b.fecha < corte].pnl.mean(), b[b.fecha >= corte].pnl.mean()
                print(f"peso {w:.1f} ventaja {e:.0%}: {len(b):5d} apuestas, ROI {b.pnl.mean():+.1%} "
                      f"(IC {lo:+.1%} a {hi:+.1%}) | 1.ª mitad {h1:+.1%} | 2.ª mitad {h2:+.1%}")


if __name__ == "__main__":
    main()
