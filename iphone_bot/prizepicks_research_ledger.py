"""Freeze and grade independent PrizePicks AI research against completed player logs.

Separate from paid sportsbook ledger. Only pre-tip snapshots already published
and time-stamped before an NBA matchup are eligible. No imagined prices, no
retrospective changes to forecasts, no false ROI or hit probabilities.
"""
import json
from datetime import datetime, timezone
from pathlib import Path
from iphone_bot.verified_nov9_nonparticipants import SOURCE as CROSSCHECKED_DNP_SOURCE
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"docs/prizepicks_ai_research.json"
LEDGER=ROOT/"docs/prizepicks_research_ledger.json"
RESULTS=ROOT/"docs/prizepicks_research_results.json"
CURRENT=ROOT/"data/nba/current/current_games.json"
OFFICIAL=ROOT/"data/nba/current/prizepicks_verified_final_games.json"
SUPPORTED=("PTS","REB","AST","PRA")

def utc(s):
    try:
        v=datetime.fromisoformat(str(s).replace("Z","+00:00"))
        return v.astimezone(timezone.utc) if v.tzinfo is not None else None
    except (ValueError,TypeError):return None

def identity(row):
    return "|".join(str(row.get(k,"")) for k in (
        "provider_projection_id","player_id","team","game","start","stat","line"))

def freeze(existing,source):
    records={identity(x):x for x in existing.get("records",[]) if identity(x)}
    added=0
    snapshot=utc(source.get("generated_at"))
    if source.get("status")!="PRIZEPICKS_AI_RESEARCH_ONLY_NOT_SPORTSBOOK_ODDS" or not snapshot:
        return {"records":list(records.values()),"new":0}
    for row in source.get("comparisons",[]):
        start=utc(row.get("start"))
        captured=utc(row.get("captured_at"))
        if not start or not captured or start<=snapshot or start<=captured:continue
        try:
            fields=("provider_projection_id","player_id","player","team","game",
                    "start","stat","line","combined_projection","original_projection")
            if any(row.get(x) in (None,"") for x in fields):continue
            if row["stat"] not in SUPPORTED or len(str(row["team"]))!=3:continue
            if not 0<=float(row["line"])<300:continue
            if not 0<=float(row["combined_projection"])<300:continue
            if not 0<=float(row["original_projection"])<300:continue
            stored={k:row.get(k) for k in fields}
            stored.update({
                "opponent_aware_projection":row.get("opponent_aware_projection"),
                "minutes_v3_research":row.get("minutes_v3_research"),
                "opportunity_v2_research":row.get("opportunity_v2_research")
                    if row.get("stat") in ("AST","REB") else None,
                "minutes_v2_research_baseline":row.get("minutes_v2_research_baseline"),
                "observed_at":row.get("observed_at"),
                # Only capture a provider-explicit two-sided tier at pretip.
                # The source's missing side metadata is not proof of standard.
                "line_tier":(row.get("more_tier") if row.get("more_tier") in
                    ("standard","goblin","demon") and
                    row.get("more_tier")==row.get("less_tier") else None),
                "line_tier_verified":bool(row.get("more_tier") in
                    ("standard","goblin","demon") and
                    row.get("more_tier")==row.get("less_tier") and
                    row.get("source")=="independent_prizepicksapi_com"),
                "captured_at":row["captured_at"],
                "snapshot_generated_at":source["generated_at"],
                "source":"PUBLISHED_PRETIP_PRIZEPICKS_AI_RESEARCH",
                "status":"PENDING",
                "actual":None,"result":None,
                "settlement_source":None,
                "not_sportsbook_odds":True,"verified_ev":False})
            key=identity(stored)
            if key not in records:
                records[key]=stored
                added+=1
        except (TypeError,ValueError):continue
    return {"records":list(records.values()),"new":added}

