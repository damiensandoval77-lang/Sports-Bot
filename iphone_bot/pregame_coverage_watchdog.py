"""Read-only per-game pretip delivery and freeze coverage watchdog.

Uses saved GitHub artifacts, never calls paid provider APIs. Forecasts and
posted lines are independently checked; a partial provider board is not
misreported as proof that absent player markets do not exist.
"""
import datetime as dt
import json
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
ET=ZoneInfo("America/New_York")
UTC=dt.timezone.utc

def parsed(value):
    try:
        t=dt.datetime.fromisoformat(str(value).replace("Z","+00:00"))
        return t.astimezone(UTC) if t.tzinfo else None
    except (ValueError,TypeError,OverflowError):
        return None

def check(now,schedule,forecast,archive,quick):
    if now.tzinfo is None:
        raise ValueError("Aware time required")
    now=now.astimezone(UTC)
    day=now.astimezone(ET).date().isoformat()
    games=[g for g in schedule.get("games",[]) if isinstance(g,dict) and
           g.get("date_eastern")==day and parsed(g.get("start"))]
    f=[p for p in forecast.get("predictions",[]) if isinstance(p,dict)]
    frozen=[p for p in archive.get("predictions",[]) if isinstance(p,dict)]
    counts=quick.get("matched_by_game",{}) if isinstance(quick.get("matched_by_game"),dict) else {}
    rows=[]
    for g in games:
        name=g.get("game")
        start=parsed(g["start"])
        secs=(start-now).total_seconds()
        upcoming=secs>0
        model=[p for p in f if p.get("game")==name and p.get("is_pregame_prediction") is True
               and parsed(p.get("start"))==start]
        saved=[p for p in frozen if p.get("game")==name and
               parsed(p.get("start"))==start and
               p.get("is_pregame_prediction") is True and
               p.get("line") is None and p.get("direction") is None and
               (captured:=parsed(p.get("captured_at"))) is not None and captured<start]
        statuses=[]
        if upcoming and not model:
            statuses.append("NO_CURRENT_PREGAME_FORECAST")
        if not saved:
            statuses.append("NO_IMMUTABLE_PRETIP_FORECAST_CAPTURE")
        if upcoming and counts.get(name,0)<=0:
            statuses.append("NO_PUBLISHED_PRIZEPICKS_AI_COMPARISON")
        # All three should be observable before imminent tipoff.
        imminent=0<secs<=1800
        if upcoming and imminent and not saved:
            statuses.append("IMMINENT_TIPOFF_WITHOUT_FROZEN_AI")
        if secs<=0 and not saved:
            statuses.append("TIPOFF_WITHOUT_FROZEN_AI")
        rows.append({"game":name,"start":start.isoformat(),
                     "minutes_to_tipoff":round(secs/60,1),
                     "current_forecasts":len(model),"frozen_forecasts":len(saved),
                     "published_prizepicks_matches":counts.get(name,0),
                     "state":"AT_RISK" if (imminent and statuses) or (secs<=0 and not saved)
                        else "WATCH" if statuses else "COVERED",
                     "reasons":statuses})
    critical=[r["game"] for r in rows if r["state"]=="AT_RISK"]
    full=bool(games) and schedule.get("coverage_complete") is True and          schedule.get("official_fixture_reconciliation",{}).get("verified_daily_counts",{}).get(day,{}).get("complete") is True
    return {"checked_at":now.isoformat(),"date_eastern":day,
            "status":"AT_RISK" if critical else "MONITORING" if not full or any(r["state"]=="WATCH" for r in rows) else "COVERED",
            "official_slate_complete":full,"scheduled_games":len(games),
            "games_with_forecasts":sum(x["current_forecasts"]>0 for x in rows),
            "games_with_frozen_forecasts":sum(x["frozen_forecasts"]>0 for x in rows),
            "games_with_published_comparisons":sum(x["published_prizepicks_matches"]>0 for x in rows),
            "critical_games":critical,"games":rows,
            "provider_board_partial":quick.get("partial_provider_board") is True,
            "note":"A snapshot coverage audit, not proof of live browser rendering or of quote completeness. Missing offers on a partial board are not assumed unavailable."}

def main():
    def read(filename):
        try:
            data=json.loads((ROOT/"docs"/filename).read_text())
            return data if isinstance(data,dict) else {}
        except (OSError,ValueError):
            return {}
    result=check(dt.datetime.now(UTC),read("nba_schedule.json"),
                 read("ai_projection_fallback.json"),
                 read("ai_no_line_pregame_archive.json"),
                 read("ai_prizepicks_quick_join_health.json"))
    (ROOT/"docs/pregame_coverage_watchdog.json").write_text(json.dumps(result,indent=2)+"\n")
    print("PREGAME COVERAGE:",json.dumps({k:result[k] for k in
          ("status","scheduled_games","games_with_forecasts",
           "games_with_frozen_forecasts","games_with_published_comparisons","critical_games")}))
    if result["status"]=="AT_RISK":
        raise SystemExit(2)

if __name__=="__main__":
    main()
