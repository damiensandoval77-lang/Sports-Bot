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
STATUS = ROOT / "docs" / "odds_fetch_status.json"
BASE = "https://api.the-odds-api.com/v4/sports/basketball_nba"
MARKETS = ("player_points", "player_rebounds", "player_assists", "player_points_rebounds_assists")
MAX_EVENTS = min(20, max(1, int(os.environ.get('ODDS_MAX_EVENTS', '15'))))
MAX_OUTCOMES_PER_EVENT = min(1600, max(100, int(os.environ.get('ODDS_OUTCOMES_PER_EVENT', '1000'))))
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
            # Round-robin distinct PLAYERS within each market, not only the
            # four stat types. This prevents a few stars or alphabetical
            # provider ordering from consuming all available row slots.
            mixed=[]
            player_queues={}
            for label,pairs in types.items():
                by_player={}
                for pair in pairs:
                    by_player.setdefault(pair[0]["player"].casefold(),deque()).append(pair)
                player_queues[label]=by_player
            while any(any(by_player.values()) for by_player in player_queues.values()):
                for market in MARKETS:
                    label=market.replace("player_","").replace("_"," ").title()
                    by_player=player_queues.get(label,{})
                    for player in sorted(by_player):
                        if by_player[player]:
                            mixed.append(by_player[player].popleft())
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

def save_status(status, **detail):
    report={"generated_at":dt.datetime.now(dt.timezone.utc).isoformat(),
            "status":status,"provider":"The Odds API",
            "old_lines_may_be_stale":status!="FETCHED",
            "details":detail}
    STATUS.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")

def main():
    key = os.environ.get("ODDS_API_KEY", "").strip()
    if not key:
        save_status("MISSING_ODDS_API_KEY")
        print("ODDS_API_KEY not set; retaining old sportsbook snapshot.")
        return
    try:
        events, _ = request("/events", key)
        now = dt.datetime.now(dt.timezone.utc)
        upcoming = [e for e in events if dt.datetime.fromisoformat(e["commence_time"].replace("Z","+00:00")) > now]
        upcoming.sort(key=lambda e: e["commence_time"])
        picks = []
        remaining = None
        inspected = 0
        covered_events=[]
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
            covered_events.append({"id":event["id"],
                "game":event.get("away_team","")+" @ "+event.get("home_team",""),
                "start":event.get("commence_time"),
                "two_sided_outcomes":len(event_rows),
                "players_quoted":len({x["player"] for x in event_rows})})
        result = {"is_live": True, "updated_at": now.isoformat(timespec="minutes"),
            "slate_events_available":len(upcoming),
            "slate_events_checked":inspected,
            "slate_event_limit":MAX_EVENTS,
            "slate_events_not_checked":max(0,len(upcoming)-inspected),
            "events_covered":covered_events,
            "coverage_warning":("PARTIAL_PROVIDER_EVENT_OR_CREDIT_COVERAGE"
                if inspected<len(upcoming) else
                "ALL_PROVIDER_LISTED_EVENTS_CHECKED"),
            "remaining_provider_credits":int(remaining) if remaining is not None else None,
            "disclaimer": "Live sportsbook odds, NOT PrizePicks lines. No AI projections or win probabilities yet. Verify all lines before use.",
            "picks": picks[:MAX_EVENTS * MAX_OUTCOMES_PER_EVENT]}
        OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        save_status("FETCHED",available_events=len(upcoming),
                    checked_events=inspected,remaining_credits=remaining,
                    outcome_rows=len(picks),
                    coverage=result["coverage_warning"])
        print(f"Published {len(result['picks'])} sportsbook outcomes from {inspected} events. Remaining credits: {remaining}")
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ValueError, KeyError) as exc:
        # Preserve last successful dashboard rather than overwriting it with sample data.
        code=exc.code if isinstance(exc,urllib.error.HTTPError) else None
        save_status("PROVIDER_FAILED",error_type=type(exc).__name__,
                    http_status=code,
                    reason="Rate limited or unauthorized" if code in (401,402,403,429)
                           else "Provider request failed or malformed")
        if code is not None:
            print(f"Odds provider returned HTTP {code}; leaving existing dashboard unchanged.")
        else:
            print(f"Odds update failed ({type(exc).__name__}); leaving existing dashboard unchanged.")
        raise SystemExit(1)

if __name__ == "__main__":
    main()
