"""Audit all genuine archived sportsbook quotes during prospective paper capture.

No new betting selection, prices or post-tip predictions. Eligibility is the
existing paper pipeline's exact conservative input/side/price policy.
"""
from collections import Counter
import math

try:
    from .paper_pick_pipeline import identity,payout,utc,expected_opponents
except ImportError:
    from paper_pick_pipeline import identity,payout,utc,expected_opponents

def coverage(comparisons,locked,captured_at):
    at=utc(captured_at)
    locked_keys={identity(r) for r in locked}
    statuses=Counter()
    examples=[]
    seen=set()
    for item in comparisons:
        for book in item.get("book_quotes",[]):
            reason="ELIGIBLE_AND_FROZEN"
            try:
                event=utc(item["start"])
                if at>=event:
                    reason="GAME_ALREADY_STARTED"
                elif item.get("stat") not in ("PTS","REB","AST","PRA"):
                    reason="UNSUPPORTED_MARKET"
                elif not expected_opponents(item["game"],str(item["team"])):
                    reason="TEAM_NOT_IN_MATCHUP"
                else:
                    model=float(item.get("combined_projection",item["projection"]))
                    original=float(item["projection"])
                    line=float(book["line"])
                    if not all(math.isfinite(v) and v>=0 for v in (model,original,line)):
                        reason="INVALID_FORECAST_OR_LINE"
                    elif model==line:
                        reason="MODEL_AT_EXACT_LINE_NO_SIDE"
                    else:
                        side="over" if model>line else "under"
                        payout(book[side])
                        key=identity({"event_start":event.isoformat(),
                          "player_id":str(item["player_id"]),"team":str(item["team"]),
                          "market":item["stat"],"bookmaker":str(book["name"]),
                          "line":line})
                        if key in seen:reason="DUPLICATE_SAME_QUOTE"
                        elif key not in locked_keys:reason="ELIGIBLE_QUOTE_MISSING_FROM_LEDGER"
                        seen.add(key)
            except (ValueError,TypeError,KeyError,OverflowError):
                reason="INVALID_SIDE_ODDS_OR_REQUIRED_IDENTITY"
            statuses[reason]+=1
            if reason not in ("ELIGIBLE_AND_FROZEN","DUPLICATE_SAME_QUOTE") and len(examples)<25:
                examples.append({"player":str(item.get("player","")),
                    "market":str(item.get("stat","")),"game":str(item.get("game","")),
                    "bookmaker":str(book.get("name","")),"line":book.get("line"),
                    "reason":reason})
    return {"status":"PRETIP_QUOTE_CAPTURE_COVERAGE_AUDIT",
       "captured_at":at.isoformat(),"quote_occurrences_checked":sum(statuses.values()),
       "eligibility_by_reason":dict(statuses),
       "eligible_quote_missing_from_ledger":statuses["ELIGIBLE_QUOTE_MISSING_FROM_LEDGER"],
       "excluded_quote_examples":examples,
       "excluded_not_backfilled":True,
       "live_probability_and_pick_selection_unchanged":True}

def verify(comparisons,locked,captured_at):
    result=coverage(comparisons,locked,captured_at)
    if result["eligible_quote_missing_from_ledger"]:
        raise AssertionError("Eligible pretip sportsbook quotes missing from paper ledger")
    return result
