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
COMPACT = ROOT / "docs" / "odds_compact.json"
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
            # Rotate across markets and then across players. Taking ALL
            # players from Points in one pass used to exhaust small event
            # caps before Rebounds/Assists/PRA were considered.
            market_players={}
            for label,pairs in types.items():
                by_player={}
                for pair in pairs:
                    by_player.setdefault(pair[0]["player"].casefold(),deque()).append(pair)
                market_players[label]=(by_player,deque(sorted(by_player)))
            while any(names for _,names in market_players.values()):
                for market in MARKETS:
                    label=market.replace("player_","").replace("_"," ").title()
                    if label not in market_players:continue
                    by_player,names=market_players[label]
                    if not names:continue
                    player=names.popleft()
                    mixed.append(by_player[player].popleft())
                    if by_player[player]:names.append(player)
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

def compact_for_dashboard(report,max_pairs_per_event=140):
    """Keep compact, real two-sided quotes across EVERY fetched NBA matchup.

    Prefer player breadth and market variety over bookmaker duplication.
    Do not alter an odd, line, timestamp, or invent availability.
    """
    from collections import defaultdict
    groups=defaultdict(list)
    for row in report.get("picks",[]):
        if row.get("game") and row.get("player") and row.get("stat"):
            groups[row["game"]].append(row)
    published=[];per_event=[]
    for event in report.get("events_covered",[]):
        game=event["game"]
        by_key={}
        for row in groups.get(game,[]):
            key=(row["player"].casefold(),row["stat"],row.get("line"),row.get("source"))
            pair=by_key.setdefault(key,{})
            if row.get("direction") in ("More","Less"):pair[row["direction"]]=row
        pairs=[v for v in by_key.values() if "More" in v and "Less" in v]
        # Retain distinct player-market pairs first, then alternate books.
        pairs.sort(key=lambda p:(p["More"]["stat"],p["More"]["player"].casefold(),
                                 str(p["More"].get("source",""))))
        by_player=defaultdict(list)
        for pair in pairs:
            k=(pair["More"]["player"].casefold(),pair["More"]["stat"])
            by_player[k].append(pair)
        selected=[]
        # Cycle markets and players together. Never let an alphabetically
        # early market monopolize the compact feed and hide points/PRA.
        by_market=defaultdict(list)
        for k in by_player:
            by_market[k[1]].append(k)
        market_order=("Points","Rebounds","Assists","Points Rebounds Assists")
        for market in by_market:
            by_market[market].sort()
        while len(selected)<max_pairs_per_event and any(by_player.values()):
            for market in market_order:
                keys=by_market.get(market,[])
                for key in keys:
                    if by_player[key] and len(selected)<max_pairs_per_event:
                        selected.append(by_player[key].pop(0))
        for pair in selected:published.extend((pair["More"],pair["Less"]))
        per_event.append({"game":game,"start":event.get("start"),
                          "source_two_sided_pairs":len(pairs),
                          "published_two_sided_pairs":len(selected),
                          "source_players":len({p["More"]["player"] for p in pairs}),
                          "published_players":len({p["More"]["player"] for p in selected})})
    return {"is_live":report["is_live"],"updated_at":report["updated_at"],
            "source":"THE_ODDS_API_VERIFIED_COMPACT_PLAYER_PROPS",
            "slate_events_available":report["slate_events_available"],
            "slate_events_checked":report["slate_events_checked"],
            "slate_events_not_checked":report["slate_events_not_checked"],
            "events_covered":per_event,"picks":published,
            "compact_display_feed":True,
            "not_prizepicks":True,
            "note":"Selected verified paired prop quotes from all checked matchups. Does not represent a complete sportsbook market list."}


