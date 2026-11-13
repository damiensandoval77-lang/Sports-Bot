"""Keep the newest verified NBA scoreboard when multiple GitHub Actions publish.

Never overwrite a newer live observation with an older schedule fallback or
stale provider error. No network requests, odds calls, or inferred scores.
"""
import json
import sys
from datetime import datetime,timezone
from pathlib import Path

LIVE={"OBSERVED_NBA_LIVE_SCOREBOARD","OBSERVED_THIRD_PARTY_SCHEDULE_AND_SCORES"}
def stamp(data):
    try:
        raw=data.get("generated_at")
        if not raw:return None
        t=datetime.fromisoformat(str(raw).replace("Z","+00:00"))
        return t.astimezone(timezone.utc) if t.tzinfo else None
    except (ValueError,TypeError):
        return None

def select(current,candidate):
    if not isinstance(candidate,dict) or not candidate.get("games"):
        return current if isinstance(current,dict) else candidate
    if not isinstance(current,dict) or not current.get("games"):
        return candidate
    curdate=set(current.get("dates_eastern") or [])
    newdate=set(candidate.get("dates_eastern") or [])
    # New Eastern day supersedes yesterday's older observations.
    if curdate!=newdate and curdate and newdate:
        if max(newdate)>max(curdate):return candidate
        if max(curdate)>max(newdate):return current
    # Never replace verified source observations with an error or a
    # schedule-only fallback, even if the fallback has a later attempt time.
    # A later fresh observation can supersede an earlier one on the same day.
    if current.get("status") in LIVE and candidate.get("status") not in LIVE:
        return current
    if candidate.get("status") in LIVE and current.get("status") not in LIVE:
        return candidate
    a=stamp(current);b=stamp(candidate)
    if a and b:
        if b<a:return current
        if b>a:return candidate
    elif a and not b:return current
    elif b and not a:return candidate
    return current

def main():
    if len(sys.argv)!=3:raise SystemExit("usage: module TARGET CANDIDATE")
    target=Path(sys.argv[1]);source=Path(sys.argv[2])
    try:
        a=json.loads(target.read_text()) if target.exists() else {}
        b=json.loads(source.read_text())
        selected=select(a,b)
        if selected is b:
            target.write_text(json.dumps(b,indent=2)+"\n")
            print("Applied newer NBA scoreboard observation")
        else:
            print("Retained latest existing NBA scoreboard observation")
    except (ValueError,OSError) as e:
        raise SystemExit("Scoreboard safety merge failed: "+type(e).__name__)

if __name__=="__main__":
    main()
