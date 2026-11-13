"""Grade immutable pre-tip AI-only projections against VERIFIED final player boxes.

Separate from PrizePicks and sportsbook settlement. Measures forecast errors,
never calculates bet hit rates/ROI without a pre-tip market line. Do not re-run
models after games. Historical grades persist even if the 48-hour archive rolls.
"""
import datetime as dt
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean
from zoneinfo import ZoneInfo

from iphone_bot.official_game_id_index import recovery_game_ids
from iphone_bot.archived_espn_game_ids import archived_espn_hints,combine_espn_hints
from iphone_bot.fetch_final_boxscores import gather, verified_espn_schedule_hints
from iphone_bot.verified_final_cache import read_cache, write_cache, row_key
from iphone_bot.paper_pick_pipeline import TEAM_ABBREVIATIONS, expected_opponents, strict_player_name
from iphone_bot.prizepicks_research_ledger import utc
from iphone_bot.recover_prizepicks_final_games import multi_origin_request
from iphone_bot.verified_prizepicks_inactives import verified_inactive_subset, additional_verified_ai_inactive_subset
from iphone_bot.verified_boxscore_dnps import verified_boxscore_dnp_subset, SOURCE as BOXSCORE_DNP_SOURCE
from iphone_bot.verified_nba_official_dnps import load_official_dnp
from iphone_bot.verified_nov9_nonparticipants import load_nonparticipants
from iphone_bot.verified_gamebook_inactives import load_gamebook_inactives
from iphone_bot.verified_pretip_trade import verified_trade_subset, SOURCE as TRADE_SOURCE

ROOT=Path(__file__).resolve().parents[1]
ARCHIVE=ROOT/"docs/ai_no_line_pregame_archive.json"
LEDGER=ROOT/"docs/ai_forecast_actual_ledger.json"
STATUS=ROOT/"docs/ai_forecast_grade_status.json"
CURRENT_STATUS=ROOT/"docs/ai_forecast_today_grade_status.json"
FINAL_CACHE=ROOT/"docs/verified_final_player_cache.json"
ET=ZoneInfo("America/New_York")
STATS=("PTS","REB","AST","PRA")
APPROVED_SOURCES={"NBA_CDN_FINAL","ESPN_FINAL"}

def eastern_day(stamp):
    moment=utc(stamp)
    return moment.astimezone(ET).date().isoformat() if moment else None

def key(p):
    return "|".join(str(p.get(k,"")) for k in ("player_id","team","game","start","stat"))

def eligible_predictions(predictions,now=None,days_back=3):
    now=now or dt.datetime.now(dt.timezone.utc)
    floor=now.astimezone(ET).date()-dt.timedelta(days=days_back)
    result={}
    for p in predictions:
        if p.get("is_pregame_prediction") is not True or p.get("line") is not None:
            continue
        start=utc(p.get("start"));locked=utc(p.get("captured_at"))
        if not start or not locked or locked>=start or now<=start:
            continue
        if start.astimezone(ET).date()<floor:
            continue
        stat=p.get("stat")
        if stat not in STATS or not p.get("player_id") or not p.get("player") or not p.get("team"):
            continue
        opponents=expected_opponents(p.get("game"),p.get("team"))
        if len(opponents)!=1:
            continue
        try:
            projection=float(p.get("projection"))
        except (ValueError,TypeError):
            continue
        if not math.isfinite(projection) or projection<0 or projection>250:
            continue
        ident=key(p)
        if ident in result:
            # Conflicting captures are not silently resolved by newest or most favorable value.
            if result[ident]!=p:
                result[ident]=None
        else:
            result[ident]=p
    return [p for p in result.values() if p is not None]

def final_requests(predictions):
    requests={}
    for p in predictions:
        start=utc(p["start"])
        day=start.astimezone(ET).date().isoformat()
        pair=(day,p["game"])
        requests.setdefault(pair,{"event_start":p["start"],"status":"PENDING",
                                  "game":p["game"],"team":p["team"],
                                  "player_id":str(p["player_id"])})
    return list(requests.values())

