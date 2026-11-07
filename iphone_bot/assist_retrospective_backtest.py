"""Retrospective assist challenger vs Nov 6 frozen sportsbook quotes.

The fixed assist_shadow_v1 formula was developed after these games; this is
NOT prospective performance, and no stored pretip assist_shadow_v1 forecast
exists for them. This audit uses *strictly prior* dated player game logs,
the originally locked baseline, bookmaker lines, and now known final assists.
"""
import json
from collections import defaultdict,Counter
from datetime import datetime,timezone
from pathlib import Path
from zoneinfo import ZoneInfo
try:
    from .assist_shadow_v1 import assist_shadow
    from .opportunity_backtest import histories,opportunity
    from .model_performance import independent_rows,forecast_values,utc,finite
except ImportError:
    from assist_shadow_v1 import assist_shadow
    from opportunity_backtest import histories,opportunity
    from model_performance import independent_rows,forecast_values,utc,finite

ROOT=Path(__file__).resolve().parents[1]
GAMES=ROOT/"data/nba/current/current_games.json"
LEDGER=ROOT/"docs/paper_pick_ledger.json"
OUT=ROOT/"docs/assist_retrospective_backtest.json"

def evaluation(records,game_rows):
    indexed=histories(game_rows)
    pairs=[];absent=Counter()
    for row in independent_rows(records):
        if row.get("market")!="AST":continue
        try:
            start=utc(row["event_start"])
            date=start.astimezone(ZoneInfo("America/New_York")).date().isoformat()
            pid=str(row["player_id"]);team=str(row.get("team",""))
            line=finite(row.get("line"));actual=finite(row.get("actual"))
            baseline=forecast_values(row)["combined"]
            if line is None or actual is None or baseline is None:
                absent["MISSING_FROZEN_BASELINE_OR_ACTUAL"]+=1;continue
            if actual==line:
                absent["PUSH_EXCLUDED"]+=1;continue
            hist=indexed.get((pid,team),[])
            prior=[x for x in hist if x["date"]<date]
            minutes=opportunity(hist,date,team).get("expected_minutes")
            attempt=assist_shadow(prior,date,team,baseline,minutes)
            if attempt["projection"] is None:
                absent[attempt["status"]]+=1;continue
            shadow=attempt["projection"]
            pairs.append({"game":row.get("game"),"date":date,
              "player":row.get("player"),"player_id":pid,"team":team,
              "line":line,"actual_assists":actual,
              "baseline_projection":round(baseline,4),
              "assist_shadow_projection":shadow,
              "baseline_side":"OVER" if baseline>line else "UNDER" if baseline<line else "NO_LEAN",
              "shadow_side":"OVER" if shadow>line else "UNDER" if shadow<line else "NO_LEAN",
              "baseline_win":int((baseline>line)==(actual>line)) if baseline!=line else None,
              "shadow_win":int((shadow>line)==(actual>line)) if shadow!=line else None,
              "baseline_error":round(abs(baseline-actual),4),
              "shadow_error":round(abs(shadow-actual),4),
              "prior_same_team_games":attempt["prior_games"],
              "latest_prior_game":attempt["latest_prior_date"],
              "projected_minutes":attempt.get("expected_minutes"),
              "retrospective_only":True})
        except (ValueError,TypeError,KeyError):
            absent["INVALID_SAVED_QUOTE"]+=1
    def describe(rows):
        n=len(rows)
        def sides(name):
            eligible=[r[name] for r in rows if r[name] is not None]
            w=sum(eligible)
            return {"record":f"{w}-{len(eligible)-w}","wins":w,"losses":len(eligible)-w,
              "eligible":len(eligible),"hit_rate":round(w/len(eligible),4) if eligible else None}
        return {"matched_assist_markets":n,
          "combined_ai":sides("baseline_win"),"assist_shadow_v1":sides("shadow_win"),
          "combined_ai_mae":round(sum(r["baseline_error"] for r in rows)/n,3) if n else None,
          "assist_shadow_mae":round(sum(r["shadow_error"] for r in rows)/n,3) if n else None,
          "distinct_game_dates":len({r["date"] for r in rows})}
    return {"generated_at":datetime.now(timezone.utc).isoformat(),
      "status":"RETROSPECTIVE_POST_HOC_RESEARCH_ONLY",
      "formula_created_after_game":True,
      "not_pregame_locked_shadow_predictions":True,
      "production_ai_unchanged":True,"simulated_probabilities_unchanged":True,
      "overall":describe(pairs),
      "by_game":{g:describe([r for r in pairs if r["game"]==g])
                 for g in sorted({r["game"] for r in pairs})},
      "coverage_exclusions":dict(absent),
      "eligible_assist_markets_saved":sum(1 for r in independent_rows(records) if r.get("market")=="AST"),
      "matched_player_examples":pairs[:100],
      "limitations":[
        "Candidate was defined AFTER outcomes; results are research only and cannot establish expected future wins.",
        "Every feature log must be STRICTLY older than event date (Eastern), and on the same team.",
        "Scores only markets with sufficient valid history, stable role, and expected minutes; baseline is scored on the IDENTICAL eligible subset.",
        "The original model's first saved pretip bookmaker line and forecasts remain immutable.",
        "Uses sportsbook quoted prices, not necessarily PrizePicks; no probability calibration or model promotion."
      ]}
def main():
    games=json.loads(GAMES.read_text()) if GAMES.exists() else []
    ledger=json.loads(LEDGER.read_text()).get("records",[])
    report=evaluation(ledger,games)
    OUT.write_text(json.dumps(report,indent=2)+"\n")
    print("RETROSPECTIVE ASSIST SHADOW:",json.dumps({k:report[k] for k in ("overall","eligible_assist_markets_saved","coverage_exclusions")}))
if __name__=="__main__":main()
