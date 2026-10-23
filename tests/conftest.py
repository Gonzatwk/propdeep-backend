from datetime import datetime, timezone

import pytest

# El fixture "api" (backend con casas y Balldontlie falsos) lo comparten varios archivos.
from tests.test_board import api  # noqa: F401


@pytest.fixture(autouse=True)
def reloj_de_liquidacion(monkeypatch):
    """La liquidación anula lo que lleva días sin jugarse: con el reloj real, los tests (jornada del
    20-nov-2026) empezarían a fallar al pasar esa fecha. Se fija el día siguiente."""
    from propdeep import track_record

    monkeypatch.setattr(track_record, "_now", lambda: datetime(2026, 11, 21, 10, tzinfo=timezone.utc))
