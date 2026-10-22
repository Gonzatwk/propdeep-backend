"""Paper bets: bank simulado en euros, separado de «Mis picks»."""
import pytest

import main
from tests.fakes import stat_row
from tests.test_board import ADMIN, DAY
from tests.test_picks import gonza  # noqa: F401


def _lines(api, headers):
    api.c.post(f"/admin/board?game_date={DAY}", headers=ADMIN)
    lines = api.c.get("/board/games/ev1", headers=headers).json()["lines"]
    return next(x for x in lines if x["stat"] == "pts"), next(x for x in lines if x["stat"] == "ast")


def test_paper_bank_moves_with_settled_bets_and_stays_out_of_mis_picks(api, gonza):  # noqa: F811
    assert api.c.get("/paper").status_code == 403
    s = api.c.post("/paper/bank", json={"initial": 200}, headers=gonza).json()
    assert s["bank"]["current"] == 200 and s["suggested"]["stake"] == 4.0

    pts, ast = _lines(api, gonza)
    s = api.c.post("/paper/bets", json={"line_id": pts["id"], "side": "over", "odds": 2.0, "bookmaker": "Bet365",
                                        "stake": 10}, headers=gonza).json()
    assert s["bank"]["at_risk"] == 10 and s["bank"]["available"] == 190
    assert s["bets"][0]["potential_return"] == 20.0
    s = api.c.post("/paper/parlays", json={"bookmaker": "Bet365", "stake": 10, "odds": 5, "legs": [
        {"line_id": pts["id"], "side": "over", "odds": 2.0}, {"line_id": ast["id"], "side": "under", "odds": 2.5},
    ]}, headers=gonza).json()
    assert s["bets"][0]["kind"] == "parlay" and s["bets"][0]["potential_return"] == 50.0

    got = api.c.get("/picks").json()
    assert got["picks"] == [] and got["parlays"] == []

    # 40 puntos (gana el más) y 8 asistencias (pierde el menos de 7,5): +10 € y -10 €.
    main.bdl_client().final_stats[999] = [stat_row(DAY, 40.0, game_id=999)]
    api.c.post("/admin/settle", headers=ADMIN)
    s = api.c.get("/paper", headers=gonza).json()
    b = s["bank"]
    assert b["current"] == 200 and b["profit"] == 0 and b["won"] == 1 and b["lost"] == 1
    assert b["roi"] == 0 and b["worst_losing_streak"] == 1 and b["max_drawdown"] == pytest.approx(10.0)
    assert [p["bank"] for p in s["curve"]][0] == 200 and len(s["curve"]) == 3

    # Empezar de cero no borra nada, pero cuenta desde ahora.
    s = api.c.post("/paper/bank", json={"initial": 300, "reset": True}, headers=gonza).json()
    assert s["bank"]["current"] == 300 and s["bets"] == []


def test_paper_bet_can_be_removed_before_the_game(api, gonza):  # noqa: F811
    pts, _ = _lines(api, gonza)
    s = api.c.post("/paper/bets", json={"line_id": pts["id"], "side": "over", "odds": 2.0, "bookmaker": "Bet365",
                                        "stake": 10}, headers=gonza).json()
    bet = s["bets"][0]
    assert api.c.delete(f"/paper/bets/single/{bet['id']}", headers=gonza).json()["bets"] == []
    assert api.c.delete(f"/paper/bets/single/{bet['id']}", headers=gonza).status_code == 404


def test_paper_bets_can_be_added_after_the_game_starts_but_picks_cannot(api, gonza):  # noqa: F811
    from tests.test_picks import BEFORE, MANUAL

    late = {**MANUAL, "commence_time": BEFORE}
    assert api.c.post("/picks", json=late, headers=gonza).status_code == 422
    r = api.c.post("/paper/bets", json={**late, "stake": 10}, headers=gonza)
    assert r.status_code == 201
    bet = r.json()["bets"][0]
    assert api.c.delete(f"/paper/bets/single/{bet['id']}", headers=gonza).status_code == 200