def settle(ledger,games,now=None,final_games=None):
    now=now or datetime.now(timezone.utc)
    games_by={}
    for g in games:
        try:
            player=str(g.get("id") or g.get("player_id"))
            team=str(g["team"]).upper()
            date=str(g["date"])
            if not player or not team or not date:continue
            key=(player,team,date)
            if key in games_by and games_by[key]!=g:
                games_by[key]=None
            elif key not in games_by:games_by[key]=g
        except (KeyError,TypeError):continue
    # Official final boxscores lack the CSV provider's player ID. Match by
    # COMPLETE normalized name + team + Eastern date + exact opponent, only
    # for independently verified final sources. Ambiguity is never graded.
    try:
        from .paper_pick_pipeline import strict_player_name, expected_opponents
    except ImportError:
        from paper_pick_pipeline import strict_player_name, expected_opponents
    official_by_name={}
    for g in (final_games or []):
        if (g.get("final_confirmed") is not True or
            g.get("source") not in ("NBA_CDN_FINAL","ESPN_FINAL",
                                     "NBA_OFFICIAL_INACTIVE_CROSSCHECKED",CROSSCHECKED_DNP_SOURCE)):
            continue
        k=(strict_player_name(g.get("player")),str(g.get("team","")).upper(),
           str(g.get("date")),str(g.get("opponent","")).upper())
        if not all(k):continue
        if k in official_by_name:
            official_by_name[k]=None
        else:
            official_by_name[k]=g
    out=[]
    for record in ledger.get("records",[]):
        row=dict(record)
        if row.get("status")=="SETTLED":
            out.append(row)
            continue
        if row.get("status")!="PENDING":
            out.append(row)
            continue
        start=utc(row.get("start"))
        if not start or now<start:
            out.append(row)
            continue
        date=start.astimezone(ZoneInfo("America/New_York")).date().isoformat()
        actual_row=games_by.get((str(row.get("player_id")),str(row.get("team")).upper(),date))
        expected=expected_opponents(row.get("game"),row.get("team"))
        if not expected:
            out.append(row)
            continue
        if not actual_row:
            k=(strict_player_name(row.get("player")),str(row.get("team","")).upper(),
               date,expected[0])
            actual_row=official_by_name.get(k)
        if not actual_row:
            out.append(row)
            continue
        # A recorded final non-participant is a verified VOID, never an UNDER.
        # Do not infer DNP just because a name is missing from the boxscore.
        if actual_row.get("dnp_final_verified") is True:
            if (actual_row.get("final_confirmed") is True and
                actual_row.get("source") in ("NBA_CDN_FINAL","ESPN_FINAL",
                                              "NBA_OFFICIAL_INACTIVE_CROSSCHECKED",CROSSCHECKED_DNP_SOURCE) and
                str(actual_row.get("opponent","")).upper() in expected and
                actual_row.get("dnp_reason")):
                row.update(status="VOID_DNP",result="VOID",actual=None,
                           settlement_source=actual_row["source"],
                           settled_game_date=date,
                           dnp_reason=actual_row["dnp_reason"])
            out.append(row)
            continue
        # Manually crosschecked evidence may ONLY void verified DNPs. It can
        # never supply played points/rebounds/assists or an apparent WIN/LOSS.
        if actual_row.get("source") in ("NBA_OFFICIAL_INACTIVE_CROSSCHECKED",CROSSCHECKED_DNP_SOURCE):
            out.append(row)
            continue
        # Verify the actual opponent matches the original, exact scheduled game.
        if not expected or str(actual_row.get("opponent","")).upper() not in expected:
            out.append(row)
            continue
        try:
            value=float(actual_row[row["stat"]])
            if not 0<=value<300:raise ValueError
            line=float(row["line"])
            prediction=float(row["combined_projection"])
        except (KeyError,TypeError,ValueError):
            out.append(row)
            continue
        result="PUSH" if value==line else (
            "WIN" if (prediction>line and value>line) or
                     (prediction<line and value<line) else
            "LOSS" if prediction!=line else "NO_LEAN")
        row.update(status="SETTLED",actual=value,result=result,
                   settlement_source=(actual_row.get("source") if actual_row.get("final_confirmed") is True
                                      else "HISTORICAL_CSV_COMPLETED_GAME"),
                   settled_game_date=date,
                   actual_minutes=float(actual_row["MIN"])
                      if actual_row.get("MIN") is not None and
                         0<float(actual_row["MIN"])<=60 else None)
        out.append(row)
    return {"records":out}

def _quote_tier(row, quote_index):
    """Only original explicit, price-specific provider metadata proves tier.

    A middle/median threshold does NOT establish a standard PrizePicks line.
    Previously frozen rows without metadata may be corroborated against the
    immutable, pretip provider quote archive by exact projection ID, fixture,
    start, team, market and threshold. Unknown or conflicting tiers stay out.
    """
    tier=row.get("line_tier")
    if tier in ("standard","goblin","demon") and row.get("line_tier_verified") is True:
        return tier
    if quote_index is None:
        return None
    quote=quote_index.get(str(row.get("provider_projection_id") or ""))
    if not isinstance(quote,dict):
        return None
    if any(str(row.get(k) or "")!=str(quote.get(k) or "")
           for k in ("player","team","game","stat")):
        return None
    try:
        if float(row["line"])!=float(quote["line"]) or (
            str(row.get("start") or "")!=str(quote.get("starts_at") or "")):
            return None
        observed=utc(quote.get("observed_at"))
        published=utc(quote.get("source_generated_at"))
        start=utc(row.get("start"))
        captured=utc(row.get("captured_at"))
        if not all((observed,published,start,captured)):
            return None
        # Only evidence available when the pick was actually frozen can
        # establish the tier. A quote published afterward is not a safe
        # retroactive standard-line label.
        if not (observed<=published<=captured<start):
            return None
    except (TypeError,ValueError):
        return None
    if (quote.get("source")!="independent_prizepicksapi_com" or
        quote.get("is_demo") is not False):
        return None
    tier=quote.get("tier")
    if tier not in ("standard","goblin","demon"):
        return None
    # A mixed or disputed side cannot safely be called a standard line.
    if quote.get("more_tier")!=tier or quote.get("less_tier")!=tier:
        return None
    return tier

