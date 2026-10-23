"""Rellena la tabla de boxscores (propdeep/boxscores.py) de una temporada entera.

Por qué: la jornada automática solo guarda lo que falta de la temporada en curso. Para la
defensa por posición, el ritmo y el uso del principio de temporada hace falta también la anterior.

Uso (con el venv activado, desde la raíz):

    python -m scripts.sincronizar_boxscores --temporada 2025 --desde-cache backtest_cache
        Sin llamar a nada: usa los JSON del backtest ya descargados.
    python -m scripts.sincronizar_boxscores --temporada 2026
        Con la API de Balldontlie, desde el 1 de octubre hasta ayer (una petición por día).
"""
from __future__ import annotations

import argparse
import glob
import json
from datetime import date
from pathlib import Path

from propdeep import boxscores
from propdeep.config import get_settings
from propdeep.db import make_session_factory


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--temporada", type=int, required=True, help="Formato Balldontlie: 2025 = 2025-26")
    parser.add_argument("--desde-cache", help="Carpeta del backtest (p. ej. backtest_cache): sin llamadas a la API")
    args = parser.parse_args()
    s = get_settings()
    session = make_session_factory(s.database_url)()
    if args.desde_cache:
        new = 0
        for f in sorted(glob.glob(f"{args.desde_cache}/bdl/stats_{args.temporada}_*.json")):
            new += boxscores.store(session, json.loads(Path(f).read_text(encoding="utf-8")))
        print(f"{new} filas nuevas de la temporada {args.temporada} desde {args.desde_cache}")
        return
    from propdeep.clients.balldontlie import BalldontlieClient

    new = boxscores.sync(session, BalldontlieClient(s.balldontlie_api_key), args.temporada,
                         min(date.today(), date(args.temporada + 1, 7, 1)), start=date(args.temporada, 10, 1))
    print(f"{new} filas nuevas de la temporada {args.temporada} desde Balldontlie")


if __name__ == "__main__":
    main()
