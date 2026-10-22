"""¿El ajuste por compañero fuera aporta algo que la casa no tenga ya en la línea?

Uso (después de un backtest con cuotas reales, que ya incluye el ajuste):
    python -m scripts.backtest --lineas odds-api --stats pts --todas-casas --max-creditos 1
    python -m scripts.analisis_companeros backtest_out/odds-api-casas/lineas.csv

Mira solo las líneas con algún compañero importante fuera y compara:
1. Si cuando el ajuste sube la proyección salen más overs de lo que decía la casa (y al revés).
2. Brier del modelo con y sin el ajuste, y del mercado.
3. Regresión con la casa como base: si el término "ajuste" sale positivo y claro, la casa no lo
   descuenta del todo y hay algo aprovechable. Si sale ~0, la casa ya lo sabía.
4. ROI de la regla de producción (peso MODEL_WEIGHT, ventaja >= MIN_EDGE, mejor cuota) con y sin el ajuste.
"""
from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

from scripts.analisis_peso import bets, ci, load


def logit(p):
    p = np.clip(p, 0.02, 0.98)
    return np.log(p / (1 - p))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("lineas")
    parser.add_argument("--peso", type=float, default=0.2)
    parser.add_argument("--ventaja", type=float, default=0.03)
    args = parser.parse_args()
    d = load(args.lineas)
    if "factor_companeros" not in d:
        raise SystemExit("Este lineas.csv es de antes del ajuste: repite el backtest (sale de la caché).")
    adj = d[d.factor_companeros != 1.0].copy()
    print(f"{len(d)} líneas; {len(adj)} con algún compañero importante fuera "
          f"({adj.fecha.nunique()} jornadas, {adj.jugador.nunique()} jugadores).")
    if len(adj) < 50:
        print("Muy pocas para sacar conclusiones.")
        return

    for name, g in (("sube (factor > 1)", adj[adj.factor_companeros > 1]), ("baja (factor < 1)", adj[adj.factor_companeros < 1])):
        if len(g):
            print(f"  Ajuste que {name}: n={len(g)} | over real {g.over.mean():.1%} | casa {g.p_mercado.mean():.1%} "
                  f"| modelo sin ajuste {g.p_modelo_base.mean():.1%} | con ajuste {g.p_modelo.mean():.1%}")

    def brier(col):
        return ((adj[col] - adj.over) ** 2).mean()

    print(f"\nBrier en esas líneas: casa {brier('p_mercado'):.4f} | modelo sin ajuste {brier('p_modelo_base'):.4f} "
          f"| con ajuste {brier('p_modelo'):.4f}")

    import statsmodels.api as sm

    X = pd.DataFrame({
        "const": 1.0,
        "modelo_base": logit(adj.p_modelo_base) - logit(adj.p_mercado),
        "ajuste": logit(adj.p_modelo) - logit(adj.p_modelo_base),
    })
    fit = sm.GLM(adj.over, X, family=sm.families.Binomial(), offset=logit(adj.p_mercado)).fit()
    print("\nRegresión con la casa como base (coeficiente, p-valor):")
    for k in ("modelo_base", "ajuste"):
        print(f"  {k:12s} {fit.params[k]:+.3f}  p={fit.pvalues[k]:.3f}")
    print("  'ajuste' > 0 con p < 0,05: el ajuste aporta información que la casa no tiene del todo.")

    sin = d.assign(p_modelo=d.p_modelo_base)
    for label, data in (("con ajuste", d), ("sin ajuste", sin)):
        b = bets(data, args.peso, args.ventaja)
        sub = b[b.factor_companeros != 1.0]
        lo, hi = ci(b)
        print(f"\nRegla peso {args.peso} ventaja {args.ventaja:.0%} {label}: {len(b)} apuestas, ROI {b.pnl.mean():+.1%} "
              f"(IC {lo:+.1%} a {hi:+.1%}); de ellas con compañero fuera {len(sub)}, ROI "
              f"{sub.pnl.mean():+.1%}" if len(sub) else f"\nRegla {label}: {len(b)} apuestas, ROI {b.pnl.mean():+.1%}")


if __name__ == "__main__":
    main()
