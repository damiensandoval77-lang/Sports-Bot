"""Publish honest coverage of passing/rebounding tracking research.

Never turn a missing current prediction board into a false 0% accuracy claim,
and never imply provider connection from a passing unit test.
"""
import json
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1]
BOARD=ROOT/"docs/ai_comparisons.json"
RESEARCH=ROOT/"docs/projection_upgrade_status.json"
PROVIDER=ROOT/"docs/tracking_provider_access_status.json"
OUTPUT=ROOT/"docs/tracking_coverage_status.json"

def summarize(board,research,provider):
    comparisons=board.get("comparisons") if isinstance(board,dict) else None
    comparisons=comparisons if isinstance(comparisons,list) else []
    tracking=(research.get("tracking_opportunity_shadow") or {}) if isinstance(research,dict) else {}
    available=provider.get("gamelevel_tracking_connected") is True if isinstance(provider,dict) else False
    ready=provider.get("licensed_use_verified") is True if isinstance(provider,dict) else False
    markets={}
    for market in ("AST","REB"):
        count=sum(1 for x in comparisons if isinstance(x,dict) and x.get("stat")==market)
        result=(tracking.get("by_market") or {}).get(market) or {}
        markets[market]={"current_board_models":count,
            "genuinely_graded_tracking_shadows":result.get("paired_markets",0),
            "grade_eligible_exact_line":result.get("exact_line_eligible",0),
            "confirmed_tracking_coverage":0 if not available or not ready else None}
    return {"generated_at":datetime.now(timezone.utc).isoformat(),
      "status":"NO_AUTHORIZED_GAMELEVEL_TRACKING" if not available or not ready else
               "SOURCE_AVAILABLE_REQUIRES_PLAYER_GAME_VALIDATION",
      "board_status":board.get("status","UNKNOWN"),
      "current_board_empty":len(comparisons)==0,
      "no_current_board_is_not_zero_accuracy":True,
      "provider_auth_configured":provider.get("status")!="NOT_CONFIGURED_NEEDS_PROVIDER_TOKEN" if isinstance(provider,dict) else False,
      "gamelevel_tracking_connected":bool(available and ready),
      "real_tracking_accuracy_improvement_proven":False,
      "by_market":markets,"live_ai_unchanged":True}

def main():
    def load(p):
        try:return json.loads(p.read_text())
        except (OSError,ValueError):return {}
    result=summarize(load(BOARD),load(RESEARCH),load(PROVIDER))
    OUTPUT.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result))

if __name__=="__main__":main()
