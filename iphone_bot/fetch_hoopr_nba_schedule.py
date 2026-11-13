"""Refresh daily NBA fixture slate from public independently updated ESPN-derived parquet.

No API key, odds, or simulated game starts. The season parquet is refreshed by
sportsdataverse. Validate true team names, game date, game state and 2026-27
season before publishing. Retain prior source if unavailable; do not make up
matchups or prices.
"""
import io,json,urllib.request
from datetime import datetime,timedelta,timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import pandas as pd
try:
 from .season_schedule_baseline import build as build_season_baseline, START, END
except ImportError:
 from season_schedule_baseline import build as build_season_baseline, START, END

ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/"docs/nba_schedule.json"
STATUS=ROOT/"docs/nba_schedule_status.json"
SEASON_ARCHIVE=ROOT/"docs/nba_season_schedule_2026_27.json"
URL="https://raw.githubusercontent.com/sportsdataverse/hoopR-nba-data/main/nba/schedules/parquet/nba_schedule_2027.parquet"
ET=ZoneInfo("America/New_York")
TEAM={
 "ATL","BOS","BKN","CHA","CHI","CLE","DAL","DEN","DET",
 "GSW","HOU","IND","LAC","LAL","MEM","MIA","MIL","MIN",
 "NOP","NYK","OKC","ORL","PHI","PHX","POR","SAC","SAS",
 "TOR","UTA","WAS"}
ALIASES={"NO":"NOP","NY":"NYK","GS":"GSW","SA":"SAS","UTAH":"UTA","PHO":"PHX","BRK":"BKN","WSH":"WAS"}
def value(v):
 if v is None or pd.isna(v):return ""
 return str(v).strip()
def parse(frame, now, days=None):
 if not all(c in frame.columns for c in (
    "date","home_display_name","away_display_name",
    "home_abbreviation","away_abbreviation","status_type_state","season_type","id")):
  raise ValueError("Published NBA schedule parquet changed columns")
 days=set(days) if days is not None else {(now.astimezone(ET).date()+timedelta(days=n)).isoformat() for n in (0,1)}
 games=[]
 seen=set()
 for row in frame.to_dict(orient="records"):
  if value(row.get("season_type")) not in ("2","2.0"):continue
  try:
   stamp=datetime.fromisoformat(value(row.get("date")).replace("Z","+00:00"))
   if stamp.tzinfo is None:continue
   date=stamp.astimezone(ET).date().isoformat()
  except (TypeError,ValueError):continue
  if date not in days:continue
  h=value(row["home_display_name"]);a=value(row["away_display_name"])
  home=ALIASES.get(value(row["home_abbreviation"]).upper(),
                   value(row["home_abbreviation"]).upper())
  away=ALIASES.get(value(row["away_abbreviation"]).upper(),
                   value(row["away_abbreviation"]).upper())
  state=value(row["status_type_state"]).lower()
  game_id=value(row["id"])
  if (home not in TEAM or away not in TEAM or home==away or
      not a or not h or not game_id or game_id in seen or
      state not in ("pre","in","post")):continue
  seen.add(game_id)
  games.append({"id":game_id,"game":a+" @ "+h,
    "home":h,"away":a,"home_abbreviation":home,"away_abbreviation":away,
    "start":stamp.astimezone(timezone.utc).isoformat(),
    "date_eastern":date,"game_state":state,
    "home_score":None,"away_score":None,
    "clock":None,"period":None,"status_detail":None})
 games.sort(key=lambda x:(x["start"],x["game"]))
 return {"status":"THIRD_PARTY_NBA_SCHEDULE_ONLY",
   "generated_at":now.isoformat(),"source":"sportsdataverse hoopR 2026-27 ESPN-sourced season schedule",
   "source_url":URL,"source_records_rejected":0,
   "timezone":"America/New_York","dates_eastern":sorted(days),
   "games":games,"total_games":len(games),
   "coverage_complete":True,"has_sportsbook_props":False,
   "has_verified_player_availability":False,
   "limitations":["Season schedule and dates only; neither player prop lines nor injuries",
                  "A season file cannot guarantee late postponements or last-minute time changes"]}
def apply_official_evidence(report,evidence_path=ROOT/"docs/verified_official_nba_fixtures.json"):
 """Validate and recover source-confirmed missing games BEFORE any publication.

 This is deliberately inside the source fetcher, not only a downstream job:
 all scheduled workflows importing or executing this fetcher receive the
 same reconciled 8-game slate instead of overwriting it with stale hoopR.
 """
 if not evidence_path.exists():
  return report
 try:
  from .reconcile_official_nba_schedule import reconcile
 except ImportError:
  from reconcile_official_nba_schedule import reconcile
 evidence=json.loads(evidence_path.read_text())
 return reconcile(report,evidence)

def fetch(now=None):
 now=now or datetime.now(timezone.utc)
 req=urllib.request.Request(URL,headers={"User-Agent":"SportsBot-NBA-Schedule/1.0"})
 with urllib.request.urlopen(req,timeout=25) as r:
  raw=r.read(8_000_001)
 if len(raw)>8_000_000:raise ValueError("Parquet exceeds bounded schedule size")
 frame=pd.read_parquet(io.BytesIO(raw))
 if len(frame)<900 or len(frame)>1600:raise ValueError("Unrecognized NBA full season schedule coverage")
 # Freeze the entire published regular-season fixture calendar independently
 # of the next-two-days dashboard view. A truncated/corrupt source must never
 # replace an existing valid season baseline.
 season_days=set()
 cursor=START
 while cursor<=END:
  season_days.add(cursor.isoformat())
  cursor+=timedelta(days=1)
 season_rows=parse(frame,now,days=season_days)["games"]
 from collections import Counter
 found={g[k] for g in season_rows for k in ("home_abbreviation","away_abbreviation")}
 if found!=TEAM:
  print("FULL_SEASON_TEAM_COVERAGE_DIAGNOSTIC:",
        json.dumps({"count":len(season_rows),"present":sorted(found),
        "missing":sorted(TEAM-found),
        "home_frequencies":dict(Counter(g["home_abbreviation"] for g in season_rows))}),
        flush=True)
 baseline=build_season_baseline(season_rows,now=now,
   source="sportsdataverse hoopR 2026-27 ESPN-sourced regular-season schedule",
   source_url=URL)
 report=apply_official_evidence(parse(frame,now))
 report["season_baseline_status"]=baseline["status"]
 report["season_baseline_total"]=baseline["total_games"]
 # Persist the master only after the entire source and the active slate
 # both pass validation. A downstream GitHub commit stages both atomically.
 SEASON_ARCHIVE.write_text(json.dumps(baseline,indent=2)+"\n")
 return report
def main():
 now=datetime.now(timezone.utc)
 report=fetch(now)
 OUTPUT.write_text(json.dumps(report,indent=2)+"\n")
 STATUS.write_text(json.dumps({
   "generated_at":now.isoformat(),"status":"SCHEDULE_FETCHED",
   "source":report["source"],"total_games":report["total_games"],
   "coverage_complete":report["coverage_complete"],
   "official_fixture_reconciliation":report.get("official_fixture_reconciliation")},indent=2)+"\n")
 print("NBA schedule from public season dataset:",
       report["total_games"],"games on",report["dates_eastern"])
if __name__=="__main__":main()
