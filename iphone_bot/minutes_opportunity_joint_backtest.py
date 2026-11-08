"""Joint independent historical audit of Minutes V3 and AST/REB Opportunity V2.

Entire 2025-26 regular season is an out-of-time evaluation domain;
all candidate inputs strictly precede each target player game.
No reconstructed sportsbook lines or assumed injuries. In this historical
run licensed tracking is absent, so opportunity candidates are explicitly
box-score rate proxies rather than potential-assist/rebound-chance statistics.
"""
import json,math
from collections import defaultdict
from datetime import datetime,timezone
from pathlib import Path
from statistics import mean

try:
 from .shot_profile_research import load_history
 from .minutes_v3_research import forecast as v3,team_context
 from .minutes_model_v2 import forecast as v2
 from .opportunity_v2_research import forecast as oppv2
except ImportError:
 from shot_profile_research import load_history
 from minutes_v3_research import forecast as v3,team_context
 from minutes_model_v2 import forecast as v2
 from opportunity_v2_research import forecast as oppv2

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"docs/minutes_v3_opportunity_v2_backtest.json"
MARKETS=("MIN","AST","REB")
def evaluate(records,season="2025-26"):
    groups=defaultdict(list)
    for row in records:
        if row.get("season")==season and row.get("id") and row.get("team") and row.get("date"):
            groups[(str(row["id"]),row["team"])].append(row)
    context=team_context(r for group in groups.values() for r in group)
    data={s:[] for s in MARKETS}
    for (pid,team),player_games in groups.items():
        history=[]
        for g in sorted(player_games,key=lambda x:(x["date"],str(x.get("game_id","")))):
            day=g["date"]
            # all team games observed on date are NEVER passed as inputs
            if len(history)>=8:
                a=v2(history,day,team).get("expected_minutes")
                b=v3(history,day,team,player_id=pid,team_games=context)
                if a is not None and b["expected_minutes"] is not None:
                    data["MIN"].append((day,float(g["MIN"]),float(a),float(b["expected_minutes"])))
                if b["expected_minutes"] is not None:
                    baselines={s:mean(float(x[s]) for x in history[-5:]) for s in ("AST","REB")}
                    o=oppv2(history,day,team,player_id=pid,minutes=b,
                            baseline_by_stat=baselines,team_games=context)
                    for stat in ("AST","REB"):
                        candidate=o["markets"][stat].get("projection")
                        if candidate is not None:
                            data[stat].append((day,float(g[stat]),baselines[stat],float(candidate)))
            history.append(g)
    result={}
    for stat,records in data.items():
        n=len(records)
        original=mean(abs(x[1]-x[2]) for x in records) if n else None
        alternative=mean(abs(x[1]-x[3]) for x in records) if n else None
        result[stat]={"paired_games":n,"distinct_game_dates":len({x[0] for x in records}),
            "baseline_mae":round(original,4) if n else None,
            "challenger_mae":round(alternative,4) if n else None,
            "challenger_minus_baseline_mae":round(alternative-original,4) if n else None,
            "candidate_better_individual_games":sum(abs(x[1]-x[3])<abs(x[1]-x[2]) for x in records),
            "baseline_better_individual_games":sum(abs(x[1]-x[3])>abs(x[1]-x[2]) for x in records)}
    return {"status":"HISTORICAL_JOINT_MINUTES_OPPORTUNITY_RESEARCH",
      "generated_at":datetime.now(timezone.utc).isoformat(),
      "holdout_season":season,"evaluated":result,
      "team_lineup_availability":"COMPLETE_PLAYER_GAME_PRESENCE_OBSERVED",
      "target_game_official_out_status":"NOT_IN_ARCHIVE_NO_TEAMMATE_INJURY_CLAIMS",
      "tracking_source":"NOT_CONNECTED_BOX_SCORE_AST_REB_RATE_PROXIES_ONLY",
      "historical_prop_line_hit_rates":None,
      "production_model_changed":False,
      "limitations":["Same-date outcomes excluded for each athlete",
          "Min V3 lineup adjustment off without independently verified pretip injury labels",
          "AST/REB opportunity backtest uses observed totals per minute, not genuine tracked chances",
          "No 2025-26 sportsbook prop lines provided, so only stat prediction MAE is measured",
          "Historical retrospective backtest does not substitute for prospective frozen grading"]}
def main():
    rows,rejected=load_history()
    result=evaluate(rows)
    result["validated_archival_rows"]=len(rows)
    result["source_rejections"]=rejected
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(result,indent=2)+"\n")
    print("JOINT_V3_V2_HOLDOUT",json.dumps(result["evaluated"]))
if __name__=="__main__":main()