def main():
    if os.environ.get("SPORTS_BOT_ENABLE_PAID_ODDS") != "1":
        save_status("PAID_ODDS_POLLING_DISABLED", note="Explicit paid-provider opt-in required; authentic prior quotes preserved and may be stale.")
        print("Paid odds polling disabled; preserving prior observations.")
        return
    key = os.environ.get("ODDS_API_KEY", "").strip()
    if not key:
        save_status("MISSING_ODDS_API_KEY")
        print("ODDS_API_KEY not set; retaining old sportsbook snapshot.")
        return
    try:
        events, start_credits = request("/events", key)
        now = dt.datetime.now(dt.timezone.utc)
        # Provider event listings can include holidays many weeks away with
        # no player markets. Only spend prop-market credits on near-term NBA.
        cutoff=now+dt.timedelta(hours=48)
        upcoming = [e for e in events if now <
            dt.datetime.fromisoformat(e["commence_time"].replace("Z","+00:00")) <= cutoff]
        upcoming.sort(key=lambda e: e["commence_time"])
        if not upcoming:
            # A late-night /events call often lists no future fixtures because
            # every game has tipped. This does NOT invalidate pregame captures.
            # Do not erase the last authentic quote snapshot with an empty one.
            save_status("NO_UPCOMING_EVENTS_PRESERVED",
                        available_events=0,checked_events=0,
                        note="All provider fixtures may have tipped; old quote file preserved and must be shown as stale.")
            print("Provider has no future events: preserving prior authentic prop snapshots.",flush=True)
            return
        picks = []
        remaining = start_credits
        inspected = 0
        covered_events=[]
        # Spread limited credits across as many games as possible before
        # purchasing four markets for the first few fixtures only.
        # The event listing is free and exposes current credit balance.
        try:
            credits=int(start_credits)
        except (TypeError,ValueError):
            credits=None
        slots=min(MAX_EVENTS,len(upcoming))
        if credits is not None and credits<=MIN_REMAINING_CREDITS:
            # /events can list a full slate while prop requests are blocked
            # by our reserve. Do not call paid event endpoints, do not publish
            # empty odds as if the slate had no real lines.
            save_status("CREDITS_BELOW_RESERVE_PRESERVED",
                        available_events=len(upcoming),checked_events=0,
                        skipped_events=len(upcoming),
                        remaining_credits=credits,
                        minimum_reserved_credits=MIN_REMAINING_CREDITS,
                        reason="NO_PROP_REQUESTS_WITHIN_CREDIT_RESERVE",
                        note="No prop endpoints called; prior authentic odds feed preserved but may be stale.")
            print("ODDS PROP COVERAGE BLOCKED: provider listed",len(upcoming),
                  "upcoming events but only",credits,"credits remain;",
                  "reserve",MIN_REMAINING_CREDITS,flush=True)
            return
        if credits is None:
            selected_markets=MARKETS
        else:
            per_event=max(1,(max(0,credits-MIN_REMAINING_CREDITS))//max(1,slots))
            selected_markets=MARKETS[:min(len(MARKETS),per_event)]
        print("NBA odds coverage plan:",slots,"events;",
              len(selected_markets),"markets per event;",
              "credits remaining:",start_credits,flush=True)
        for event in upcoming[:MAX_EVENTS]:
            if remaining is not None and int(remaining) <= MIN_REMAINING_CREDITS:
                print('Stopping early to preserve Odds API credits.', flush=True)
                break
            inspected += 1
            event_rows = []
            payload, remaining = request("/events/" + urllib.parse.quote(event["id"], safe="") + "/odds", key,
                regions="us", markets=",".join(selected_markets), oddsFormat="american")
            event_rows = balanced_bookmaker_rows(
                payload.get("bookmakers", []), event, MAX_OUTCOMES_PER_EVENT)
            # Spread a fixed display cap across books while keeping each
            # Over/Under price pair intact. No additional API calls.
            picks.extend(event_rows)
            covered_events.append({"id":event["id"],
                "game":event.get("away_team","")+" @ "+event.get("home_team",""),
                "start":event.get("commence_time"),
                "two_sided_outcomes":len(event_rows),
                "markets_requested":list(selected_markets),
                "players_quoted":len({x["player"] for x in event_rows})})
        result = {"is_live": True, "updated_at": now.isoformat(timespec="minutes"),
            "slate_events_available":len(upcoming),
            "market_types_requested":list(selected_markets),
            "market_coverage_limited":len(selected_markets)<len(MARKETS),
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
        if not picks:
            stopped_for_credits=(remaining is not None and int(remaining)<=MIN_REMAINING_CREDITS)
            save_status("CREDITS_BELOW_RESERVE_PRESERVED" if stopped_for_credits and not inspected
                        else "NO_TWO_SIDED_PLAYER_PROPS_PRESERVED",
                        available_events=len(upcoming),checked_events=inspected,
                        skipped_events=len(upcoming)-inspected,
                        remaining_credits=remaining,
                        minimum_reserved_credits=MIN_REMAINING_CREDITS,
                        reason=("INSUFFICIENT_CREDITS_FOR_FULL_SLATE" if stopped_for_credits
                                else "PROVIDER_RETURNED_NO_COMPLETE_PAIRS"),
                        note="No completed real Over/Under pairs available. Last verified snapshot was not replaced.")
            print("No two-sided real player props returned; preserving prior published snapshots.",flush=True)
            return
        OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        compact=compact_for_dashboard(result)
        COMPACT.write_text(json.dumps(compact,separators=(",",":"))+"\n",encoding="utf-8")
        print("Compact dashboard:",len(compact["picks"]),"rows from",len(compact["events_covered"]),"events",flush=True)
        save_status("FETCHED_PARTIAL" if inspected<len(upcoming)
                    else "FETCHED",available_events=len(upcoming),
                    checked_events=inspected,
                    skipped_events=len(upcoming)-inspected,
                    remaining_credits=remaining,
                    minimum_reserved_credits=MIN_REMAINING_CREDITS,
                    outcome_rows=len(picks),
                    coverage=result["coverage_warning"],
                    reason="INSUFFICIENT_CREDITS_OR_EVENT_CAP" if inspected<len(upcoming)
                           else "ALL_PROVIDER_EVENTS_CHECKED")
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
