"""Lock research-only assist V2 snapshots from verified pretip AI board.

Append-only: original snapshots are never recalculated or overwritten.
"""
import json
from datetime import datetime, timezone
from pathlib import Path
try:
    from .assist_v2_research import forecast
    from .opportunity_backtest import histories, opportunity
    from .paper_pick_pipeline import utc, expected_opponents, identity, settle
except ImportError:
    from assist_v2_research import forecast
    from opportunity_backtest import histories, opportunity
    from paper_pick_pipeline import utc, expected_opponents, identity, settle

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
    seen={identity(r) for r in result}
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
                key="|".join((start.isoformat(),pid,team.upper(),"AST",str(quote["name"]).casefold(),format(line,".10g")))
                if key in seen:continue
                prediction=forecast(hist,day,team,minutes,baseline=base,line=line)
                if prediction["status"]!="RESEARCH_FORECAST":continue
                if prediction["projection"]==line:continue
                side="OVER" if prediction["projection"]>line else "UNDER"
                odds=quote.get("over" if side=="OVER" else "under")
                try:
                    from .paper_pick_pipeline import payout
                except ImportError:
                    from paper_pick_pipeline import payout
                try:payout(odds)
                except (TypeError,ValueError):continue
                result.append({"side":side,"american_odds":int(odds),"event_start":start.isoformat(),"captured_at":stamp.isoformat(),
                  "player_id":pid,"player":row["player"],"team":team,
                  "game":row["game"],"market":"AST","bookmaker":str(quote["name"]),
                  "line":line,"baseline_projection":base,
                  "v2_projection":prediction["projection"],
                  "v2_over_probability_uncalibrated":prediction["over_probability"],
                  "v2_push_probability_uncalibrated":prediction["push_probability"],
                  "over_odds":quote.get("over"),"under_odds":quote.get("under"),
                  "prior_latest_date":prediction["latest_prior_date"],
                  "status":"PENDING","paper_only":True,"model":"ASSIST_V2_SHADOW_RESEARCH",
                  "production_applied":False,"simulations":prediction["simulations"]})
                seen.add(key)
        except (KeyError,TypeError,ValueError,OverflowError):
            continue
    return result

def grade(records,completed_games,now=None):
    """Use the production verifier without changing pretip V2 predictions."""
    return settle(records,completed_games,now=now)

def summary(records):
    unique={}
    for r in records:
        if r.get("status")!="SETTLED":continue
        key=(r["event_start"],r["player_id"],r["team"],r["market"],r["line"])
        unique.setdefault(key,r)
    rows=list(unique.values())
    decisions=[r for r in rows if r.get("result") in ("WIN","LOSS")]
    return {"captured":len(records),"settled":sum(r.get("status")=="SETTLED" for r in records),
            "pending":sum(r.get("status")=="PENDING" for r in records),
            "independent_settled_markets":len(rows),
            "wins":sum(r["result"]=="WIN" for r in decisions),
            "losses":sum(r["result"]=="LOSS" for r in decisions),
            "hit_rate":round(sum(r["result"]=="WIN" for r in decisions)/len(decisions),4) if decisions else None,
            "research_only":True}

def main():
    board=json.loads(BOARD.read_text())
    games=json.loads(GAMES.read_text())
    old=json.loads(OUT.read_text()).get("records",[]) if OUT.exists() else []
    records=capture(board,games,old)
    OUT.write_text(json.dumps({"version":1,"records":records},indent=2)+"\n")
    print("V2 SHADOW:",len(records),"snapshots; new",len(records)-len(old))
if __name__=="__main__":main()