def settle_predictions(predictions,final_rows,existing=None,confirmed_inactives=None,confirmed_transfers=None):
    """No missing player or unverified DNP is ever a zero-stat observation."""
    retained={key(r):dict(r) for r in (existing or []) if r.get("status") in ("GRADED","EXCLUDED_VERIFIED_DNP","EXCLUDED_VERIFIED_NONPARTICIPANT")}
    by_name=defaultdict(list)
    for row in final_rows:
        if (row.get("final_confirmed") is not True or
            row.get("source") not in APPROVED_SOURCES or
            row.get("dnp_final_verified") is True or
            not row.get("source_game_id")):
            continue
        n=strict_player_name(row.get("player"))
        if not n:continue
        ident=(n,row.get("team"),row.get("date"),row.get("opponent"))
        by_name[ident].append(row)
    dnp_by_name=defaultdict(list)
    for row in list(final_rows)+list(confirmed_inactives or []):
        if (row.get("final_confirmed") is not True or
            row.get("dnp_final_verified") is not True or
            row.get("source") not in APPROVED_SOURCES|{"NBA_OFFICIAL_INACTIVE_CROSSCHECKED",BOXSCORE_DNP_SOURCE} or
            not row.get("source_game_id") or not row.get("dnp_reason")):
            continue
        n=strict_player_name(row.get("player"))
        if n:
            dnp_by_name[(n,row.get("team"),row.get("date"),row.get("opponent"))].append(row)
    transferred={
        (strict_player_name(r.get("player")),r.get("team"),r.get("date"),r.get("opponent")):r
        for r in (confirmed_transfers or [])
        if r.get("source")==TRADE_SOURCE and r.get("nonparticipant_final_verified") is True
        and r.get("final_confirmed") is True and r.get("source_game_id")
    }
    new_transfers=0
    new_exclusions=0
    new_grades=0
    for p in predictions:
        ident=key(p)
        if ident in retained:continue
        day=eastern_day(p["start"])
        opponents=expected_opponents(p["game"],p["team"])
        if len(opponents)!=1:continue
        candidates=by_name.get((strict_player_name(p["player"]),p["team"],day,opponents[0]),[])
        # Exact confirmed nonparticipant excludes forecast error, never a zero-stat game.
        # Conflicting played/DNP identities remain unresolved.
        match=(strict_player_name(p["player"]),p["team"],day,opponents[0])
        inactive=dnp_by_name.get(match,[])
        transfer=transferred.get(match)
        if transfer and not candidates and not inactive:
            retained[ident]={
                "status":"EXCLUDED_VERIFIED_NONPARTICIPANT",
                "player_id":str(p["player_id"]),"player":p["player"],
                "team":p["team"],"game":p["game"],"start":p["start"],
                "stat":p["stat"],"captured_at":p["captured_at"],
                "projection":float(p["projection"]),"actual":None,
                "error":None,"absolute_error":None,"minutes":None,
                "final_source":transfer["source"],
                "source_game_id":str(transfer["source_game_id"]),
                "verified_nonparticipation_reason":transfer["reason"],
                "line":None,"betting_grade":None
            }
            new_transfers+=1
            continue
        if not candidates and len(inactive)==1:
            dnp=inactive[0]
            retained[ident]={
                "status":"EXCLUDED_VERIFIED_DNP",
                "player_id":str(p["player_id"]),"player":p["player"],
                "team":p["team"],"game":p["game"],"start":p["start"],
                "stat":p["stat"],"captured_at":p["captured_at"],
                "projection":float(p["projection"]),"actual":None,
                "error":None,"absolute_error":None,"minutes":None,
                "final_source":dnp["source"],
                "source_game_id":str(dnp["source_game_id"]),
                "verified_dnp_reason":dnp["dnp_reason"],
                "line":None,"betting_grade":None
            }
            new_exclusions+=1
            continue
        if len(candidates)!=1 or inactive:continue
        actual_row=candidates[0]
        try:
            actual=float(actual_row[p["stat"]]); projection=float(p["projection"])
            minutes=float(actual_row["MIN"])
        except (TypeError,ValueError,KeyError):
            continue
        if not all(math.isfinite(v) for v in (actual,projection,minutes)):
            continue
        if not (0<=actual<=250 and 0<minutes<=60):
            continue
        retained[ident]={
            "status":"GRADED", "player_id":str(p["player_id"]),
            "player":p["player"],"team":p["team"],"game":p["game"],
            "start":p["start"],"stat":p["stat"],
            "captured_at":p["captured_at"],"projection":projection,
            "actual":actual,"error":round(projection-actual,5),
            "absolute_error":round(abs(projection-actual),5),
            "final_source":actual_row["source"],
            "source_game_id":str(actual_row["source_game_id"]),
            "minutes":minutes,"line":None,"betting_grade":None
        }
        new_grades+=1
    return {"records":sorted(retained.values(),key=lambda x:(x["start"],x["game"],x["player"],x["stat"])),
            "new_grades":new_grades,"new_exclusions":new_exclusions,"new_transfers":new_transfers}

