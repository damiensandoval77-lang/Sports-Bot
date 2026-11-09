"""Preserve genuine price-free NBA forecasts when the upcoming board rolls over.

Only forecasts whose original generation preceded scheduled tipoff qualify.
Never backfill from after-tipoff estimates, recompute archived estimates, or
infer a sportsbook line, direction, confidence, or settled grade.
"""
import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/"docs/ai_no_line_pregame_archive.json"
SOURCE=ROOT/"docs/ai_projection_fallback.json"
STATS={"PTS","REB","AST","PRA"}

def dt(value):
    try:
        val=datetime.fromisoformat(str(value).replace("Z","+00:00"))
        return val.astimezone(timezone.utc) if val.tzinfo else None
    except (ValueError,TypeError):return None

def merge(existing,feed,now=None):
    now=now or datetime.now(timezone.utc)
    seen={}
    def accept(item,stamp):
        if not isinstance(item,dict):return
        created=dt(item.get("captured_at") or stamp)
        start=dt(item.get("start"))
        if not created or not start or created>=start or created>now: return
        if start<now-timedelta(hours=48) or start>now+timedelta(hours=48):return
        if item.get("is_pregame_prediction") is not True or item.get("stat") not in STATS:return
        if item.get("line") is not None or item.get("direction") is not None:return
        if item.get("calibrated_probability") is not None:return
        if not (item.get("player") and item.get("player_id") and item.get("team") and item.get("game")):return
        try: proj=float(item["projection"])
        except (ValueError,TypeError,KeyError):return
        if not __import__("math").isfinite(proj) or not 0<=proj<=300:return
        key=(str(item["player_id"]),str(item["team"]),str(item["game"]),start.isoformat(),str(item["stat"]))
        # Earliest pretip snapshot always wins; later reruns cannot mutate it.
        candidate={**item,"captured_at":created.isoformat()}
        if key not in seen or dt(seen[key]["captured_at"])>created:
            seen[key]=candidate
    if existing.get("status")=="IMMUTABLE_OBSERVED_PRETIP_NOLINE_AI_ARCHIVE":
        for item in existing.get("predictions",[]):accept(item,existing.get("generated_at"))
    if feed.get("status")=="PREGAME_PROJECTIONS_NO_LINES":
        for item in feed.get("predictions",[]):accept(item,feed.get("generated_at"))
    rows=sorted(seen.values(),key=lambda p:(p["start"],p["game"],p["player"],p["stat"]))
    return {"status":"IMMUTABLE_OBSERVED_PRETIP_NOLINE_AI_ARCHIVE",
      "generated_at":now.isoformat(),"source":"TRAINED_NBA_PLAYER_REGRESSORS_WITHOUT_MARKET_LINES",
      "predictions":rows,"games_covered":len({p["game"] for p in rows}),
      "notice":"Original pretip AI projections, immutable over 48-hour rolling game window. No book lines, betting pick direction or verified probability."}

def main():
    current=json.loads(DEST.read_text()) if DEST.exists() else {}
    extra_path=os.environ.get("ADDITIONAL_PREGAME_ARCHIVE")
    if extra_path and Path(extra_path).exists():
        extra=json.loads(Path(extra_path).read_text())
        if extra.get("status")=="IMMUTABLE_OBSERVED_PRETIP_NOLINE_AI_ARCHIVE":
            current={"status":"IMMUTABLE_OBSERVED_PRETIP_NOLINE_AI_ARCHIVE",
                     "predictions":current.get("predictions",[])+extra.get("predictions",[])}
    fresh=json.loads(SOURCE.read_text()) if SOURCE.exists() else {}
    output=merge(current,fresh)
    DEST.write_text(json.dumps(output,separators=(",",":"))+"\n")
    print("PREGAME NO-LINE ARCHIVE:",len(output["predictions"]),
          "game identities:",output["games_covered"],flush=True)

if __name__=="__main__":main()
