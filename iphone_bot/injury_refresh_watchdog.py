"""Free, bounded NBA injury/model synchronization watchdog.

Detects when published new AI was built from an earlier official report.
Only asks for recovery if a future scheduled NBA game remains. A separate
GitHub job limits retries and skips actively running projections.
"""
import argparse,json
from datetime import datetime,timezone,timedelta
from pathlib import Path
try:
    from .injury_refresh_integrity import integrity,official_version,ts
except ImportError:
    from injury_refresh_integrity import integrity,official_version,ts

ROOT=Path(__file__).resolve().parents[1]
def decision(injuries,model,schedule,now=None):
    now=now or datetime.now(timezone.utc)
    version=official_version(injuries)
    if not version:return {"needs_refresh":False,"reason":"NO_VERIFIED_OFFICIAL_REPORT"}
    if version>now or now-version>timedelta(hours=18):
        return {"needs_refresh":False,"reason":"OFFICIAL_REPORT_OUTSIDE_VALID_WINDOW"}
    future=[]
    for g in schedule.get("games",[]):
        tip=ts(g.get("start"))
        if tip and g.get("game_state")=="pre" and now<tip<now+timedelta(hours=24):
            future.append(g)
    if not future:return {"needs_refresh":False,"reason":"NO_UPCOMING_GAMES"}
    check=integrity(injuries,model,now)
    if not check["safe"]:
        return {"needs_refresh":True,"reason":check["reason"],"upcoming_games":len(future)}
    return {"needs_refresh":False,"reason":"MODEL_MATCHES_LATEST_OFFICIAL_REPORT",
            "upcoming_games":len(future)}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--official",default=str(ROOT/"docs/injury_context.json"))
    p.add_argument("--model",default=str(ROOT/"docs/lagged_matchup_live_all_markets.json"))
    p.add_argument("--schedule",default=str(ROOT/"docs/nba_schedule.json"))
    args=p.parse_args()
    def read(path):
        file=Path(path)
        return json.loads(file.read_text()) if file.exists() else {}
    result=decision(read(args.official),read(args.model),read(args.schedule))
    print("INJURY_AI_RECOVERY_WATCHDOG",json.dumps(result),flush=True)
    if result["needs_refresh"]:raise SystemExit(10)
if __name__=="__main__":main()