def unresolved_reasons(pending, final_rows):
    """Explain unresolved identities using verified final rows; never infer DNP or zero."""
    reasons = {}
    for p in pending:
        day = eastern_day(p.get("start"))
        opponents = expected_opponents(p.get("game"), p.get("team"))
        opponent = next(iter(opponents)) if len(opponents) == 1 else None
        trusted = [
            r for r in final_rows
            if r.get("final_confirmed") is True
            and r.get("source") in APPROVED_SOURCES
            and r.get("source_game_id")
            and r.get("date") == day
        ]
        matchup = [
            r for r in trusted
            if (r.get("team"), r.get("opponent")) in (
                (p.get("team"), opponent), (opponent, p.get("team")))
        ]
        same_name = [r for r in matchup
                     if strict_player_name(r.get("player")) == strict_player_name(p.get("player"))]
        exact = [r for r in same_name
                 if r.get("team") == p.get("team") and r.get("opponent") == opponent]
        if not matchup:
            reason = "VERIFIED_FINAL_MATCHUP_NOT_RETRIEVED"
        elif not same_name:
            reason = "PLAYER_NOT_IN_RETRIEVED_FINAL_ROWS_DNP_UNVERIFIED"
        elif not exact:
            reason = "PLAYER_TEAM_OPPONENT_IDENTITY_MISMATCH"
        elif len(exact) > 1:
            reason = "AMBIGUOUS_DUPLICATE_FINAL_IDENTITY"
        elif exact[0].get("dnp_final_verified"):
            reason = "INACTIVE_EVIDENCE_NOT_SETTLED"
        else:
            reason = "FINAL_PLAYER_ROW_REJECTED_OR_CONFLICTING"
        reasons[key(p)] = {
            "player": p.get("player"), "team": p.get("team"),
            "game": p.get("game"), "stat": p.get("stat"),
            "reason": reason,
        }
    return reasons

