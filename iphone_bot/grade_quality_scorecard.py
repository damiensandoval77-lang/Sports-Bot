"""Explain verified paper performance without changing frozen historical picks.

All counts come from existing independently deduplicated grading summaries.
No retrospective model tuning, no implied profitable edge from two dates.
"""
import json
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
INPUT=ROOT/"docs/paper_results.json"
OUTPUT=ROOT/"docs/grade_quality_scorecard.json"
MARKETS=("PTS","REB","AST","PRA")

def build(results):
    performance=results.get("performance") or {}
    models=performance.get("models") or {}
    combined=models.get("combined") or {}
    stats=performance.get("by_stat") or {}
    audit=results.get("probability_audit") or {}
    probs=audit.get("overall") or {}
    dates=int((results.get("accuracy_feedback") or {}).get("overall",{}).get("overall",{}).get("distinct_game_dates") or 0)
    rows=[]
    for market in MARKETS:
        row=(stats.get(market) or {}).get("combined") or {}
        rows.append({"market":market,"graded":int(row.get("direction_eligible") or 0),
            "wins":int(row.get("direction_wins") or 0),
            "losses":int(row.get("direction_losses") or 0),
            "hit_rate":row.get("direction_hit_rate"),
            "mae":row.get("mae"),
            "paper_roi_per_priced_unit":row.get("paper_roi_per_priced_unit"),
            "priced":int(row.get("priced_paper_selections") or 0)})
    assert sum(x["graded"] for x in rows)==int(combined.get("direction_eligible") or 0)
    selection=results.get("selective_challenger") or {}
    screened=list((selection.get("by_stat") or {}).values())
    screen_wins=sum(int(x.get("wins") or 0) for x in screened)
    screen_losses=sum(int(x.get("losses") or 0) for x in screened)
    screen_total=screen_wins+screen_losses
    return {"status":"NO_VALIDATED_PROFITABLE_EDGE","generated_at":datetime.now(timezone.utc).isoformat(),
        "source_generated_at":results.get("generated_at"),
        "independent_game_dates":dates,
        "minimum_future_game_dates_to_assess_new_changes":6,
        "all_model_directions":{"n":int(combined.get("direction_eligible") or 0),
            "wins":int(combined.get("direction_wins") or 0),
            "losses":int(combined.get("direction_losses") or 0),
            "hit_rate":combined.get("direction_hit_rate"),
            "paper_roi_per_priced_unit":combined.get("paper_roi_per_priced_unit")},
        "by_market":rows,
        "original_probability_audit":{"sample_size":probs.get("sample_size"),
            "mean_predicted":probs.get("average_estimated_probability"),
            "realized_hit_rate":probs.get("observed_hit_rate"),
            "calibration_gap":probs.get("calibration_gap"),
            "sufficient_for_recalibration":bool(audit.get("sufficient_overall_sample"))},
        "prospective_selective_research":{"n":screen_total,"wins":screen_wins,
            "losses":screen_losses,"hit_rate":round(screen_wins/screen_total,4) if screen_total else None,
            "validated":False,"cannot_be_assumed_profitable":True},
        "main_board_probability_usable":False,
        "main_board_ev_usable":False,
        "live_selection_edge_validated":False,
        "recommendation":"ABSTAIN_FROM_CALLING_RAW_MODEL_LEANS_BETTING_PICKS",
        "limitations":["Only two distinct completed game dates; player props are correlated.",
          "Original residual probability sample is not Combined AI confidence.",
          "Selective screener is early prospective research, not an approved production betting edge.",
          "No settled historical records or projection snapshots were changed."]}

def main():
    result=build(json.loads(INPUT.read_text()))
    OUTPUT.write_text(json.dumps(result,indent=2)+"\n")
    print("Audit",result["status"],result["all_model_directions"],"days",result["independent_game_dates"])

if __name__=="__main__":main()
