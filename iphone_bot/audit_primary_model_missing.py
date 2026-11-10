"""Read-only exact-standard-price recovery diagnostics.

Never creates a late freeze, replaces an original price, treats a research
projection as a validated model, or calls paid APIs.
"""
import datetime as dt
import json
from collections import Counter
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]/"docs"
ET=ZoneInfo("America/New_York")

def eastern_date(value):
    try:
        t=dt.datetime.fromisoformat(str(value).replace("Z","+00:00"))
        return t.astimezone(ET).date().isoformat() if t.tzinfo else None
    except (TypeError,ValueError,OverflowError):return None

def key(x):
    try:line=float(x["line"])
    except (ValueError,TypeError,KeyError):return None
    return (x.get("game"),x.get("player"),x.get("team"),x.get("stat"),line)

def audit(quotes, frozen, live, research, day, now=None):
    now=now or dt.datetime.now(dt.timezone.utc)
    archive=[x for x in quotes.get("quotes",[])
             if x.get("tier")=="standard" and
             x.get("source")=="independent_prizepicksapi_com" and
             x.get("is_demo") is False and eastern_date(x.get("starts_at"))==day
             and key(x)]
    locked=[x for x in frozen.get("records",[]) if eastern_date(x.get("start"))==day and key(x)]
    modeled=[x for x in live.get("predictions",[]) if eastern_date(x.get("start"))==day and key(x)
             and x.get("pickem_tier")=="standard"
             and x.get("standard_line_two_sided_verified") is True]
    research_rows=[x for x in research.get("records",[]) if eastern_date(x.get("start"))==day and key(x)
                   and x.get("more_tier")=="standard" and x.get("less_tier")=="standard"
                   and x.get("research_only") is True]
    original={key(x) for x in locked}
    original_markets={k[:4] for k in original}
    live_quotes={key(x) for x in modeled}
    research_quotes={key(x) for x in research_rows}
    missing={key(x) for x in archive}-original
    reasons=Counter()
    details=[]
    for k in sorted(missing,key=lambda v:tuple(str(z) for z in v)):
        moved=k[:4] in original_markets
        live_available=k in live_quotes
        backed=k in research_quotes
        reason=("MOVED_ORIGINAL_STANDARD_THRESHOLD" if moved else
                "MODEL_EXISTS_BUT_PRIMARY_FREEZE_MISSING" if live_available else
                "NO_VALIDATED_PRIMARY_MODEL_FOR_MARKET")
        reasons[reason]+=1
        details.append({"game":k[0],"player":k[1],"team":k[2],
                        "stat":k[3],"standard_line":k[4],
                        "reason":reason,"new_live_model_available":live_available,
                        "separate_research_receipt":backed,
                        "original_primary_frozen_market":moved,
                        "safe_action":("PRESERVE_ORIGINAL_FROZEN_LINE_AND_RESEARCH_VERSION" if moved
                                       else "INVESTIGATE_MISSING_PRETIP_MODEL_OR_FEATURES")})
    return {"status":"PRIMARY_STANDARD_CAPTURE_INCOMPLETE" if missing else "PRIMARY_STANDARD_CAPTURE_VERIFIED",
            "checked_at":now.isoformat(),"game_date_eastern":day,
            "verified_standard_quotes":len({key(x) for x in archive}),
            "original_primary_frozen_quotes":len(original),
            "unmatched_exact_standard_thresholds":len(missing),
            "missing_by_cause":dict(sorted(reasons.items())),
            "details":details,
            "note":"Only original pre-tip validated models count in the primary grade ledger. Line moves and research-only quotes are never promoted, repriced, or retrograded."}

def main():
    def read(filename):
        try:return json.loads((ROOT/filename).read_text())
        except (OSError,ValueError):return {}
    now=dt.datetime.now(dt.timezone.utc)
    day=now.astimezone(ET).date().isoformat()
    result=audit(read("prizepicks_pregame_line_archive.json"),
                 read("lagged_matchup_all_market_ledger.json"),
                 read("lagged_matchup_live_all_markets.json"),
                 read("standard_quote_ai_research_archive.json"),day,now)
    (ROOT/"primary_model_missing_diagnostics.json").write_text(json.dumps(result,indent=2)+"\n")
    print("PRIMARY STANDARD LINE RECOVERY:",result["unmatched_exact_standard_thresholds"],
          result["missing_by_cause"])

if __name__=="__main__":main()
