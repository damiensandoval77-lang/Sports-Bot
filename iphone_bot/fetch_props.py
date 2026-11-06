#!/usr/bin/env python3
"""Fetch authorized NBA player prop odds into the GitHub Pages dashboard.
Requires ODDS_API_KEY secret. Never writes the key to the public output.
"""
import datetime as dt
import json
import math
import os
import pathlib
import urllib.error
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "data.json"
BASE = "https://api.the-odds-api.com/v4/sports/basketball_nba"
MARKETS = ("player_points", "player_rebounds", "player_assists", "player_points_rebounds_assists")
MAX_EVENTS = min(3, max(1, int(os.environ.get('ODDS_MAX_EVENTS', '2'))))
MAX_OUTCOMES_PER_EVENT = 450
MIN_REMAINING_CREDITS = 12  # Stop before the account is nearly depleted.

def request(path, key, **params):
    query = urllib.parse.urlencode({"apiKey": key, **params})
    req = urllib.request.Request(BASE + path + "?" + query, headers={"User-Agent": "Sports-Bot/1.0"})
    with urllib.request.urlopen(req, timeout=25) as response:
        return json.load(response), response.headers.get("x-requests-remaining")

def balanced_bookmaker_rows(bookmakers,event,max_outcomes):
    """Round-robin COMPLETE two-sided prop quotes across available books."""
    from collections import deque
    queues=[]
    for book in bookmakers:
        all_pairs=[]
        for market in book.get("markets",[]):
            if market.get("key") not in MARKETS:
                continue
            pairs={}
            for outcome in market.get("outcomes",[]):
                player=outcome.get("description")
                side=outcome.get("name")
                point=outcome.get("point")
                if not player or side not in ("Over","Under") or point is None:
                    continue
                try:
                    line=float(point)
                    odd=int(outcome.get("price"))
                except (ValueError,TypeError):
                    continue
                if not math.isfinite(line) or odd==0:
                    continue
                pairs.setdefault((player,line),{})[side]=odd
            for (player,line),sides in pairs.items():
                if "Over" not in sides or "Under" not in sides:
                    continue
                common={"player":player,"line":line,"projection":None,
                    "stat":market["key"].replace("player_","").replace("_"," ").title(),
                    "source":book.get("title","Unknown"),
                    "game":event.get("away_team","")+" @ "+event.get("home_team",""),
                    "start":event.get("commence_time"),
                    "market_updated":market.get("last_update")}
                all_pairs.append([
                    dict(common,direction="More",odds=sides["Over"]),
                    dict(common,direction="Less",odds=sides["Under"])])
        if all_pairs:
            # Balance market TYPES inside a book as well; otherwise a points
            # block can exhaust the cap before rebounds, assists or PRA.
            types={}
            for pair in all_pairs:
                types.setdefault(pair[0]["stat"],deque()).append(pair)
            mixed=[]
            while any(types.values()):
                for market in MARKETS:
                    label=market.replace("player_","").replace("_"," ").title()
                    if types.get(label):
                        mixed.append(types[label].popleft())
            queues.append(deque(mixed))
    result=[]
    while queues and len(result)+2<=max_outcomes:
        remaining=[]
        for q in queues:
            if q and len(result)+2<=max_outcomes:
                result.extend(q.popleft())
            if q:
                remaining.append(q)
        queues=remaining
    return result

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
        inspected = 0
        for event in upcoming[:MAX_EVENTS]:
            if remaining is not None and int(remaining) < MIN_REMAINING_CREDITS:
                print('Stopping early to preserve Odds API credits.', flush=True)
                break
            inspected += 1
            event_rows = []
            payload, remaining = request("/events/" + urllib.parse.quote(event["id"], safe="") + "/odds", key,
                regions="us", markets=",".join(MARKETS), oddsFormat="american")
            event_rows = balanced_bookmaker_rows(
                payload.get("bookmakers", []), event, MAX_OUTCOMES_PER_EVENT)
            # Spread a fixed display cap across books while keeping each
            # Over/Under price pair intact. No additional API calls.
            picks.extend(event_rows)
        result = {"is_live": True, "updated_at": now.isoformat(timespec="minutes"),
            "disclaimer": "Live sportsbook odds, NOT PrizePicks lines. No AI projections or win probabilities yet. Verify all lines before use.",
            "picks": picks[:MAX_EVENTS * MAX_OUTCOMES_PER_EVENT]}
        OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(f"Published {len(result['picks'])} sportsbook outcomes from {inspected} events. Remaining credits: {remaining}")
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ValueError, KeyError) as exc:
        # Preserve last successful dashboard rather than overwriting it with sample data.
        if isinstance(exc, urllib.error.HTTPError):
            print(f"Odds provider returned HTTP {exc.code}; leaving existing dashboard unchanged.")
        else:
            print(f"Odds update failed ({type(exc).__name__}); leaving existing dashboard unchanged.")
        raise SystemExit(1)

if __name__ == "__main__":
    main()
