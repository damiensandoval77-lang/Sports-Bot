#!/usr/bin/env python3
"""Fetch authorized NBA player prop odds into the GitHub Pages dashboard.
Requires ODDS_API_KEY secret. Never writes the key to the public output.
"""
import datetime as dt
import json
import os
import pathlib
import urllib.error
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "data.json"
BASE = "https://api.the-odds-api.com/v4/sports/basketball_nba"
MARKETS = ("player_points", "player_rebounds", "player_assists", "player_points_rebounds_assists")
MAX_EVENTS = 2  # Keep quota usage bounded; tune after reviewing remaining credits.

def request(path, key, **params):
    query = urllib.parse.urlencode({"apiKey": key, **params})
    req = urllib.request.Request(BASE + path + "?" + query, headers={"User-Agent": "Sports-Bot/1.0"})
    with urllib.request.urlopen(req, timeout=25) as response:
        return json.load(response), response.headers.get("x-requests-remaining")

def main():
    key = os.environ.get("ODDS_API_KEY", "").strip()
    if not key:
        print("ODDS_API_KEY not set; leaving sample dashboard unchanged.")
        return
    try:
        events, _ = request("/events", key)
        now = dt.datetime.now(dt.timezone.utc)
        upcoming = [e for e in events if dt.datetime.fromisoformat(e["commence_time"].replace("Z","+00:00")) > now]
        upcoming.sort(key=lambda e: e["commence_time"])
        picks = []
        remaining = None
        for event in upcoming[:MAX_EVENTS]:
            payload, remaining = request("/events/" + urllib.parse.quote(event["id"], safe="") + "/odds", key,
                regions="us", markets=",".join(MARKETS), oddsFormat="american")
            for book in payload.get("bookmakers", []):
                for market in book.get("markets", []):
                    if market.get("key") not in MARKETS:
                        continue
                    for outcome in market.get("outcomes", []):
                        if outcome.get("name") not in ("Over", "Under") or not outcome.get("description"):
                            continue
                        picks.append({"player": outcome["description"], "stat": market["key"].replace("player_","").replace("_"," ").title(),
                            "direction": "More" if outcome["name"] == "Over" else "Less",
                            "line": outcome.get("point"), "projection": None, "odds": outcome.get("price"),
                            "source": book.get("title","Unknown"), "game": event.get("away_team","") + " @ " + event.get("home_team",""),
                            "start": event.get("commence_time"), "market_updated": market.get("last_update")})
        result = {"is_live": True, "updated_at": now.isoformat(timespec="minutes"),
            "disclaimer": "Live sportsbook odds, NOT PrizePicks lines. No AI projections or win probabilities yet. Verify all lines before use.",
            "picks": picks[:500]}
        OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(f"Published {len(result['picks'])} sportsbook outcomes from {min(MAX_EVENTS,len(upcoming))} events. Remaining credits: {remaining}")
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ValueError, KeyError) as exc:
        # Preserve last successful dashboard rather than overwriting it with sample data.
        if isinstance(exc, urllib.error.HTTPError):
            print(f"Odds provider returned HTTP {exc.code}; leaving existing dashboard unchanged.")
        else:
            print(f"Odds update failed ({type(exc).__name__}); leaving existing dashboard unchanged.")
        raise SystemExit(1)

if __name__ == "__main__":
    main()
