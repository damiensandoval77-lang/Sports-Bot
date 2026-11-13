"""No-paid-API emergency publisher: genuine fresh PrizePicks lines × pregame AI.

Does not re-train models or compute a calibrated hit probability. It publishes
a distinct research-only comparison surface, never overwriting sportsbooks.
Stale upstream data fail closed with explicit diagnostics, never fake picks.
"""
import datetime as dt
import json
import math
import unicodedata
from collections import Counter,defaultdict
from pathlib import Path
from zoneinfo import ZoneInfo

from iphone_bot.paper_pick_pipeline import expected_opponents

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"docs/prizepicks_site.json"
AI=ROOT/"docs/ai_projection_fallback.json"
FORM=ROOT/"docs/current_form.json"
OUT=ROOT/"docs/ai_prizepicks_quick_join.json"
HEALTH=ROOT/"docs/ai_prizepicks_quick_join_health.json"
STAT={"PTS","REB","AST","PRA"}
MAX_PP_AGE=90*60
MAX_MODEL_AGE=3*3600
ET=ZoneInfo("America/New_York")

def utc(x):
    try:
        t=dt.datetime.fromisoformat(str(x).replace("Z","+00:00"))
        return t.astimezone(dt.timezone.utc) if t.tzinfo else None
    except (ValueError,TypeError):return None

def normal_name(value):
    s=unicodedata.normalize("NFKD",str(value or "")).casefold()
    return "".join(c for c in s if c.isalnum() and not unicodedata.combining(c))

