"""¿La nota (propdeep/nota.py) dice algo? Validación con el backtest guardado. No gasta créditos.

Para cada línea principal de puntos de 2025-26 se construye el análisis como en producción (con
su estimación y las casas), se calcula la nota y se compara el lado elegido con lo que pasó:

- Por tramos de nota: cuánto acierta el lado frente a lo que decía el precio justo del mercado
  (acierto - precio justo, en puntos). Si la nota sirve, sube con la nota y en las dos mitades.
- Por partes (valor, forma, matchup, fiabilidad): regresión logística del resultado con el precio
  justo como base. Lo que no predice nada no debería puntuar.

Uso (con el venv activado, desde la raíz):

    python -m scripts.validar_nota
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

from propdeep import fair
from propdeep.clients.balldontlie import canonical_name
from propdeep.clients.odds import parse_all_props
from propdeep.model import analyze, compute_splits, compute_trends, devig
from propdeep.nota import nota
from scripts.backtest import Season, strip_suffix, to_games, to_rows


def _load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def build(cache: str) -> pd.DataFrame:
    stats, prev = [], []
    for f in sorted(glob.glob(f"{cache}/bdl/stats_2025_*.json")):
        stats += _load(f)
    for f in sorted(glob.glob(f"{cache}/bdl/stats_2024_*.json")):
        prev += _load(f)
    season = Season(to_rows(prev) + to_rows(stats), to_games(_load(f"{cache}/bdl/games_2025.json")), 2025)
    by_name = defaultdict(list)
    for r in season.rows:
        by_name[(strip_suffix(r.player_name), r.day)].append(r)

    def side_of(row):
        g = season.games_by_id.get(row.game_id)
        if not g:
            return None, None
        home = g.home_id == row.team_id
        return home, (g.visitor_id if home else g.home_id)

    out = []
    for f in glob.glob(f"{cache}/odds/*_odds_date=*"):
        snap = _load(f).get("data")
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
            if not hist:
                continue
            count = defaultdict(int)
            for p in props:
                count[p.line] += 1
            line = max(count, key=lambda x: (count[x], -min(abs(devig(q.over_odds, q.under_odds) - 0.5)
                                                            for q in props if q.line == x)))
            at_line = [p for p in props if p.line == line]
            main = min(at_line, key=lambda q: 1 / q.over_odds + 1 / q.under_odds)
            values = [h.stats["pts"] for h in hist]
            trends = compute_trends(values, [h.minutes for h in hist], line,
                                    sum(1 for h in hist if h.season == season.season))
            ctx = season.context(row, "pts")
            home, opp = zip(*(side_of(h) for h in hist))
            trends.splits = compute_splits(values, list(home), list(opp), line, side_of(row)[1])
            try:
                a = analyze(row.player_name, "pts", line, main.over_odds, main.under_odds, trends, ctx,
                            model_weight=0.2).to_dict()
            except ValueError:
                continue
            books = [{"bookmaker": p.bookmaker, "line": p.line, "over_odds": p.over_odds, "under_odds": p.under_odds}
                     for p in props]
            a["books"] = books
            a["estimate"] = fair.estimate("pts", line, a["prob_over_model"], a["prob_over_market"], trends.sd, books)
            n = nota(a)
            actual = row.stats["pts"]
            if n is None or actual == line:
                continue
            won = (actual > line) == (n.side == "over")
            out.append({"fecha": day, "score": n.score, "side": n.side, "prob": n.prob, "fair": n.fair,
                        "y": float(won), **n.parts})
    return pd.DataFrame(out)


def report(d: pd.DataFrame) -> None:
    corte = sorted(d.fecha.unique())[len(d.fecha.unique()) // 2]
    d["mitad"] = np.where(d.fecha < corte, "1.ª", "2.ª")
    d["exceso"] = d.y - d.fair
    print(f"{len(d)} líneas con nota. Lado: {d.side.value_counts().to_dict()}")
    print(f"Nota: media {d.score.mean():.1f}, percentiles 50/75/90/95/99: "
          f"{[int(d.score.quantile(q)) for q in (0.5, 0.75, 0.9, 0.95, 0.99)]}\n")
    print("Por tramos de nota: acierto del lado - precio justo (puntos), n | 1.ª mitad | 2.ª mitad")
    d["tramo"] = pd.qcut(d.score, 5, duplicates="drop")
    for tramo, t in d.groupby("tramo", observed=True):
        se = t.exceso.std() / math.sqrt(len(t))
        halves = " | ".join(f"{h} {100 * g.exceso.mean():+.1f}" for h, g in t.groupby("mitad"))
        print(f"  {str(tramo):16s} n={len(t):5d}  {100 * t.exceso.mean():+.1f} ± {196 * se:.1f}  | {halves}")

    import statsmodels.api as sm

    print("\nQué parte predice algo: regresión logística del resultado con el precio justo como base")
    lm = np.log(d.fair / (1 - d.fair))
    parts = ["valor_modelo", "valor_precio", "forma", "matchup", "fiabilidad"]
    for nombre, t in (("Total", d), ("1.ª mitad", d[d.mitad == "1.ª"]), ("2.ª mitad", d[d.mitad == "2.ª"])):
        res = sm.GLM(t.y, sm.add_constant(t[parts]), family=sm.families.Binomial(),
                     offset=lm.loc[t.index]).fit()
        coefs = ", ".join(f"{p} {res.params[p]:+.2f} (p={res.pvalues[p]:.2f})" for p in parts)
        print(f"  {nombre}: {coefs}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--cache", default="backtest_cache")
    args = parser.parse_args()
    report(build(args.cache))


if __name__ == "__main__":
    main()
