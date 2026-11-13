"""Lock every eligible trained NBA prediction before tipoff for future grading.

Runs immediately after model comparison, BEFORE any delayed grading/research
jobs. Never reconstructs snapshots from postgame data. No live bets.
"""
import json
from datetime import datetime,timezone
from pathlib import Path
try:
    from .paper_pick_pipeline import LEDGER,RESULTS,ROOT,snapshot,summary,utc
except ImportError:
    from paper_pick_pipeline import LEDGER,RESULTS,ROOT,snapshot,summary,utc

try:
    from .quote_capture_coverage import verify as verify_quote_coverage
except ImportError:
    from quote_capture_coverage import verify as verify_quote_coverage

COVERAGE=ROOT/"docs/pregame_quote_capture_coverage.json"
COMPARISONS=ROOT/"docs/ai_comparisons.json"
CURRENT_FORM=ROOT/"docs/current_form.json"


def capture(current,existing,now=None):
    now=utc(now or datetime.now(timezone.utc).isoformat())
    if current.get("status")!="EXPERIMENTAL_NON_CALIBRATED" or current.get("verified_current_matchups") is not True:
        raise ValueError("Only trained and identity-verified AI comparisons can be locked")
    generated=utc(current["generated_at"])
    age=(now-generated).total_seconds()
    if age<0 or age>45*60:
        raise ValueError("AI predictions must be freshly generated and captured before tipoff")
    rows=current.get("comparisons")
    if not isinstance(rows,list):
        raise ValueError("No model comparison array")
    # Use actual capture time, NOT the earlier generation timestamp:
    # no prediction created after tipoff can be made to appear pregame.
    locked=snapshot(rows,now.isoformat(),existing)
    if len(locked)<len(existing):raise AssertionError("Locked picks deleted")
    return locked


def main():
    current=json.loads(COMPARISONS.read_text())
    existing=json.loads(LEDGER.read_text()).get("records",[]) if LEDGER.exists() else []
    capture_time=datetime.now(timezone.utc).isoformat()
    locked=capture(current,existing,capture_time)
    quote_report=verify_quote_coverage(current.get("comparisons",[]),locked,capture_time)
    COVERAGE.write_text(json.dumps(quote_report,indent=2)+"\n")
    added=len(locked)-len(existing)
    LEDGER.write_text(json.dumps({"version":1,"records":locked},indent=2)+"\n")
    form=json.loads(CURRENT_FORM.read_text()) if CURRENT_FORM.exists() else None
    RESULTS.write_text(json.dumps(summary(locked,source=form),indent=2)+"\n")
    print("AI PRE-GAME SNAPSHOTS:",json.dumps({
        "existing":len(existing),"new":added,"total":len(locked),
        "pending":sum(x["status"]=="PENDING" for x in locked),
        "settled_preserved":sum(x["status"]=="SETTLED" for x in locked),
        "generated_at":current["generated_at"],
        "quote_eligibility":quote_report["eligibility_by_reason"]}),flush=True)


if __name__=="__main__":main()
