"""Recover the latest genuinely frozen pregame AI board from repository history.

No odds API calls, no invented predictions, no rewriting model outputs.
Recovery is strictly a dated historical *archive*, never a live sportsbook
quote or post-tip model run. This also preserves an existing suitable archive.
"""
import json
import subprocess
from datetime import datetime,timezone,timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
ARCHIVE=ROOT/"docs/ai_pregame_archive.json"
BOARD_PATH="docs/ai_comparisons.json"
ET=ZoneInfo("America/New_York")

def timestamp(s):
    d=datetime.fromisoformat(str(s).replace("Z","+00:00"))
    if d.tzinfo is None:raise ValueError("No timestamp zone")
    return d.astimezone(timezone.utc)

def choose(payloads,now):
    day=now.astimezone(ET).date()
    candidates=[]
    for board in payloads:
        if not isinstance(board,dict) or board.get("status")!="EXPERIMENTAL_NON_CALIBRATED":continue
        if board.get("verified_current_matchups") is not True:continue
        try:stamp=timestamp(board["generated_at"])
        except (KeyError,ValueError,TypeError):continue
        if stamp>now or now-stamp>timedelta(hours=36):continue
        rows=[]
        for x in board.get("comparisons",[]):
            try:
                start=timestamp(x["start"])
                if (start.astimezone(ET).date()==day and
                    stamp<start and x.get("player_id") and
                    x.get("game") and x.get("stat") and
                    isinstance(x.get("book_quotes"),list) and
                    x.get("book_quotes")):
                    rows.append(x)
            except (TypeError,KeyError,ValueError):continue
        if rows:candidates.append((stamp,rows,board))
    if not candidates:return None
    stamp,rows,board=max(candidates,key=lambda c:c[0])
    return {"status":"FROZEN_PREGAME_HISTORICAL_ARCHIVE_NOT_LIVE",
        "generated_at":now.isoformat(),"original_board_generated_at":stamp.isoformat(),
        "date_eastern":day.isoformat(),
        "source":"Past immutable GitHub revision of AI board",
        "comparisons":rows,"comparison_rows":len(rows),
        "games_with_archived_predictions":len({x["game"] for x in rows}),
        "is_live":False,"live_sportsbook_lines":False,
        "probabilities_calibrated":False,
        "note":"Pregame snapshot ONLY. Games may have started, and odds/lines are NOT current."}

def historical_boards(max_revisions=40):
    revs=subprocess.check_output(["git","log","-n",str(max_revisions),
       "--format=%H","--",BOARD_PATH],cwd=ROOT,text=True).splitlines()
    for rev in revs:
        try:
            data=subprocess.check_output(["git","show",rev+":"+BOARD_PATH],
                cwd=ROOT,text=True,stderr=subprocess.DEVNULL)
            yield json.loads(data)
        except (subprocess.CalledProcessError,json.JSONDecodeError):continue

def main():
    now=datetime.now(timezone.utc)
    existing=[]
    if ARCHIVE.exists():
        try:
            old=json.loads(ARCHIVE.read_text())
            if old.get("status")=="FROZEN_PREGAME_HISTORICAL_ARCHIVE_NOT_LIVE":
                existing.append({"status":"EXPERIMENTAL_NON_CALIBRATED",
                    "verified_current_matchups":True,
                    "generated_at":old["original_board_generated_at"],
                    "comparisons":old["comparisons"]})
        except (ValueError,KeyError):pass
    archive=choose([*existing,*historical_boards()],now)
    if archive is None:
        # Preserve old file for history, but browser will reject wrong day.
        print("No qualifying current Eastern-day pretip archived AI board")
        return
    ARCHIVE.write_text(json.dumps(archive,separators=(",",":"))+"\n")
    print("Recovered archived AI:",archive["comparison_rows"],"props across",
        archive["games_with_archived_predictions"],"games; original time:",
        archive["original_board_generated_at"])

if __name__=="__main__":main()
