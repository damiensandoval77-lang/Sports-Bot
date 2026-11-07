"""Lock research-only assist V2 snapshots from verified pretip AI board.

Append-only: original snapshots are never recalculated or overwritten.
"""
import json
from datetime import datetime, timezone
from pathlib import Path
try:
    from .assist_v2_research import forecast
    from .opportunity_backtest import histories, opportunity
    from .paper_pick_pipeline import utc, expected_opponents
except ImportError:
    from assist_v2_research import forecast
    from opportunity_backtest import histories, opportunity
    from paper_pick_pipeline import utc, expected_opponents

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"docs/assist_v2_shadow_ledger.json"
BOARD=ROOT/"docs/ai_comparisons.json"
GAMES=ROOT/"data/nba/current/current_games.json"

def capture(board,games,existing,now=None):
    stamp=utc(now or datetime.now(timezone.utc).isoformat())
    generated=utc(board["generated_at"])
    if board.get("status")!="EXPERIMENTAL_NON_CALIBRATED" or board.get("verified_current_matchups") is not True:
        raise ValueError("Unverified AI board")
    if not 0 <= (stamp-generated).total_seconds() <= 45*60:
        raise ValueError("Board is not fresh")
    index=histories(games)
    result=list(existing)
    seen={(str(r["event_start"]),str(r["player_id"]),str(r["team"]),str(r["bookmaker"]),float(r["line"])) for r in result}
    for row in board.get("comparisons",[]):
        if row.get("stat")!="AST":continue
        try:
            start=utc(row["start"])
            if stamp>=start:continue
            pid=str(row["player_id"]);team=str(row["team"])
            if not expected_opponents(row["game"],team):continue
            base=float(row["combined_projection"])
            day=start.astimezone(__import__("zoneinfo").ZoneInfo("America/New_York")).date().isoformat()
            hist=index.get((pid,team),[])
            minutes=opportunity(hist,day,team).get("expected_minutes")
            for quote in row.get("book_quotes",[]):
                line=float(quote["line"])
                key=(start.isoformat(),pid,team,str(quote["name"]),line)
                if key in seen:continue
                prediction=forecast(hist,day,team,minutes,baseline=base,line=line)
                if prediction["status"]!="RESEARCH_FORECAST":continue
                result.append({"event_start":start.isoformat(),"captured_at":stamp.isoformat(),
                  "player_id":pid,"player":row["player"],"team":team,
                  "game":row["game"],"market":"AST","bookmaker":str(quote["name"]),
                  "line":line,"baseline_projection":base,
                  "v2_projection":prediction["projection"],
                  "v2_over_probability_uncalibrated":prediction["over_probability"],
                  "v2_push_probability_uncalibrated":prediction["push_probability"],
                  "over_odds":quote.get("over"),"under_odds":quote.get("under"),
                  "prior_latest_date":prediction["latest_prior_date"],
                  "status":"PENDING","model":"ASSIST_V2_SHADOW_RESEARCH",
                  "production_applied":False,"simulations":prediction["simulations"]})
                seen.add(key)
        except (KeyError,TypeError,ValueError,OverflowError):
            continue
    return result

def main():
    board=json.loads(BOARD.read_text())
    games=json.loads(GAMES.read_text())
    old=json.loads(OUT.read_text()).get("records",[]) if OUT.exists() else []
    records=capture(board,games,old)
    OUT.write_text(json.dumps({"version":1,"records":records},indent=2)+"\n")
    print("V2 SHADOW:",len(records),"snapshots; new",len(records)-len(old))
if __name__=="__main__":main()
