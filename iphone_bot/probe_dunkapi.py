"""Small DunkAPI historical coverage check; only authenticated metadata requests.

Uses at most two list_games calls (2 credits each) and one free estimate request.
No API key or full private response is printed.
"""
import json
import os
import urllib.request
import urllib.error

KEY = os.environ.get("DUNKAPI_KEY", "").strip()
BASE = "https://mcp.dunkapi.com/v1/"

def request(endpoint, data):
    req = urllib.request.Request(
        BASE + endpoint, json.dumps(data).encode("utf-8"),
        headers={"x-api-key": KEY, "Content-Type": "application/json"},
        method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)

def main():
    if not KEY:
        raise SystemExit("DUNKAPI_KEY secret is missing from GitHub Actions")
    date = os.getenv("DUNK_GAME_DATE", "2026-03-15")
    queries = [
        {"date": date, "status": "final", "season_type": "regular", "league": "nba", "limit": 10},
        {"season": 2026, "season_type": "regular", "status": "final", "league": "nba", "limit": 5},
    ]
    games = []
    for index, query in enumerate(queries, start=1):
        payload = request("list_games", query)
        games = payload.get("games", []) if isinstance(payload, dict) else []
        print("Lookup", index, "returned", len(games), "games; response keys:",
              sorted(payload.keys()) if isinstance(payload,dict) else type(payload).__name__, flush=True)
        if games:
            break
    if not games:
        print("AUTH REQUEST ACCEPTED but the provider returned no games for either query.")
        print("This does not prove historical coverage or prop access. Check DunkAPI account and list_games documentation.")
        return
    completed = [g for g in games if g.get("game_id") and g.get("status") == "final"]
    if not completed:
        print("Returned games had no completed game_id; inspect provider documentation.")
        return
    selected = completed[0]
    game_id = str(selected["game_id"])
    print("Selected game ID", game_id, "date", selected.get("date"), flush=True)
    estimate = request("get_player_props", {"game_id": game_id, "estimate_only": True, "league": "nba"})
    if isinstance(estimate,dict):
        print("Cost estimate:", json.dumps({k: v for k,v in estimate.items()
              if k in {"cost","credits","estimated_credits","credits_required",
                       "estimated_cost","games","count","note","estimate_only"}})[:1200])
        print("Estimate response keys:",sorted(estimate.keys()))
    else:
        print("Unexpected estimate response type:",type(estimate).__name__)
    print("PROBE COMPLETE: no historical prop payload purchased.")
if __name__ == "__main__":
    main()
