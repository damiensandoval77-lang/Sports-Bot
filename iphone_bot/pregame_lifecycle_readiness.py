"""Independent pregame readiness audit with strict source provenance.

No paid feeds; reads only persisted repository snapshots. Does not imply
missing provider markets are nonexistent, and never fabricates a line.
"""
import datetime as dt
import json
import sys
from collections import Counter
from pathlib import Path
from zoneinfo import ZoneInfo

from iphone_bot.archive_prizepicks_pregame_lines import safe_row, moment
from iphone_bot.grade_frozen_ai_forecasts import key, utc

ROOT=Path(__file__).resolve().parents[1]
ET=ZoneInfo("America/New_York")
SCHEDULE=ROOT/"docs/nba_schedule.json"
QUOTES=ROOT/"docs/prizepicks_pregame_line_archive.json"
FORECASTS=ROOT/"docs/ai_no_line_pregame_archive.json"
OUTPUT=ROOT/"docs/pregame_lifecycle_readiness.json"

def audit(schedule,archive,forecasts,now=None):
    now=now or dt.datetime.now(dt.timezone.utc)
    today=now.astimezone(ET).date().isoformat()
    output={"generated_at":now.isoformat(),"status":"NOT_READY",
        "target_date_eastern":None,"games":[],"counts":{},
        "issues":[],"scope":"NEXT_FUTURE_NBA_SLATE",
        "real_sportsbook_lines_are_not_guaranteed":True,
        "is_a_simulated_outcome":False}
    if schedule.get("status")!="THIRD_PARTY_NBA_SCHEDULE_ONLY" or schedule.get("coverage_complete") is not True:
        output["issues"].append("OFFICIAL_SCHEDULE_NOT_CONFIRMED_COMPLETE")
    entries=[g for g in schedule.get("games",[]) if isinstance(g,dict) and
             g.get("date_eastern") and g.get("game") and moment(g.get("start"))]
    dates=sorted({g["date_eastern"] for g in entries if moment(g["start"])>now})
    next_days=[x for x in dates if x>today]
    target=next_days[0] if next_days else (dates[0] if dates else None)
    output["target_date_eastern"]=target
    if not target:
        output["issues"].append("NO_UPCOMING_SCHEDULED_GAMES")
        return output
    scheduled=[g for g in entries if g["date_eastern"]==target and moment(g["start"])>now]
    if not scheduled:
        output["issues"].append("NO_UNSTARTED_GAMES_ON_TARGET_DATE")
    if len({g["game"] for g in scheduled})!=len(scheduled):
        output["issues"].append("DUPLICATE_SCHEDULED_GAME_IDENTITY")
    source_valid=archive.get("status")=="VERIFIED_PRETIP_PRIZEPICKS_QUOTES_ARCHIVE"
    preds_valid=forecasts.get("status")=="IMMUTABLE_OBSERVED_PRETIP_NOLINE_AI_ARCHIVE"
    if not source_valid:output["issues"].append("SOURCE_ARCHIVE_STATUS_INVALID")
    if not preds_valid:output["issues"].append("MODEL_ARCHIVE_STATUS_INVALID")
    valid_quotes=[q for q in (archive.get("quotes") or [])
                  if source_valid and safe_row(q)]
    valid_predictions=[p for p in (forecasts.get("predictions") or []) if
                       preds_valid and isinstance(p,dict) and
                       p.get("is_pregame_prediction") is True and
                       p.get("line") is None and p.get("player") and p.get("team") and
                       p.get("stat") in ("PTS","REB","AST","PRA") and
                       utc(p.get("captured_at")) and utc(p.get("start")) and
                       utc(p["captured_at"])<utc(p["start"])]
    for g in scheduled:
        quote=[x for x in valid_quotes if x.get("game")==g["game"] and
               abs((moment(x["starts_at"])-moment(g["start"])).total_seconds())<=1800]
        predicted=[x for x in valid_predictions if x.get("game")==g["game"] and
                   abs((utc(x["start"])-moment(g["start"])).total_seconds())<=1800]
        market_ids={(q["player"],q["team"],q["stat"]) for q in quote}
        models={(p["player"],p["team"],p["stat"]) for p in predicted}
        row={"game":g["game"],"start":g["start"],
             "captured_line_markets":len(market_ids),"captured_ai_forecasts":len(models),
             "status":("LINES_AND_AI" if market_ids and models else
                       "ONLY_LINES" if market_ids else "ONLY_AI" if models else "MISSING_BOTH")}
        output["games"].append(row)
    tally=Counter(x["status"] for x in output["games"])
    output["counts"]={"scheduled":len(scheduled),
                     "games_with_saved_quotes":sum(x["captured_line_markets"]>0 for x in output["games"]),
                     "games_with_saved_ai":sum(x["captured_ai_forecasts"]>0 for x in output["games"]),
                     "saved_line_markets":sum(x["captured_line_markets"] for x in output["games"]),
                     "saved_ai_forecasts":sum(x["captured_ai_forecasts"] for x in output["games"]),
                     "coverage":dict(tally)}
    if output["counts"]["games_with_saved_quotes"]<len(scheduled):
        output["issues"].append("SOME_SCHEDULED_GAMES_WITHOUT_SAVED_VERIFIED_LINES")
    if output["counts"]["games_with_saved_ai"]<len(scheduled):
        output["issues"].append("SOME_SCHEDULED_GAMES_WITHOUT_SAVED_AI_FORECASTS")
    # At very early pregame dates the provider can correctly have no published
    # markets; this is NOT a valid reason to claim readiness.
    output["status"]="READY" if not output["issues"] else "NOT_READY"
    output["note"]="Source coverage for the next scheduled NBA date, not a guarantee every player has a priced market. Missing quotes may reflect provider gaps or pre-publication."
    return output

def main():
    try:
        objects=[json.loads(x.read_text()) for x in (SCHEDULE,QUOTES,FORECASTS)]
        result=audit(*objects)
    except (OSError,ValueError,TypeError) as e:
        result={"generated_at":dt.datetime.now(dt.timezone.utc).isoformat(),
                "status":"NOT_READY","issues":["READINESS_INPUT_UNAVAILABLE",type(e).__name__]}
    OUTPUT.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n")
    print("NEXT NBA SLATE PREFLIGHT:",json.dumps(result))
    return 0 if result["status"]=="READY" else 1

if __name__=="__main__":sys.exit(main())
