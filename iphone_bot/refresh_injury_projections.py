"""Cheap official-injury refresh for already trained *upcoming* NBA AI props.

Do not call paid odds APIs or retrain models. Recompute pregame projections
from archived pre-injury model forecasts and verified prior-game on/off
evidence; never rescale an already adjusted output a second time. Preserve
original predictions in immutable paper ledgers. Hide injured/unverifiable
new picks rather than show stale projected numbers as current.
"""
import json
import copy
from datetime import datetime,timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from collections import defaultdict
from statistics import mean

try:
    from .paper_pick_pipeline import utc,expected_opponents
    from .research_context import injury_minutes_research
    from .matchup_context import team_allowances
    from .injury_projection_adjustment import (
        finite,teammate_minutes_ratio,opponent_defense_ratio,reproject)
except ImportError:
    from paper_pick_pipeline import utc,expected_opponents
    from research_context import injury_minutes_research
    from matchup_context import team_allowances
    from injury_projection_adjustment import (
        finite,teammate_minutes_ratio,opponent_defense_ratio,reproject)

ROOT=Path(__file__).resolve().parents[1]
BOARD=ROOT/"docs/ai_comparisons.json"
INJURIES=ROOT/"docs/injury_context.json"
GAMES=ROOT/"data/nba/current/current_games.json"
ET=ZoneInfo("America/New_York")

def material(player_id,team,day,by_id):
    hist=sorted((g for g in by_id.get(str(player_id),[])
                 if g.get("team")==team and str(g.get("date",""))<day),
                key=lambda x:x["date"])
    mins=[finite(g.get("MIN")) for g in hist[-5:]]
    usable=[n for n in mins if n is not None and 0<n<=60]
    return len(usable)>=3 and mean(usable)>=22

