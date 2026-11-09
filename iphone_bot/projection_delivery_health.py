"""Report schedule-to-projection delivery coverage without inventing game props.

Independent pretip AI estimates and posted lines have different provenance.
Started games use preserved original forecasts. Missing games are surfaced,
not silently marked as successfully delivered.
"""
import json
from datetime import datetime,timezone,timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
SCHEDULE=ROOT/"docs/nba_schedule.json"
LIVE=ROOT/"docs/ai_projection_fallback.json"
ARCHIVE=ROOT/"docs/ai_no_line_pregame_archive.json"
OUT=ROOT/"docs/projection_delivery_health.json"
ET=ZoneInfo("America/New_York")
def parsed(s):
    try:
        d=datetime.fromisoformat(str(s).replace("Z","+00:00"))
        return d.astimezone(timezone.utc) if d.tzinfo else None
    except (TypeError,ValueError):return None

def report(schedule,live,archive,now=None):
    now=now or datetime.now(timezone.utc)
    entries=[]
    for name,source in (("upcoming_model",live),("immutable_pretip_archive",archive)):
        allowed=("PREGAME_PROJECTIONS_NO_LINES" if name=="upcoming_model"
                 else "IMMUTABLE_OBSERVED_PRETIP_NOLINE_AI_ARCHIVE")
        if source.get("status")!=allowed:continue
        timestamp=source.get("generated_at")
        for p in source.get("predictions",[]):
            start=parsed(p.get("start"))
            captured=parsed(p.get("captured_at") or timestamp)
            if not start or not captured or captured>=start or captured>now:continue
            if p.get("is_pregame_prediction") is not True or p.get("stat") not in ("PTS","REB","AST","PRA"):
                continue
            if p.get("line") is not None or p.get("direction") is not None:continue
            entries.append((str(p.get("game")),start,p.get("player_id"),p.get("stat"),name))
    checks=[]
    for game in schedule.get("games",[]):
        tip=parsed(game.get("start"))
        if not tip or not now-timedelta(hours=7)<=tip<=now+timedelta(hours=36):continue
        label=game.get("game")
        if not label:continue
        rows={(pid,stat) for g,start,pid,stat,src in entries
              if g==label and abs((start-tip).total_seconds())<=30*60}
        archived={(pid,stat) for g,start,pid,stat,src in entries
                  if g==label and src=="immutable_pretip_archive"
                  and abs((start-tip).total_seconds())<=30*60}
        state=("started" if tip<=now else "upcoming")
        checks.append({"game":label,"start":tip.isoformat(),"state":state,
                       "independent_ai_player_stats":len(rows),
                       "preserved_pretip_player_stats":len(archived),
                       "status":"AI_PREGAME_CAPTURE_PRESENT" if rows else "MISSING_AI_FORECAST"})
    missing=[g["game"] for g in checks if g["status"]=="MISSING_AI_FORECAST"]
    return {"status":"PROJECTION_COVERAGE_GAPS" if missing else
            "ALL_LISTED_GAMES_HAVE_PREGAME_AI" if checks else "NO_ACTIVE_FIXTURES_TO_CHECK",
            "generated_at":now.isoformat(),
            "schedule_source":schedule.get("source"),
            "schedule_coverage_complete":schedule.get("coverage_complete") is True,
            "listed_games_checked":len(checks),
            "missing_ai_games":missing,
            "games":checks,
            "note":"Coverage of independently generated, original pretip AI estimates, not PrizePicks offers, hit rates or live score availability."}

def main():
    schedule=json.loads(SCHEDULE.read_text()) if SCHEDULE.exists() else {}
    current=json.loads(LIVE.read_text()) if LIVE.exists() else {}
    saved=json.loads(ARCHIVE.read_text()) if ARCHIVE.exists() else {}
    result=report(schedule,current,saved)
    OUT.write_text(json.dumps(result,indent=2)+"\n")
    print("PROJECTION DELIVERY:",result["status"],"games checked",
          result["listed_games_checked"],"missing",result["missing_ai_games"],flush=True)

if __name__=="__main__":main()
