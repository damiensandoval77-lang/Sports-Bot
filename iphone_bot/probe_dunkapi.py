import json, os, urllib.request
KEY = os.environ["DUNKAPI_KEY"]
BASE = "https://mcp.dunkapi.com/v1/"
def request(endpoint, data):
    req = urllib.request.Request(BASE + endpoint, json.dumps(data).encode("utf-8"), headers={"x-api-key": KEY, "Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)
def main():
    date = os.getenv("DUNK_GAME_DATE", "2026-03-15")
    games = request("list_games", {"date": date, "status": "final", "season_type": "regular", "league": "nba", "limit": 10}).get("games", [])
    if not games:
        raise SystemExit("No completed regular-season games available on this date")
    game_id = str(games[0]["game_id"])
    print("Selected game:", game_id)
    estimate = request("get_player_props", {"game_id": game_id, "estimate_only": True, "league": "nba"})
    print("Provider estimate:", json.dumps(estimate)[:2000])
    print("Probe only: no historical prop records purchased.")
if __name__ == "__main__":
    main()
