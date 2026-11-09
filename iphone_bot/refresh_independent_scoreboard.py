#!/usr/bin/env python3
"""Independent, public NBA scoreboard snapshot; no paid API or Replit required.

Snapshots are labeled as schedule/score observations, never sportsbook lines.
On an upstream failure we retain the last good snapshot rather than replacing
it with an empty one falsely marked fresh.
"""
import datetime as dt
import json
from pathlib import Path
from zoneinfo import ZoneInfo

from iphone_bot.fetch_nba_schedule import collect, read_schedule

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs/nba_scoreboard_independent.json"
EASTERN = ZoneInfo("America/New_York")

def snapshot(days, reader=read_schedule, now=None, previous=None):
    now = now or dt.datetime.now(dt.timezone.utc)
    dates = [d.isoformat() for d in days]
    try:
        report = collect(days, reader=reader)
        rows = report.get("games", [])
        if len(dates) != len(set(dates)):
            raise ValueError("Duplicate requested dates")
        if len({str(g.get("id")) for g in rows}) != len(rows):
            raise ValueError("Duplicate game identifiers")
        return {
            "generated_at": now.isoformat(),
            "status": "OBSERVED_THIRD_PARTY_SCHEDULE_AND_SCORES",
            "source": "ESPN public scoreboard (not sportsbook or player prop data)",
            "dates_eastern": dates,
            "total_games": len(rows),
            "games": rows,
            "source_records_rejected": report.get("source_records_rejected", 0),
            "is_sportsbook_feed": False,
            "is_prizepicks_feed": False,
            "error": None,
        }
    except (OSError, TimeoutError, RuntimeError, ValueError, KeyError, TypeError) as e:
        # A stale snapshot remains stale; do not update its generated_at field.
        old = dict(previous or {})
        if old.get("games") and old.get("generated_at"):
            old["status"] = "STALE_UPSTREAM_ERROR"
            old["last_attempt_at"] = now.isoformat()
            old["error"] = type(e).__name__
            return old
        return {
            "generated_at": None,
            "last_attempt_at": now.isoformat(),
            "status": "UNAVAILABLE_UPSTREAM_ERROR",
            "source": "ESPN public scoreboard (not sportsbook)",
            "dates_eastern": dates,
            "total_games": 0,
            "games": [],
            "error": type(e).__name__,
            "is_sportsbook_feed": False,
            "is_prizepicks_feed": False,
        }

def main():
    day=dt.datetime.now(EASTERN).date()
    days=[day,day+dt.timedelta(days=1)]
    previous = None
    if OUTPUT.exists():
        try:
            previous=json.loads(OUTPUT.read_text())
        except (OSError,ValueError):
            pass
    result=snapshot(days,previous=previous)
    OUTPUT.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({"status":result["status"],"total_games":result["total_games"],
                      "generated_at":result["generated_at"],"error":result.get("error")}))
    if result["status"]!="OBSERVED_THIRD_PARTY_SCHEDULE_AND_SCORES":
        raise SystemExit(1)

if __name__=="__main__":
    main()
