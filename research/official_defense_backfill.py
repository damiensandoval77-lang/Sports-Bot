"""Bounded official NBA final-box backfill for opponent research, NOT betting grades.

Uses a saved full-season fixture solely as ID/date/team discovery, the official
NBA league schedule to recover NBA IDs, and the final CDN box itself to prove
status, date and matchup. Does not trust a fixture as proof of a final game.
Research artifact only: no pushes, no original-ledger edits, no odds API calls.
"""
import argparse
import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from iphone_bot.fetch_final_boxscores import (
    NBA_SCHEDULE, NBA_SCHEDULE_ALT, request_json, verified_schedule_ids,
    final_schedule_boxscore, team, local_date
)
from iphone_bot.verified_final_cache import merge_rows
from research.verified_team_defense_context import final_games

MAX_GAMES = 90
MAX_LOOKBACK_DAYS = 25

def planned_games(schedule, now, limit=MAX_GAMES, lookback_days=MAX_LOOKBACK_DAYS):
    if (schedule.get("status") != "VERIFIED_PUBLISHED_NBA_2026_27_SEASON_BASELINE"
        or schedule.get("season") != "2026-27"
        or not schedule.get("source_url")):
        raise ValueError("no verified season schedule")
    if not 1 <= limit <= MAX_GAMES or not 1 <= lookback_days <= MAX_LOOKBACK_DAYS:
        raise ValueError("invalid query budget")
    if datetime.fromisoformat(schedule["generated_at"].replace("Z","+00:00")) > now:
        raise ValueError("schedule published after capture")
    cutoff = now - timedelta(days=lookback_days)
    matched=[]
    seen=set()
    for g in schedule.get("games",[]):
        try:
            tip = datetime.fromisoformat(g["start"].replace("Z","+00:00"))
            away,home=team(g["away_abbreviation"]),team(g["home_abbreviation"])
            day = local_date(g["start"])
            key=(day,away,home)
            if not away or not home or away==home or g["date_eastern"]!=day:
                continue
            if not cutoff <= tip < now-timedelta(hours=2):
                continue
            if key in seen:
                raise ValueError("ambiguous fixture")
            seen.add(key)
            matched.append((tip,key))
        except (TypeError, KeyError, ValueError) as err:
            if str(err)=="ambiguous fixture":
                raise
            continue
    return [key for _,key in sorted(matched,reverse=True)[:limit]]

def collect(season, existing_cache, *, now, request=request_json, limit=MAX_GAMES):
    targets=planned_games(season,now,limit)
    official={}
    schedule_error=None
    for url in (NBA_SCHEDULE,NBA_SCHEDULE_ALT):
        try:
            official=verified_schedule_ids(request(url),set(targets))
            if official:break
        except (OSError,ValueError,KeyError,TypeError) as err:
            schedule_error=type(err).__name__
    if not official:
        return {"status":"OFFICIAL_SCHEDULE_UNAVAILABLE","requested_games":len(targets),
                "verified_new_games":0,"rows":[],
                "production_approved":False,"schedule_error":schedule_error}
    retrieved=[]
    errors=Counter()
    for key in targets:
        gid=official.get(key)
        if not gid:
            errors["official_game_id_not_found"]+=1
            continue
        try:
            rows=final_schedule_boxscore(gid,key,request)
            if not rows:
                errors["official_final_unavailable"]+=1
                continue
            # Reject a partial box even if NBA status says final.
            teams={key[1],key[2]}
            if {r["team"] for r in rows}!=teams or any(
                sum(r["team"]==t and not r.get("dnp_final_verified") for r in rows)<7
                for t in teams):
                errors["partial_official_final_box"]+=1
                continue
            retrieved.extend(rows)
        except (ValueError,TypeError,KeyError,OSError) as err:
            errors["bad_verified_final_"+type(err).__name__]+=1
    prior=existing_cache.get("rows",[]) if existing_cache.get("version")==1 else []
    merged=merge_rows(prior,retrieved)
    # Keep only matched official NBA CDN finals; no ESPN source assumed equal.
    accepted={r["source_game_id"] for r in retrieved if r.get("source")=="NBA_CDN_FINAL"}
    confirmed,_=final_games({"version":1,"rows":merged})
    valid={g["id"] for g in confirmed}
    # Whole-game consistency gate: drop any new event that failed final_games().
    valid_new=accepted & valid
    merged=[r for r in merged if r["source_game_id"] not in accepted or
            r["source_game_id"] in valid_new]
    return {"version":1,"status":"RESEARCH_OFFICIAL_NBA_FINAL_BOX_BACKFILL",
            "captured_at":now.isoformat(),"source":"NBA_CDN_FINAL",
            "season_schedule_source":season["source_url"],
            "requested_games":len(targets),
            "official_ids_found":len(official),
            "verified_new_games":len(valid_new),
            "verified_combined_games":len(final_games({"version":1,"rows":merged})[0]),
            "failures":dict(sorted(errors.items())),
            "rows":merged,
            "production_approved":False,
            "retroactive_pregame_feature_claims":False,
            "note":"Official final observations captured now. Never claim availability at historical pick capture; does not change grading, sportsbook lines, model outputs or live odds."}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--schedule",default="docs/nba_season_schedule_2026_27.json")
    p.add_argument("--prior",default="docs/verified_final_player_cache.json")
    p.add_argument("--output",default="official-defense-history-research.json")
    p.add_argument("--limit",type=int,default=MAX_GAMES)
    a=p.parse_args()
    now=datetime.now(timezone.utc)
    result=collect(json.loads(Path(a.schedule).read_text()),
                   json.loads(Path(a.prior).read_text()),now=now,limit=a.limit)
    Path(a.output).write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps({k:result.get(k) for k in (
        "status","requested_games","official_ids_found","verified_new_games",
        "verified_combined_games","failures","production_approved")},indent=2))

if __name__=="__main__":main()
