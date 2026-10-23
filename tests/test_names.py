"""Emparejar el nombre de The Odds API con el jugador de Balldontlie."""
import httpx

from propdeep.clients.balldontlie import BalldontlieClient, canonical_name
from scripts.backtest import strip_suffix

PLAYERS = {
    "Jones": [{"id": 1, "first_name": "Herbert", "last_name": "Jones"},
              {"id": 2, "first_name": "Tre", "last_name": "Jones"}],
    "Jackson": [{"id": 3, "first_name": "Jaren", "last_name": "Jackson Jr."},
                {"id": 4, "first_name": "Isaiah", "last_name": "Jackson"}],
    "Williams": [{"id": 5, "first_name": "Vince", "last_name": "Williams Jr."},
                 {"id": 6, "first_name": "Jaylin", "last_name": "Williams"}],
    "Hyland": [{"id": 7, "first_name": "Nah'Shon", "last_name": "Hyland"}],
    "Doncic": [{"id": 8, "first_name": "Luka", "last_name": "Dončić"}],
}


def _client(searches):
    def handler(request):
        term = request.url.params["search"]
        searches.append(term)
        return httpx.Response(200, json={"data": PLAYERS.get(term, []), "meta": {}})

    return BalldontlieClient("k", http=httpx.Client(base_url="https://bdl.test", transport=httpx.MockTransport(handler)))


def test_nicknames_find_the_real_player():
    searches = []
    bdl = _client(searches)
    assert bdl.find_player("Herb Jones")["id"] == 1
    assert bdl.find_player("Bones Hyland")["id"] == 7
    assert bdl.find_player("Vincent Williams Jr")["id"] == 5


def test_suffix_is_not_the_search_term():
    searches = []
    bdl = _client(searches)
    assert bdl.find_player("Jaren Jackson Jr.")["id"] == 3
    assert bdl.find_player("Jaren Jackson")["id"] == 3  # sin el sufijo también
    assert searches[0] == "Jackson"


def test_accents_and_unknown_players():
    bdl = _client([])
    assert bdl.find_player("Luka Doncic")["id"] == 8
    assert bdl.find_player("Tre Jones")["id"] == 2
    assert bdl.find_player("Nadie Jones") is None  # varios candidatos y ninguno coincide


def test_backtest_matches_nicknames_too():
    assert strip_suffix(canonical_name("Bones Hyland")) == strip_suffix("Nah'Shon Hyland")
    assert strip_suffix(canonical_name("Ron Holland")) == strip_suffix("Ronald Holland II")
    assert canonical_name("Luka Dončić") == "luka doncic"
