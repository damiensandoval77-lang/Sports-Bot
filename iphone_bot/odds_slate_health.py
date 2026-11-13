"""No-network truth table for NBA slate -> odds provider -> priced props.

Counts independently scheduled games, not just the provider's event list.
Absence from a public schedule/odds feed is not proof a bookmaker has no lines.
All status counters reflect published, timestamped evidence only.
"""
import datetime as dt
import json
from collections import Counter
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"docs/odds_slate_health.json"
EASTERN=ZoneInfo("America/New_York")
FRESH_HOURS=6
QUOTA_STATES={"CREDITS_BELOW_RESERVE_PRESERVED","LEGACY_ZERO_EVENT_FETCH_CREDIT_RESERVE"}

def utc(raw):
    d=dt.datetime.fromisoformat(str(raw).replace("Z","+00:00"))
    if d.tzinfo is None:raise ValueError("naive date")
    return d.astimezone(dt.timezone.utc)

def game_key(game):
    # No fuzzy player/team assumptions, only presentation spelling.
    value=" ".join(str(game or "").casefold().split())
    return value.replace("la clippers","los angeles clippers")

def report(schedule,odds,status,archive=None,now=None):
    now=now or dt.datetime.now(dt.timezone.utc)
    today=now.astimezone(EASTERN).date().isoformat()
    if not isinstance(schedule,dict):schedule={}
    if not isinstance(odds,dict):odds={}
    if not isinstance(status,dict):status={}
    status_name=str(status.get("status") or "UNKNOWN")
    details=status.get("details") if isinstance(status.get("details"),dict) else {}
    # Legacy bug: older runs published status=FETCHED even when no event
    # endpoints were queried because only <=12 credits remained.
    # Infer a diagnostic from historical *published* metadata, without
    # rewriting the historical provider response or spending API credits.
    try:
        remaining=int(details.get("remaining_credits"))
        checked=int(details.get("checked_events"))
        listed=int(details.get("available_events"))
        reserve=int(details.get("minimum_reserved_credits") or 12)
    except (ValueError,TypeError):
        remaining=checked=listed=reserve=None
    if (status_name=="FETCHED" and remaining is not None and
        checked==0 and listed is not None and listed>0 and
        remaining<=reserve):
        status_name="LEGACY_ZERO_EVENT_FETCH_CREDIT_RESERVE"
    if status_name=="LEGACY_ZERO_EVENT_FETCH_CREDIT_RESERVE":
        details={**details,"minimum_reserved_credits":reserve}
    try:
        stamp=utc(odds.get("updated_at"))
        feed_fresh=now>=stamp and now-stamp<=dt.timedelta(hours=FRESH_HOURS)
    except (ValueError,TypeError):feed_fresh=False
    active_pairs=set()
    if feed_fresh:
        # Real paired More/Less only, never a single-sided or unpriced market.
        grouped={}
        for p in odds.get("picks",[]):
            if not isinstance(p,dict):continue
            try:
                if utc(p.get("start"))<=now:continue
                if not p.get("game") or not p.get("player") or not p.get("stat"):continue
                k=(game_key(p["game"]),str(p["player"]).casefold(),str(p["stat"]),
                   str(p.get("line")),str(p.get("source")))
                if p.get("direction") in ("More","Less"):
                    grouped.setdefault(k,set()).add(p["direction"])
            except (ValueError,TypeError):continue
        active_pairs={x[0] for x,v in grouped.items() if v=={"More","Less"}}
    provider_checked=set()
    if feed_fresh:
        provider_checked={game_key(x.get("game")) for x in odds.get("events_covered",[])
                          if isinstance(x,dict) and x.get("game")}
    archive_games=set()
    if isinstance(archive,dict) and archive.get("status")=="FROZEN_PREGAME_HISTORICAL_ARCHIVE_NOT_LIVE" and archive.get("date_eastern")==today:
        archive_games={game_key(x.get("game")) for x in archive.get("comparisons",[])
                       if isinstance(x,dict) and x.get("game")}
    all_today=[];seen=set()
    for x in schedule.get("games",[]):
        if not isinstance(x,dict) or x.get("date_eastern")!=today:continue
        key=game_key(x.get("game"))
        if not key or key in seen:continue
        try:start=utc(x.get("start"))
        except (ValueError,TypeError):continue
        seen.add(key)
        if start<=now:
            state="STARTED_OR_FINISHED_NO_NEW_PREGAME_MARKET"
        elif key in active_pairs:
            state="FRESH_VERIFIED_PAIRED_PROPS"
        elif status_name in QUOTA_STATES:
            state="ODDS_CREDIT_RESERVE_BLOCKED"
        elif not feed_fresh:
            state="STALE_OR_MISSING_ODDS_SNAPSHOT"
        elif key in provider_checked:
            state="NO_PAIRED_PROPS_IN_LAST_PROVIDER_SNAPSHOT"
        else:
            state="NOT_CHECKED_OR_ABSENT_FROM_PROVIDER_FEED"
        all_today.append({"game":x["game"],"start":start.isoformat(),
            "game_state":x.get("game_state"),"coverage":state,
            "has_historical_pregame_ai":key in archive_games,
            "live_betting_lines_verified":state=="FRESH_VERIFIED_PAIRED_PROPS"})
    counts=dict(Counter(x["coverage"] for x in all_today))
    upcoming=[x for x in all_today if x["coverage"]!="STARTED_OR_FINISHED_NO_NEW_PREGAME_MARKET"]
    return {"status":"DESCRIPTIVE_NBA_SLATE_ODDS_COVERAGE",
       "generated_at":now.isoformat(),"date_eastern":today,
       "schedule_source":schedule.get("source"),
       "schedule_coverage_complete":schedule.get("coverage_complete") is True,
       "provider_status":status_name,
       "provider_events_reported":details.get("available_events"),
       "provider_events_checked":details.get("checked_events"),
       "remaining_provider_credits":details.get("remaining_credits"),
       "reserved_credits":details.get("minimum_reserved_credits"),
       "paired_quotes_fresh":feed_fresh,
       "scheduled_today":len(all_today),
       "upcoming_scheduled":len(upcoming),
       "upcoming_with_fresh_props":sum(x["live_betting_lines_verified"] for x in upcoming),
       "upcoming_missing_fresh_props":sum(not x["live_betting_lines_verified"] for x in upcoming),
       "by_coverage":counts,
       "games":all_today,
       "historical_ai_is_not_live":True,
       "no_new_provider_requests_made":True,
       "limitation":"Incomplete schedules and provider listings do not prove an event has no bookmaker props. Stale quotes are not current."}

def load(path):
    try:return json.loads(path.read_text())
    except (FileNotFoundError,ValueError):return {}

def main():
    result=report(load(ROOT/"docs/nba_schedule.json"),load(ROOT/"docs/odds_compact.json"),
                  load(ROOT/"docs/odds_fetch_status.json"),
                  load(ROOT/"docs/ai_pregame_archive.json"))
    OUT.write_text(json.dumps(result,indent=2)+"\n")
    print("NBA slate/odds health:",json.dumps({k:result[k] for k in (
        "scheduled_today","upcoming_scheduled","upcoming_with_fresh_props",
        "upcoming_missing_fresh_props","remaining_provider_credits",
        "reserved_credits","provider_status")},sort_keys=True))

if __name__=="__main__":main()