def build(provider,ai,form,now=None):
    now=now or dt.datetime.now(dt.timezone.utc)
    base={
        "generated_at":now.isoformat(),"status":"UNAVAILABLE_INPUTS",
        "source":"OBSERVED_PRIZEPICKS_VS_SAVED_PREGAME_REGRESSORS",
        "research_only":True,"has_actual_prizepicks_lines":False,
        "has_verified_american_sportsbook_odds":False,
        "calibrated_hit_probability_available":False,
        "offers_matched":0,"matched_games":0,
        "comparisons":[],"skipped_reasons":{},"missing_official_games":[],
        "provider_generated_at":provider.get("generated_at"),
        "model_generated_at":ai.get("generated_at")}
    failures=[]
    if provider.get("status")!="LIVE_THIRD_PARTY_PRIZEPICKS_LINES":
        failures.append("NO_OBSERVED_PRIZEPICKS_SOURCE")
    if ai.get("status")!="PREGAME_PROJECTIONS_NO_LINES":
        failures.append("NO_OBSERVED_PREGAME_MODEL_BOARD")
    ptime=utc(provider.get("generated_at"))
    atime=utc(ai.get("generated_at"))
    if not ptime or not 0<=(now-ptime).total_seconds()<=MAX_PP_AGE:
        failures.append("PROVIDER_SNAPSHOT_STALE")
    if not atime or not 0<=(now-atime).total_seconds()<=MAX_MODEL_AGE:
        failures.append("AI_FORECAST_SNAPSHOT_STALE")
    if form.get("season")!="2026-27" or not isinstance(form.get("players"),list):
        failures.append("ROSTER_NOT_VERIFIED")
    if failures:return {**base,"status":"STALE_OR_UNVERIFIED_SOURCE",
                       "skipped_reasons":dict(Counter(failures))}
    roster=defaultdict(set)
    for p in form["players"]:
        if not isinstance(p,dict):continue
        n=normal_name(p.get("player")); team=p.get("team")
        if n and team:roster[n].add((str(team),str(p.get("player_id"))))
    forecasts=defaultdict(list)
    for p in ai.get("predictions",[]):
        if not isinstance(p,dict) or p.get("is_pregame_prediction") is not True:
            continue
        if p.get("line") is not None or p.get("direction") is not None:continue
        start=utc(p.get("start"))
        if not start or start<=now or p.get("stat") not in STAT:continue
        try: projected=float(p.get("projection"))
        except (TypeError,ValueError):continue
        if not math.isfinite(projected) or projected<0 or projected>250:continue
        forecasts[(normal_name(p.get("player")),str(p.get("team")),
                   p.get("game"),start.isoformat(),p.get("stat"))].append((p,projected))
    skip=Counter()
    matched=[];seen=set()
    for offer in provider.get("board_offers",[]):
        if not isinstance(offer,dict):
            skip["malformed_offer"]+=1;continue
        if offer.get("is_demo") is not False or offer.get("source")!="independent_prizepicksapi_com":
            skip["unverified_offer"]+=1;continue
        start=utc(offer.get("starts_at")); observed=utc(offer.get("observed_at"))
        if not start or not observed or start<=now or not 0<=(now-observed).total_seconds()<=MAX_PP_AGE:
            skip["started_or_stale_offer"]+=1;continue
        team=str(offer.get("team") or "")
        name=normal_name(offer.get("player"))
        game=offer.get("game")
        stat=offer.get("stat")
        opponents=expected_opponents(game,team)
        if len(opponents)!=1 or (offer.get("opponent") and offer["opponent"] not in opponents):
            skip["team_opponent_mismatch"]+=1;continue
        people=roster.get(name,set())
        if len(people)!=1 or next(iter(people))[0]!=team:
            skip["missing_or_ambiguous_roster"]+=1;continue
        key=(name,team,game,start.isoformat(),stat)
        options=forecasts.get(key,[])
        if len(options)!=1:
            skip["no_unique_pregame_forecast"]+=1;continue
        p,projection=options[0]
        # Identity must agree with the unique season roster, not just the name/team.
        # A reused name or stale model player ID must never inherit a real quote.
        roster_id=next(iter(people))[1]
        if not roster_id or str(p.get("player_id") or "")!=roster_id:
            skip["roster_player_id_mismatch"]+=1;continue
        try:line=float(offer.get("line"))
        except (TypeError,ValueError):
            skip["invalid_line"]+=1;continue
        if not math.isfinite(line) or line<0 or line>=250:
            skip["invalid_line"]+=1;continue
        if offer.get("more_tier")!="standard" or offer.get("less_tier")!="standard":
            skip["not_two_sided_standard_line"]+=1;continue
        original_id=str(offer.get("id") or "")
        identity=(original_id,key,line)
        if identity in seen:continue
        seen.add(identity)
        difference=round(projection-line,2)
        matched.append({
          "provider_projection_id":original_id,"player":offer["player"],
          "player_id":str(p["player_id"]),"team":team,"opponent":opponents[0],
          "game":game,"start":start.isoformat(),"stat":stat,"line":line,
          "observed_at":observed.isoformat(),"model_generated_at":atime.isoformat(),
          "projection":round(projection,2),"difference":difference,
          "ai_direction":"MORE" if difference>0 else "LESS" if difference<0 else "NO_LEAN",
          "more_tier":offer.get("more_tier"),"less_tier":offer.get("less_tier"),
          "source":"independent_prizepicksapi_com","research_only":True,
          "confidence_percent":None,"estimated_ev":None,
          "book_quotes":[],"odds":None,
          "reliability_screen":{"validated":False,"side":None}
        })
    matched.sort(key=lambda p:(p["start"],p["game"],p["player"],p["stat"],p["line"]))
    status=("FRESH_RESEARCH_ONLY_PRIZEPICKS_AI_COMPARISONS" if matched
            else "NO_MATCHED_UPCOMING_MARKETS")
    return {**base,"status":status,
         "has_actual_prizepicks_lines":bool(matched),
         "offers_matched":len(matched),
         "matched_games":len({p["game"] for p in matched}),
         "comparisons":matched,
         "skipped_reasons":dict(sorted(skip.items())),
         "partial_provider_board":provider.get("partial_board") is True,
         "source_coverage_complete":provider.get("complete_provider_board") is True,
         "note":"Real posted pick'em thresholds joined to independently published uncalibrated no-line AI forecasts. Not a validated bet, winning probability, or sportsbook quote."}

def main():
    def read(path):
        try:return json.loads(path.read_text()) if path.exists() else {}
        except (OSError,ValueError):return {}
    result=build(read(SOURCE),read(AI),read(FORM))
    OUT.write_text(json.dumps(result,separators=(",",":"),ensure_ascii=False)+"\n")
    health={
        "generated_at":result["generated_at"],
        "status":result["status"],
        "provider_generated_at":result["provider_generated_at"],
        "model_generated_at":result["model_generated_at"],
        "offers_matched":result["offers_matched"],
        "matched_games":result["matched_games"],
        "matched_by_game":dict(sorted(__import__("collections").Counter(
            row["game"] for row in result["comparisons"]).items())),
        "partial_provider_board":result.get("partial_provider_board"),
        "source_coverage_complete":result.get("source_coverage_complete"),
        "research_only":True,
        "calibrated_hit_probability_available":False,
        "skipped_reasons":result["skipped_reasons"],
        "large_file":"docs/ai_prizepicks_quick_join.json",
    }
    HEALTH.write_text(json.dumps(health,indent=2)+"\n")
    print("QUICK PP × AI:",result["status"],
          "matches:",result["offers_matched"],
          "games:",result["matched_games"])
    if result["status"] in ("UNAVAILABLE_INPUTS","STALE_OR_UNVERIFIED_SOURCE"):
        raise SystemExit(2)

if __name__=="__main__":
    main()