def report(day,predictions,graded,fetch_report=None,now=None,final_rows=None):
    now=now or dt.datetime.now(dt.timezone.utc)
    chosen=[p for p in predictions if eastern_day(p["start"])==day]
    resolved=[g for g in graded["records"] if eastern_day(g["start"])==day]
    records=[g for g in resolved if g.get("status")=="GRADED"]
    excluded=[g for g in resolved if g.get("status")=="EXCLUDED_VERIFIED_DNP"]
    transfers=[g for g in resolved if g.get("status")=="EXCLUDED_VERIFIED_NONPARTICIPANT"]
    by_key={key(g):g for g in resolved}
    pending=[p for p in chosen if key(p) not in by_key]
    missing_details = unresolved_reasons(pending, final_rows or []) if final_rows is not None else {}
    stat_metrics={}
    for stat in STATS:
        rows=[r for r in records if r["stat"]==stat]
        stat_metrics[stat]={
            "graded":len(rows),
            "mae":round(mean(r["absolute_error"] for r in rows),3) if rows else None,
            "mean_signed_error":round(mean(r["error"] for r in rows),3) if rows else None,
        }
    return {
        "status":("AI_PRETIP_FORECASTS_GRADED" if chosen and not pending else
                  "AI_PRETIP_FORECASTS_PARTIALLY_GRADED" if records else
                  "NO_VERIFIED_AI_FORECAST_ACTUALS"),
        "generated_at":now.isoformat(),"game_date_eastern":day,
        "recorded_pregame_forecasts":len(chosen),"graded":len(records),"verified_dnp_exclusions":len(excluded),
        "verified_pretip_transfer_exclusions":len(transfers),
        "accounted_for":len(records)+len(excluded)+len(transfers),"ungraded":len(pending),
        "new_grades":graded["new_grades"],
        "new_verified_dnp_exclusions":graded.get("new_exclusions",0),
        "new_verified_pretip_transfer_exclusions":graded.get("new_transfers",0),
        "excluded_verified_transfer_players":sorted({r["player"] for r in transfers}),
        "by_stat":stat_metrics,
        "ungraded_by_game":dict(sorted(Counter(p["game"] for p in pending).items())),
        "excluded_verified_dnp_players":sorted({r["player"] for r in excluded}),
        "ungraded_distinct_player_names_by_game":{
            game: sorted({p["player"] for p in pending if p["game"]==game})
            for game in sorted({p["game"] for p in pending})},
        "ungraded_distinct_player_markets":len({
            (p["game"],p["player_id"],p["stat"]) for p in pending}),
        "final_feed":fetch_report or {},
        "ungraded_diagnostics": {
            "by_reason": dict(sorted(Counter(x["reason"] for x in missing_details.values()).items())),
            "players": sorted(missing_details.values(),
                              key=lambda x:(x["game"],x["player"],x["stat"])),
            "source": "VERIFIED_FINAL_ROWS_ONLY_NO_DNP_INFERENCE" if final_rows is not None else "NOT_EVALUATED",
        },
        "is_betting_hit_rate":False,
        "note":"Forecast-vs-actual absolute error only; no market line or bet direction. Missing players/DNP are not assigned zero."
    }

