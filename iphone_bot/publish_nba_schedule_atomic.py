"""Safely rebase NBA schedule publisher onto concurrent GitHub commits.

The verified full-season master is the source of missing fixtures, not
sportsbook line availability. A delayed empty daily refresh cannot erase
upcoming games or replace a fresher scored game.
"""
import datetime as dt
import json
import os
from pathlib import Path
from iphone_bot.season_schedule_baseline import validate, reconcile_window, ET

DOCS=Path(__file__).resolve().parents[1]/"docs"

def read(path):
    try:return json.loads(Path(path).read_text())
    except (OSError,ValueError):return {}

def stage(candidate_daily,candidate_master,current_daily,current_master,now=None):
    now=now or dt.datetime.now(dt.timezone.utc)
    try:master=validate(candidate_master)
    except (ValueError,KeyError,TypeError):
        master=validate(current_master)
    if current_master.get("status")==master.get("status"):
        try:
            current_master=validate(current_master)
            if str(current_master.get("generated_at",""))>str(master.get("generated_at","")):
                master=current_master
        except (ValueError,KeyError,TypeError):pass
    # Only fresh verified daily observations should override published
    # baseline fixture identity, original start time, or score.
    current_time=str(current_daily.get("generated_at") or "")
    candidate_time=str(candidate_daily.get("generated_at") or "")
    proposed=candidate_daily if candidate_time>=current_time else current_daily
    day=now.astimezone(ET).date()
    dates=[day,day+dt.timedelta(days=1)]
    observed=proposed.get("games",[]) if proposed.get("coverage_complete") is True else []
    rebuilt=reconcile_window(master,dates,observed)
    result=dict(proposed)
    result.update(rebuilt)
    result.update(status="THIRD_PARTY_NBA_SCHEDULE_ONLY",
                  generated_at=max(current_time,candidate_time,now.isoformat()),
                  source=(str(proposed.get("source",""))+" + verified full-season fixture repair"),
                  source_url=master.get("source_url"),
                  timezone="America/New_York",
                  has_sportsbook_props=False,
                  has_verified_player_availability=False,
                  season_baseline_status=master["status"],
                  season_baseline_total=master["total_games"])
    result["limitations"]=[
        "Published fixture baseline restores known games; it is not a player-line, injury, or live boxscore source.",
        "NBA Cup unassigned matches and revised tip times require later verification."]
    return result,master

def main():
    temp=Path(os.environ["RUNNER_TEMP"])
    proposed=read(temp/"new-day.json")
    incoming=read(temp/"new-season.json")
    current=read(DOCS/"nba_schedule.json")
    archived=read(DOCS/"nba_season_schedule_2026_27.json")
    day,season=stage(proposed,incoming,current,archived)
    DOCS.mkdir(parents=True,exist_ok=True)
    (DOCS/"nba_schedule.json").write_text(json.dumps(day,indent=2)+"\n")
    if archived.get("games")!=season.get("games"):
        (DOCS/"nba_season_schedule_2026_27.json").write_text(json.dumps(season,indent=2)+"\n")
    status=read(DOCS/"nba_schedule_status.json")
    status.update(generated_at=day["generated_at"],
                  status="SCHEDULE_FETCHED",source=day["source"],
                  total_games=day["total_games"],
                  coverage_complete=day["coverage_complete"],
                  season_baseline_total=season["total_games"])
    (DOCS/"nba_schedule_status.json").write_text(json.dumps(status,indent=2)+"\n")
    print("SAFE NBA SCHEDULE PUBLISH:",day["total_games"],
          "current fixtures; published season",season["total_games"],
          "recovered",day["baseline_recovered"])

if __name__=="__main__":main()