def refresh(board,injuries,games,now):
    now=utc(now)
    if board.get("status")!="EXPERIMENTAL_NON_CALIBRATED" or not board.get("verified_current_matchups"):
        raise ValueError("No identity-verified original trained board")
    if injuries.get("status")!="OFFICIAL_NBA_REPORT_VERIFIED" or injuries.get("injury_data_verified") is not True:
        return board,{"status":"NO_OFFICIAL_REPORT_NO_CHANGES"}
    issued=utc(injuries["report_issued_at"])
    if not 0<=(now-issued).total_seconds()<=18*3600:
        return board,{"status":"STALE_OR_FUTURE_REPORT_NO_CHANGES"}
    if board.get("injury_report_issued_at")==issued.isoformat():
        return board,{"status":"SAME_OFFICIAL_REPORT_ALREADY_APPLIED"}
    generated=utc(board["generated_at"])
    if not 0<=(now-generated).total_seconds()<=8*3600:
        return board,{"status":"STALE_OR_FUTURE_SPORTSBOOK_BOARD_NO_CHANGES"}
    by_id=defaultdict(list)
    for g in games:
        if g.get("id") is not None:by_id[str(g["id"])].append(g)
    official=defaultdict(list)
    for p in injuries.get("players",[]):
        if not isinstance(p,dict):continue
        if p.get("game_date") and p.get("player_id") and p.get("team"):
            official[(str(p["player_id"]),str(p["game_date"]))].append(p)
    cache={}
    kept=[]
    excluded=[]
    counts=defaultdict(int)
    # Keep suppressed offers outside the visible board so a later official
    # AVAILABLE update can restore them without inventing a new market line.
    candidates=board.get("comparisons",[])+board.get("injury_excluded_comparisons",[])
    seen=set()
    for source in candidates:
        ident=(str(source.get("player_id")),str(source.get("start")),
               str(source.get("stat")),str(source.get("line")),
               str(source.get("sportsbook")))
        if ident in seen:continue
        seen.add(ident)
        row=copy.deepcopy(source)
        try:
            start=utc(row["start"])
            if start<=now:
                kept.append(row);continue
            day=start.astimezone(ET).date().isoformat()
            team=str(row["team"]);pid=str(row["player_id"]);market=str(row["stat"])
            opposing=expected_opponents(row["game"],team)
            if len(opposing)!=1:kept.append(row);continue
            opponent=next(iter(opposing))
            def status(player_id,team_code):
                statuses={str(p.get("status","")).upper()
                          for p in official.get((str(player_id),day),[])
                          if p.get("team")==team_code}
                return statuses.pop() if len(statuses)==1 else None
            if status(pid,team) in ("OUT","DOUBTFUL"):
                counts["ruled_out_player_removed"]+=1
                excluded.append(row)
                continue
            out_team=[]
            out_opp=[]
            for (oid,odate),entries in official.items():
                if odate!=day:continue
                if status(oid,team)=="OUT" and oid!=pid and material(oid,team,day,by_id):
                    out_team.append({"player_id":oid,"player":entries[0].get("player","")})
                if status(oid,opponent)=="OUT" and material(oid,opponent,day,by_id):
                    out_opp.append({"player_id":oid,"player":entries[0].get("player","")})
            # An earlier injury adjustment must always be undone before new
            # game-day information is applied. Never compound post-tip values.
            original=finite(row.get("preinjury_original_projection"))
            if original is None:original=finite(row.get("projection"))
            base_shadow=finite(row.get("preinjury_shadow_projection"))
            if "preinjury_shadow_projection" not in row:
                base_shadow=finite(row.get("shadow_projection"))
            if original is None:counts["invalid_baseline"]+=1;continue
            row["preinjury_original_projection"]=original
            row["preinjury_shadow_projection"]=base_shadow
            row["preinjury_combined_projection"]=round(
                (original+base_shadow)/2 if base_shadow is not None else original,1)
            row["official_out_teammates"]=out_team
            row["official_out_opponents"]=out_opp
            if out_team or out_opp:
                history=sorted([g for g in by_id.get(pid,[])
                    if g.get("team")==team and str(g.get("date",""))<day],
                    key=lambda g:g["date"])
                scenario=injury_minutes_research(history,games,day,team,
                    [{"player_id":o["player_id"],"player":o["player"],"team":team} for o in out_team])
                team_ratio=teammate_minutes_ratio(scenario,len(out_team))
                if day not in cache:cache[day]=team_allowances(games,day)
                opp_ratio=opponent_defense_ratio(
                    cache[day],opponent,[o["player_id"] for o in out_opp],
                    games,day,market)
                updated=reproject(original,base_shadow,team_ratio,opp_ratio)
                if updated is None:
                    counts["unsupported_injury_pick_removed"]+=1
                    excluded.append(row)
                    continue
                row.update(projection=round(updated["original"],1),
                    shadow_projection=round(updated["opponent"],1) if updated["opponent"] is not None else None,
                    combined_projection=round(updated["combined"],1),
                    injury_reprojection_status="REPROJECTED_FROM_VERIFIED_OFFICIAL_OUT",
                    injury_scenario_applied_to_combined=True,
                    lineup_research_adjustment_applied=True,
                    injury_reprojection_factor=updated["factor"],
                    injury_scenario_projection=round(updated["combined"],1),
                    injury_minutes_research=scenario)
                row["projection_explanation"]={"sentences":[
                    "Updated for NBA official game-day OUT status: "+
                    ", ".join(p["player"] for p in out_team+out_opp)+".",
                    "Revised forecast: "+str(round(updated["combined"],1))+
                    " versus pre-injury "+str(row["preinjury_combined_projection"])+
                    ". This uses strictly earlier teammate minutes or opponent defensive totals.",
                    "Injury-conditional historical adjustment is unvalidated; previously published probability estimates are withheld."
                ]}
                counts["reprojected"]+=1
            else:
                row.update(projection=round(original,1),
                    shadow_projection=round(base_shadow,1) if base_shadow is not None else None,
                    combined_projection=row["preinjury_combined_projection"],
                    injury_reprojection_status="NO_OFFICIAL_OUT_IN_MATCHUP",
                    injury_scenario_applied_to_combined=False,
                    lineup_research_adjustment_applied=False,
                    injury_scenario_projection=None)
                counts["baseline_or_restored"]+=1
            projected=float(row["combined_projection"])
            row["combined_difference"]=round(projected-float(row["line"]),1)
            if row.get("shadow_projection") is not None:
                row["shadow_difference"]=round(float(row["shadow_projection"])-float(row["line"]),1)
            else:
                row["shadow_difference"]=None
            row["difference"]=round(float(row["projection"])-float(row["line"]),1)
            row["combined_direction"]="Over" if projected>row["line"] else "Under" if projected<row["line"] else "Neutral"
            row["lean"]="Over" if row["difference"]>0 else "Under" if row["difference"]<0 else "Neutral"
            row["injury_context_requires_reprojection"]=bool(out_team or out_opp)
            row["injury_reprojection_at"]=now.isoformat()
            # Historical residual probabilities and experimental EV were
            # computed against the original uninjured model. No calibrated
            # replacement can be obtained without retraining; do not reuse.
            for field in ("estimated_over_probability","estimated_under_probability",
                          "estimated_push_probability","estimated_selected_probability",
                          "estimated_probability_side"):
                row[field]=None
            row["probability_method"]="WITHHELD_AFTER_UPDATED_INJURY_CONTEXT"
            row["experimental_ev_available"]=False
            row["experimental_best_quote"]=None
            row["ev_status"]="REQUIRES_UPDATED_MODEL_RESIDUALS"
            for quote in row.get("book_quotes",[]):
                if isinstance(quote,dict):
                    for field in list(quote):
                        if field.startswith("hypothetical_") or field.endswith("_model_probability"):
                            quote.pop(field,None)
            kept.append(row)
        except (KeyError,ValueError,TypeError,OverflowError):
            counts["invalid_row_removed"]+=1
    updated=dict(board)
    updated["comparisons"]=kept
    updated["injury_excluded_comparisons"]=excluded
    updated["injury_suppressed_offer_count"]=len(excluded)
    updated["games_with_ai_props"]=len({r["game"] for r in kept if utc(r["start"])>now})
    updated["comparison_rows_published"]=len(kept)
    updated["comparison_rows_truncated"]=0
    updated["lineup_research_adjustments_applied"]=any(
        r.get("injury_scenario_applied_to_combined") is True for r in kept)
    updated["injury_context_source"]="OFFICIAL_NBA_REPORT_VERIFIED"
    updated["injury_data_verified"]=True
    updated["injury_refreshed_at"]=now.isoformat()
    updated["injury_report_issued_at"]=issued.isoformat()
    updated["injury_reprojection_counts"]=dict(counts)
    return updated,{"status":"REFRESHED_WITH_OFFICIAL_INJURY_REPORT",**counts}

def main():
    if not BOARD.exists() or not INJURIES.exists():return
    original=json.loads(BOARD.read_text())
    injuries=json.loads(INJURIES.read_text())
    games=json.loads(GAMES.read_text()) if GAMES.exists() else []
    updated,report=refresh(original,injuries,games,datetime.now(timezone.utc))
    print("INJURY LIVE AI REFRESH:",json.dumps(report,sort_keys=True),flush=True)
    if report["status"]=="REFRESHED_WITH_OFFICIAL_INJURY_REPORT" and updated!=original:
        BOARD.write_text(json.dumps(updated,indent=2)+"\n")

if __name__=="__main__":
    main()