def main():
    now=dt.datetime.now(dt.timezone.utc)
    raw=json.loads(ARCHIVE.read_text()) if ARCHIVE.exists() else {}
    archive=raw.get("predictions") or []
    selected=eligible_predictions(archive,now)
    old=json.loads(LEDGER.read_text()).get("records",[]) if LEDGER.exists() else []
    requested=final_requests(selected)
    # Each original archived player belongs to one exact scheduled game.
    # Cross-provider lookup is permitted ONLY for missing players, and only
    # explicit independently verified ESPN final DNPs can be accepted.
    secondary_dnp_requests={}
    for p in selected:
        teams=str(p.get("game") or "").split(" @ ")
        if len(teams)!=2:
            continue
        away=TEAM_ABBREVIATIONS.get(teams[0].strip())
        home=TEAM_ABBREVIATIONS.get(teams[1].strip())
        if not away or not home or away==home or p.get("team") not in (away,home):
            continue
        group=(eastern_day(p["start"]),away,home)
        secondary_dnp_requests.setdefault(group,set()).add(
            (strict_player_name(p.get("player")),p["team"]))
    if len(requested)>25:
        raise SystemExit("More than 25 final matchups; refusing incomplete grade fetch")
    if requested:
        try:
            schedule_path=ROOT/"docs/nba_schedule.json"
            try:
                schedule=json.loads(schedule_path.read_text())
                espn_hints=verified_espn_schedule_hints(schedule)
            except (OSError,ValueError,TypeError):
                espn_hints={}
            # Daily schedule rollover must not erase historical ESPN lookup
            # hints. Final evidence still comes solely from the direct
            # completed boxscore's event ID, date and team checks.
            requested_days={eastern_day(p["start"]) for p in selected}
            historical=archived_espn_hints(dates=requested_days)
            espn_hints=combine_espn_hints(espn_hints,historical)
            actuals,fetch_report=gather(requested,now=now,request=multi_origin_request,
                                      known_game_ids=recovery_game_ids(ROOT/"docs/official_nba_game_ids.json",
                                          ROOT/"docs/verified_official_final_game_ids.json"),
                                      known_espn_games=espn_hints,
                                      supplemental_espn_dnp_names=secondary_dnp_requests)
        except (OSError,ValueError,TypeError,KeyError) as e:
            actuals=[];fetch_report={"status":"FINAL_FETCH_FAILED","errors":[type(e).__name__]}
    else:
        actuals=[];fetch_report={"status":"NO_ELIGIBLE_ARCHIVED_GAMES"}
    try:
        confirmed_inactives=(verified_inactive_subset(actuals)+
                             additional_verified_ai_inactive_subset(actuals)+
                             verified_boxscore_dnp_subset(actuals)+
                             load_official_dnp(actuals)+
                             load_nonparticipants(actuals))
    except (OSError,ValueError,TypeError,KeyError):
        confirmed_inactives=[]
    cached_before=read_cache(FINAL_CACHE)
    saved=write_cache(FINAL_CACHE,cached_before,actuals)
    # Reuse only previously verified NBA/ESPN final player rows. If both
    # sources disagree on an identity, merge_rows omits that identity.
    actuals=saved
    fetch_report["verified_cache_rows"]=len(saved)
    fetch_report["newly_retrieved_verified_rows"]=len([
        row for row in saved if row_key(row) not in {row_key(x) for x in cached_before}
    ])
    fetch_report["cache_recovery_used"]=bool(cached_before)
    try:
        # Recreate every verified exclusion from the final confirmed/cached rows.
        # Do not discard explicit boxscore DNP evidence after cache reconciliation.
        confirmed_inactives=(verified_inactive_subset(actuals)+
                             additional_verified_ai_inactive_subset(actuals)+
                             verified_boxscore_dnp_subset(actuals)+
                             load_official_dnp(actuals)+
                             load_nonparticipants(actuals))
    except (OSError,ValueError,TypeError,KeyError):
        confirmed_inactives=[]
    confirmed_inactives.extend(load_gamebook_inactives(actuals + confirmed_inactives))
    try:
        confirmed_transfers=verified_trade_subset(actuals)
    except (OSError,ValueError,TypeError,KeyError):
        confirmed_transfers=[]
    graded=settle_predictions(selected,actuals,old,confirmed_inactives=confirmed_inactives,
                              confirmed_transfers=confirmed_transfers)
    LEDGER.write_text(json.dumps({"version":1,"records":graded["records"]},indent=2)+"\n")
    day=(now.astimezone(ET).date()-dt.timedelta(days=1)).isoformat()
    status=report(day,selected,graded,fetch_report,now,final_rows=actuals)
    STATUS.write_text(json.dumps(status,indent=2)+"\n")
    # Expose today's verified grades while games are still in progress.
    # Never infer final results from live scores or simulated performance.
    current_day=now.astimezone(ET).date().isoformat()
    current_report=report(current_day,selected,graded,fetch_report,now,final_rows=actuals)
    current_report["is_current_day_live_grade_status"]=True
    current_report["final_only_no_live_wins"]=True
    CURRENT_STATUS.write_text(json.dumps(current_report,indent=2)+"\n")
    print("AI NO-LINE GRADE:",json.dumps({
        k:status[k] for k in ("game_date_eastern","status","recorded_pregame_forecasts",
                           "graded","ungraded","new_grades")},sort_keys=True))

if __name__=="__main__":
    main()
