"""Append-only, source-proven pretip AI/PrizePicks baseline pairing.

A separate recovery lane: never confused with the opponent-aware New AI,
simulated probabilities, or an actual wager. No provider API calls.
"""
import datetime as dt
import json
import math
import unicodedata
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"docs/frozen_baseline_pregame_line_ledger.json"
OLD=ROOT/"docs/frozen_baseline_pregame_lines_2026-11-09.json"
STATUS="FROZEN_BASELINE_PRETIP_MARKETS_APPEND_ONLY"

def moment(value):
    try:
        t=dt.datetime.fromisoformat(str(value).replace("Z","+00:00"))
        return t.astimezone(dt.timezone.utc) if t.tzinfo else None
    except (TypeError,ValueError,OverflowError):return None

def norm(value):
    s=unicodedata.normalize("NFKD",str(value or "")).casefold()
    return "".join(ch for ch in s if ch.isalnum() and not unicodedata.combining(ch))

def ident(row):
    return tuple(str(row.get(field) or "") for field in ("player_id","team","game","start","stat"))

def safe_frozen(row):
    if not isinstance(row,dict) or row.get("source_model")!="PRETIP_AI_ONLY_ARCHIVE_BASELINE" or row.get("quote_tier")!="standard" or row.get("not_a_wager") is not True:
        return False
    start,lock,model,seen,generated=map(moment,[row.get(k) for k in
        ("start","locked_at","model_captured_at","quote_observed_at","provider_snapshot_at")])
    return bool(start and lock and model and seen and generated and
                model<=lock<start and seen<=generated<=lock and
                isinstance(row.get("provider_quote_id"),str) and row["provider_quote_id"] and
                all(type(row.get(k)) in (int,float) and math.isfinite(row[k]) and 0<=row[k]<=200 for k in ("line","model_projection")))

def freeze(prior,quotes,models,schedule,now=None,seed=None):
    now=now or dt.datetime.now(dt.timezone.utc)
    if prior and prior.get("status")!=STATUS:
        raise ValueError("Invalid previous immutable baseline ledger")
    existing={}
    for row in list((seed or {}).get("records",[]))+list(prior.get("records",[])):
        if not safe_frozen(row):raise ValueError("Invalid prior frozen baseline market")
        k=ident(row)
        if k in existing and existing[k]!=row:raise ValueError("Frozen pretip market conflict")
        existing[k]=row
    if quotes.get("status")!="VERIFIED_PRETIP_PRIZEPICKS_QUOTES_ARCHIVE" or models.get("status")!="IMMUTABLE_OBSERVED_PRETIP_NOLINE_AI_ARCHIVE" or schedule.get("coverage_complete") is not True:
        raise ValueError("Provider archive, AI archive, or official slate unavailable")
    games={g["game"]:g for g in schedule.get("games",[]) if isinstance(g,dict) and
           g.get("game") and moment(g.get("start")) and moment(g["start"])>now}
    forecasts=defaultdict(list)
    for r in models.get("predictions",[]):
        game=games.get(r.get("game"))
        start=moment(r.get("start"));captured=moment(r.get("captured_at"))
        if (not game or r.get("is_pregame_prediction") is not True or
           r.get("line") is not None or not r.get("player_id") or
           r.get("stat") not in ("PTS","REB","AST","PRA") or
           r.get("team") not in {game.get("home_abbreviation"),game.get("away_abbreviation")} or
           not start or not captured or not (captured<now<start) or
           abs((moment(game["start"])-start).total_seconds())>1800 or
           type(r.get("projection")) not in (int,float) or
           not math.isfinite(r["projection"]) or not 0<=r["projection"]<=200):
            continue
        k=(norm(r.get("player")),r["team"],r["game"],r["stat"],start.isoformat())
        forecasts[k].append(r)
    offers=defaultdict(list)
    for q in quotes.get("quotes",[]):
        game=games.get(q.get("game"))
        start=moment(q.get("starts_at"));observed=moment(q.get("observed_at"));generated=moment(q.get("source_generated_at"))
        if (not game or q.get("source")!="independent_prizepicksapi_com" or q.get("is_demo") is not False or
           q.get("tier")!="standard" or q.get("more_tier")!="standard" or q.get("less_tier")!="standard" or
           q.get("team") not in {game.get("home_abbreviation"),game.get("away_abbreviation")} or
           not start or not observed or not generated or not (observed<=generated<=now<start) or
           abs((moment(game["start"])-start).total_seconds())>1800 or
           type(q.get("line")) not in (int,float) or not math.isfinite(q["line"]) or not 0<=q["line"]<=200):
            continue
        k=(norm(q.get("player")),q["team"],q["game"],q["stat"],start.isoformat())
        offers[k].append(q)
    added=0
    for k,forecasts_for_key in forecasts.items():
        if len({(x["player_id"],x["projection"],x["captured_at"]) for x in forecasts_for_key})!=1:continue
        r=forecasts_for_key[0]
        if ident(r) in existing:continue
        options=offers.get(k,[])
        if not options:continue
        latest=max(moment(q["observed_at"]) for q in options)
        chosen=[q for q in options if moment(q["observed_at"])==latest]
        if len({q["line"] for q in chosen})!=1:continue
        q=chosen[0]
        row={"status":"FROZEN_PRETIP_RESEARCH_UNGRADED",
         "source_model":"PRETIP_AI_ONLY_ARCHIVE_BASELINE",
         "source_model_archive":"docs/ai_no_line_pregame_archive.json",
         "source_quote_archive":"docs/prizepicks_pregame_line_archive.json",
         "game":r["game"],"team":r["team"],"player":r["player"],
         "player_id":r["player_id"],"stat":r["stat"],"start":r["start"],
         "model_projection":r["projection"],"model_captured_at":r["captured_at"],
         "provider_quote_id":str(q.get("id") or ""),"line":q["line"],"quote_tier":"standard",
         "quote_observed_at":q["observed_at"],
         "provider_snapshot_at":q["source_generated_at"],
         "locked_at":now.isoformat(),
         "modeled_direction":"More" if r["projection"]>q["line"] else "Less" if r["projection"]<q["line"] else "No lean",
         "estimated_hit_chance":None,"calibrated_probability":None,
         "not_a_wager":True,"grade":"PENDING","actual":None,"verified_final_source":None}
        if not safe_frozen(row):continue
        existing[ident(row)]=row
        added+=1
    rows=sorted(existing.values(),key=lambda r:(r["start"],r["game"],r["team"],r["player_id"],r["stat"]))
    return {"status":STATUS,"updated_at":now.isoformat(),"original_record_count":len(rows),
            "new_pretip_locks":added,"record_count":len(rows),
            "records":rows,"immutable_predictions":True,"not_a_wager":True,
            "note":"Prospective authentic standard quotes joined to earlier captured baseline-model AI forecasts; no calibrated probabilities, no simulated win rates, no retroactive capture."}

def main():
    def load(p):return json.loads(p.read_text()) if p.exists() else {}
    existing=load(OUT)
    seed=load(OLD) if not existing else {}
    out=freeze(existing,load(ROOT/"docs/prizepicks_pregame_line_archive.json"),
        load(ROOT/"docs/ai_no_line_pregame_archive.json"),
        load(ROOT/"docs/nba_schedule.json"),seed=seed)
    OUT.write_text(json.dumps(out,ensure_ascii=False,separators=(",",":"))+"\n")
    print("AUTOMATIC FROZEN BASELINE",out["record_count"],"NEW",out["new_pretip_locks"])
if __name__=="__main__":main()