def verified_quote_index(source):
    """Do not trust a projection ID with conflicting archive metadata."""
    result={}
    conflicted=set()
    if source.get("status")!="VERIFIED_PRETIP_PRIZEPICKS_QUOTES_ARCHIVE":
        return result
    for q in source.get("quotes",[]):
        if not isinstance(q,dict) or not q.get("id"):
            continue
        key=str(q["id"])
        if key in result and result[key]!=q:
            conflicted.add(key)
        else:
            result[key]=q
    for key in conflicted:result.pop(key,None)
    return result

def paired_joint_metrics(representatives):
    """Independent representative PrizePicks markets, exact original frozen forecast."""
    out={}
    for stat in ("AST","REB"):
        eligible=[]
        for row in representatives:
            if row.get("stat")!=stat or row.get("status")!="SETTLED":
                continue
            shadow=row.get("opportunity_v2_research")
            point=(shadow.get("markets") or {}).get(stat,{}) if isinstance(shadow,dict) else {}
            mins=row.get("minutes_v3_research")
            if (not isinstance(mins,dict) or
                point.get("status")!="PREGAME_OPPORTUNITY_V2_RESEARCH"):
                continue
            day=row.get("settled_game_date")
            if not day or (point.get("last_prior_game") or "9999")>=day or (mins.get("last_prior_date") or "9999")>=day:
                continue
            try:
                actual=float(row["actual"]);old=float(row["combined_projection"])
                new=float(point["projection"]);line=float(row["line"])
                if not all(__import__("math").isfinite(x) for x in (actual,old,new,line)):
                    continue
            except (TypeError,KeyError,ValueError):
                continue
            eligible.append((row,actual,old,new,line))
        n=len(eligible)
        all_direction=[x for x in eligible if x[1]!=x[4] and x[2]!=x[4] and x[3]!=x[4]]
        out[stat]={"paired":n,
            "distinct_game_dates":len({x[0].get("settled_game_date") for x in eligible}),
            "baseline_mae":round(sum(abs(x[1]-x[2]) for x in eligible)/n,4) if n else None,
            "challenger_mae":round(sum(abs(x[1]-x[3]) for x in eligible)/n,4) if n else None,
            "paired_direction_grades":len(all_direction),
            "baseline_wins":sum((x[2]>x[4])==(x[1]>x[4]) for x in all_direction),
            "challenger_wins":sum((x[3]>x[4])==(x[1]>x[4]) for x in all_direction),
            "tracked_chances_samples":sum(x[0]["opportunity_v2_research"]["markets"][stat].get("source_kind")=="OBSERVED_TRACKING_CHANCES_CONVERTED" for x in eligible),
            "production_applied":False}
    return {"status":"PRETIP_FROZEN_PRIZEPICKS_JOINT_RESEARCH_ONLY",
        "by_market":out,"verified_edge":False,
        "note":"No payoff/ROI inferred; paired observations only and alternate thresholds are not counted as independent."}

