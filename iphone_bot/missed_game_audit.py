"""Explain why completed or remembered NBA games have not been graded.

Only the immutable pregame ledger establishes that a historical projection was
actually captured. Team final scores, current AI cards and archived box scores
cannot be used to invent earlier pregame selections.
"""
import json
from collections import defaultdict
from datetime import datetime,timezone
from pathlib import Path
from zoneinfo import ZoneInfo
try:
    from .paper_pick_pipeline import utc,TEAM_ABBREVIATIONS
except ImportError:
    from paper_pick_pipeline import utc,TEAM_ABBREVIATIONS

ROOT=Path(__file__).resolve().parents[1]
LEDGER=ROOT/"docs/paper_pick_ledger.json"
RESULTS=ROOT/"docs/paper_results.json"
GAMES=ROOT/"data/nba/current/current_games.json"
FINAL=ROOT/"data/nba/current/final_boxscores.json"
OUTPUT=ROOT/"docs/missed_game_audit.json"


def inspect(records,boxscores=None,now=None):
    now=utc(now or datetime.now(timezone.utc).isoformat())
    complete=boxscores or []
    games=defaultdict(list)
    for row in records:
        try:
            start=utc(row["event_start"])
            date=start.astimezone(ZoneInfo("America/New_York")).date().isoformat()
            key=(date,str(row["game"]))
            games[key].append(row)
        except (ValueError,TypeError,KeyError):continue
    by_game=defaultdict(list)
    for row in complete:
        if row.get("source") in ("NBA_CDN_FINAL","ESPN_FINAL") and row.get("final_confirmed") is not True:
            continue
        if row.get("source") not in ("NBA_CDN_FINAL","ESPN_FINAL") and not row.get("id"):continue
        day=str(row.get("date") or "")
        t=str(row.get("team") or "")
        opp=str(row.get("opponent") or "")
        by_game[(day,t,opp)].append(row)
    result=[]
    for (day,game),rows in sorted(games.items()):
        times=sorted(utc(r["event_start"]) for r in rows)
        start=times[0]
        try:
            away,home=game.split(" @ ")
            a,h=TEAM_ABBREVIATIONS.get(away),TEAM_ABBREVIATIONS.get(home)
            boxes=by_game.get((day,a,h),[])+by_game.get((day,h,a),[])
        except (ValueError,TypeError):
            boxes=[]
        unique={(str(r["player_id"]),r["market"]) for r in rows}
        settled=[r for r in rows if r.get("status")=="SETTLED"]
        pending=[r for r in rows if r.get("status")=="PENDING"]
        pregame=[r for r in rows if utc(r["captured_at"])<utc(r["event_start"])]
        age=(now-start).total_seconds()/3600
        if not pending:
            reason="FULLY_SETTLED_VERIFIED_GAME"
        elif settled:
            reason="PARTIALLY_SETTLED_MISSING_PLAYER_BOXES_OR_DNP"
        elif age<3:
            reason="GAME_TOO_RECENT_FINAL_NOT_VERIFIED"
        elif not pregame:
            reason="NO_ELIGIBLE_PRETIP_CAPTURE"
        elif boxes:
            reason="MATCHED_PLAYER_LOGS_AVAILABLE_BUT_NOT_YET_GRADED"
        else:
            reason="WAITING_FOR_VERIFIED_COMPLETED_PLAYER_BOXSCORES"
        result.append({"game_date_eastern":day,"matchup":game,
          "scheduled_start_utc":start.isoformat(),
          "bookmaker_captures":len(rows),
          "unique_player_stat_markets":len(unique),
          "pregame_captures":len(pregame),
          "settled":len(settled),"pending":len(pending),
          "pending_unique_players":len({str(r["player_id"]) for r in pending}),
          "hours_since_scheduled_tipoff":round(age,2),
          "available_player_boxscore_rows":len(boxes),
          "diagnosis":reason})
    dates=sorted({g["game_date_eastern"] for g in result})
    return {"generated_at":now.isoformat(),
      "status":"IMMUTABLE_PREGAME_COVERAGE_AND_SETTLEMENT_DIAGNOSTIC",
      "earliest_saved_game_date":dates[0] if dates else None,
      "latest_saved_game_date":dates[-1] if dates else None,
      "total_saved_bookmaker_captures":sum(x["bookmaker_captures"] for x in result),
      "unique_matchups_with_captures":len(result),
      "celtics_matchups":[g for g in result if "Boston Celtics" in g["matchup"]],
      "historical_warning":"Games missing from the immutable ledger cannot be added as pregame predictions after tipoff.",
      "matchups":result}


def main():
    p=json.loads(LEDGER.read_text())
    rows=p.get("records",[])
    boxes=[]
    for path in (GAMES,FINAL):
        if path.exists():
            try:boxes+=json.loads(path.read_text())
            except (ValueError,TypeError):pass
    report=inspect(rows,boxes)
    OUTPUT.write_text(json.dumps(report,indent=2)+"\n")
    print("SAVED PREGAME COVERAGE:",json.dumps({k:report[k] for k in
       ("earliest_saved_game_date","latest_saved_game_date",
        "total_saved_bookmaker_captures","unique_matchups_with_captures",
        "celtics_matchups")},sort_keys=True),flush=True)
    print("UNSETTLED GAMES:",json.dumps([g for g in report["matchups"]
      if g["settled"]==0 and g["pending"]],sort_keys=True),flush=True)


if __name__=="__main__":main()
