"""Paired, immutable-book assist V2 retrospective evaluation.

Run: python -m iphone_bot.assist_v2_backtest
No production model, sportsbook line, or saved pick is modified.
"""
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
try:
    from .assist_v2_research import forecast
    from .opportunity_backtest import histories, opportunity
    from .model_performance import independent_rows, forecast_values, quote_side_price, utc, finite
except ImportError:
    from assist_v2_research import forecast
    from opportunity_backtest import histories, opportunity
    from model_performance import independent_rows, forecast_values, quote_side_price, utc, finite

ROOT=Path(__file__).resolve().parents[1]
LEDGER=ROOT/"docs/paper_pick_ledger.json"
GAMES=ROOT/"data/nba/current/current_games.json"
OUT=ROOT/"docs/assist_v2_backtest.json"

def compare(records, games, sims=20000):
    index=histories(games)
    paired=[]
    skipped=Counter()
    for row in independent_rows(records):
        if row.get("market")!="AST": continue
        try:
            start=utc(row["event_start"])
            day=start.astimezone(ZoneInfo("America/New_York")).date().isoformat()
            pid=str(row["player_id"]); team=str(row["team"])
            line=finite(row.get("line")); actual=finite(row.get("actual"))
            base=forecast_values(row)["combined"]
            if any(v is None for v in (line,actual,base)):
                skipped["MISSING_LOCKED_VALUES"]+=1;continue
            hist=index.get((pid,team),[])
            minutes=opportunity(hist,day,team).get("expected_minutes")
            v2=forecast(hist,day,team,minutes,baseline=base,line=line,simulations=sims)
            if v2["status"]!="RESEARCH_FORECAST":
                skipped[v2["status"]]+=1;continue
            alt=v2["projection"]
            paired.append({"player":row.get("player"),"player_id":pid,
              "game":row.get("game"),"date":day,"line":line,"actual":actual,
              "baseline":base,"v2":alt,"v2_over_probability_uncalibrated":v2["over_probability"],
              "v2_push_probability_uncalibrated":v2["push_probability"],
              "baseline_side":"OVER" if base>line else "UNDER" if base<line else None,
              "v2_side":"OVER" if alt>line else "UNDER" if alt<line else None,
              "over_price":row.get("over_odds"),"under_price":row.get("under_odds"),
              "captured_at":row["captured_at"],"event_start":row["event_start"],
              "latest_prior_date":v2["latest_prior_date"],
              "baseline_over_probability":None,
              "v2_probability_calibrated":False,
              "_quote":row})
        except (ValueError,KeyError,TypeError,OverflowError,ZeroDivisionError):
            skipped["INVALID_ROW"]+=1
    def stats(name):
        err=[];wins=losses=pushes=0;profit=[];changed=0
        for r in paired:
            pred=r[name];line=r["line"];actual=r["actual"]
            err.append(abs(pred-actual))
            side=r[name+"_side"] if name=="v2" else r["baseline_side"]
            if side is None:continue
            if actual==line:pushes+=1;continue
            win=(side=="OVER")== (actual>line)
            wins+=int(win);losses+=int(not win)
            price=quote_side_price(r["_quote"],side)
            if price is not None:profit.append(price if win else -1.)
        return {"observations":len(err),"mae":round(sum(err)/len(err),4) if err else None,
                "wins":wins,"losses":losses,"pushes":pushes,
                "hit_rate":round(wins/(wins+losses),4) if wins+losses else None,
                "priced_picks":len(profit),
                "paper_roi":round(sum(profit)/len(profit),4) if profit else None}
    baseline=stats("baseline");challenger=stats("v2")
    for r in paired:r.pop("_quote")
    return {"status":"RETROSPECTIVE_RESEARCH_NOT_PRETIP_LOCKED",
       "generated_at":datetime.now(timezone.utc).isoformat(),
       "historical_features_strictly_before_target":True,
       "same_independent_markets_for_both_models":True,
       "model_developed_after_evaluated_games":True,
       "live_model_unchanged":True,
       "simulations_per_v2_forecast":sims,
       "baseline":baseline,"v2":challenger,
       "paired_mae_delta_v2_minus_baseline":round(challenger["mae"]-baseline["mae"],4) if paired else None,
       "changed_sides":sum(r["baseline_side"]!=r["v2_side"] for r in paired),
       "excluded":dict(skipped),"rows":paired,
       "promotion_gate":{"status":"BLOCKED_PENDING_PROSPECTIVE_VALIDATION",
         "minimum_pretip_locked_independent_markets":200,
         "minimum_distinct_game_dates":20,
         "require_lower_mae":True,"require_higher_paper_roi":True,
         "require_probability_calibration":True,
         "automatic_promotion":False},
       "limitations":["V2 created after these outcomes; retrospective improvement cannot justify promotion.",
         "No real pretip V2 snapshots or calibration cohort yet.",
         "Opportunity, injury, opponent and pace inputs are only used when genuinely available pregame.",
         "Simulation probability is uncalibrated; cannot be interpreted as betting edge."]}
def main():
    ledger=json.loads(LEDGER.read_text()).get("records",[])
    games=json.loads(GAMES.read_text()) if GAMES.exists() else []
    report=compare(ledger,games)
    OUT.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({k:report[k] for k in ("status","baseline","v2","paired_mae_delta_v2_minus_baseline","changed_sides","excluded")},indent=2))
if __name__=="__main__":main()