def summarize(ledger,now=None,quote_archive=None):
    now=now or datetime.now(timezone.utc)
    rows=ledger.get("records",[])
    settled=[r for r in rows if r.get("status")=="SETTLED"]
    eligible=[r for r in settled if r.get("result") in ("WIN","LOSS")]
    all_tier_research_by_market={}
    for stat in SUPPORTED:
        group=[r for r in eligible if r.get("stat")==stat]
        all_tier_research_by_market[stat]={
            "graded_lines":len(group),"wins":sum(r["result"]=="WIN" for r in group),
            "line_hit_rate":round(sum(r["result"]=="WIN" for r in group)/len(group),4) if group else None,
            "distinct_game_dates":len({r.get("settled_game_date") for r in group}),
            "scope":"ALL_TIERS_EXPLORATORY_NOT_OFFICIAL_HIT_RATE"}
    # OFFICIAL STANDARD ONLY: one original, source-verified standard quote per
    # player/game/market. A median of goblin/demon thresholds is never a
    # standard line. Conflicting standard quotes fail closed as ambiguous.
    quote_index=verified_quote_index(quote_archive or {})
    groups={}
    tier_counts={"standard":0,"goblin":0,"demon":0,"unverified":0}
    for row in rows:
        tier=_quote_tier(row,quote_index)
        tier_counts[tier or "unverified"]+=1
        if tier!="standard":continue
        key=(row.get("player_id"),row.get("team"),row.get("game"),
             row.get("start"),row.get("stat"))
        groups.setdefault(key,[]).append(row)
    representatives=[]
    ambiguous_groups=0
    for group in groups.values():
        # Follow the predetermined last pretip standard quote rule, not the
        # most favorable settled result. The quote is chosen independently
        # of actual values and is consistent with NFL frozen standard lines.
        # Simultaneous conflicting standard thresholds are untrustworthy.
        latest=max(str(r.get("captured_at") or "") for r in group)
        chosen=[r for r in group if str(r.get("captured_at") or "")==latest]
        if len({float(r["line"]) for r in chosen})!=1:
            ambiguous_groups+=1
            continue
        representatives.append(min(chosen,key=lambda r:str(r.get("provider_projection_id") or "")))
    independent={}
    for stat in SUPPORTED:
        sample=[r for r in representatives
                if r.get("stat")==stat and r.get("status")=="SETTLED"
                and r.get("result") in ("WIN","LOSS")]
        wins=sum(r["result"]=="WIN" for r in sample)
        independent[stat]={"graded":len(sample),"wins":wins,
                           "losses":len(sample)-wins,
                           "hit_rate":round(wins/len(sample),4) if sample else None,
                           "distinct_game_dates":len({r.get("settled_game_date") for r in sample})}
    return {"status":"PRIZEPICKS_PRETIP_RESEARCH_GRADED_NOT_ODDS",
            "updated_at":now.isoformat(),"saved":len(rows),
            "settled":len(settled),"void_dnp":sum(r.get("status")=="VOID_DNP" for r in rows),
            "pending":sum(r.get("status")=="PENDING" for r in rows),
            "independent_player_market_count":len(representatives),
            "verified_quote_tier_counts":tier_counts,
            "ambiguous_standard_line_markets_excluded":ambiguous_groups,
            "official_grading_scope":"VERIFIED_PRETIP_STANDARD_LINES_ONLY",
            "independent_settled_center_lines":sum(v["graded"] for v in independent.values()),
            "independent_settled_standard_lines":sum(v["graded"] for v in independent.values()),
            "independent_by_market":independent,
            "minutes_v3_opportunity_v2_paired":paired_joint_metrics(representatives),
            "by_market":{stat:{"graded_lines":item["graded"],
                "wins":item["wins"],"line_hit_rate":item["hit_rate"],
                "distinct_game_dates":item["distinct_game_dates"]}
                for stat,item in independent.items()},
            "all_tiers_research_by_market":all_tier_research_by_market,
            "wager_roi":None,"verified_ev":False,
            "selection_method":"EXPLICIT_VERIFIED_STANDARD_TIER_ONLY_NO_MEDIAN_FALLBACK",
            "notice":"Only explicit source-verified standard PrizePicks tiers count toward official independent hit rates. Demon, goblin, unknown-tier, and ambiguous records are excluded from hit-rate denominators. All frozen quote outcomes remain in a separate archival research ledger."}

def main():
    old=json.loads(LEDGER.read_text()) if LEDGER.exists() else {"records":[]}
    source=json.loads(SOURCE.read_text()) if SOURCE.exists() else {}
    frozen=freeze(old,source)
    games=json.loads(CURRENT.read_text()) if CURRENT.exists() else []
    official=json.loads(OFFICIAL.read_text()) if OFFICIAL.exists() else []
    graded=settle(frozen,games,final_games=official)
    archive_path=ROOT/"docs/prizepicks_pregame_line_archive.json"
    archive=json.loads(archive_path.read_text()) if archive_path.exists() else {}
    report=summarize(graded,quote_archive=archive)
    previous=json.loads(RESULTS.read_text()) if RESULTS.exists() else {}
    def unchanged_except_timestamp(entry):
        return {k:v for k,v in entry.items() if k!="updated_at"}
    if (graded["records"]==old.get("records",[]) and LEDGER.exists() and
        unchanged_except_timestamp(previous)==unchanged_except_timestamp(report)):
        print("PrizePicks research ledger and explicit standard-only metrics unchanged")
        return
    graded["updated_at"]=datetime.now(timezone.utc).isoformat()
    LEDGER.parent.mkdir(parents=True,exist_ok=True)
    LEDGER.write_text(json.dumps(graded,indent=2)+"\n")
    RESULTS.write_text(json.dumps(report,indent=2)+"\n")
    print("PrizePicks research ledger:",len(graded["records"]),
          "new:",frozen["new"],"settled:",
          sum(r.get("status")=="SETTLED" for r in graded["records"]))
if __name__=="__main__":main()
