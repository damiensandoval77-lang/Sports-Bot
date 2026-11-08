"""Research-only opportunity, injury, defender V4 and 20k-simulation validation.

All snapshots are captured before tipoff and immutable. A same-game injury
status must be sourced from a report published before the prediction and
matching the event date. No fresh 2026-27 defender matchups are implied by a
2025-26 research archive. This file NEVER modifies a live projection or a
displayed probability.
"""
import hashlib
import json
import math
import random
from collections import Counter,defaultdict
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
from pathlib import Path

try:
    from .paper_pick_pipeline import utc
except ImportError:
    from paper_pick_pipeline import utc

try:
    from .opportunity_backtest import histories as opportunity_histories,opportunity as opportunity_forecast,candidate as opportunity_candidate,stability_candidate as stability_opportunity_candidate
except ImportError:
    from opportunity_backtest import histories as opportunity_histories,opportunity as opportunity_forecast,candidate as opportunity_candidate,stability_candidate as stability_opportunity_candidate

try:
    from .selection_gate_shadow import pregame_gate
except ImportError:
    from selection_gate_shadow import pregame_gate

try:
    from .assist_shadow_v1 import assist_shadow
except ImportError:
    from assist_shadow_v1 import assist_shadow

try:
    from .sanity_shadow_research import shadow as sanity_shadow
except ImportError:
    from sanity_shadow_research import shadow as sanity_shadow

try:
    from .stress_test_20k_research import check as stress_check
except ImportError:
    from stress_test_20k_research import check as stress_check

try:
    from .model_disagreement_research import detect as disagreement_detect,report as disagreement_report
except ImportError:
    from model_disagreement_research import detect as disagreement_detect,report as disagreement_report

try:
    from .unified_reliability_research import view as unified_reliability_view
except ImportError:
    from unified_reliability_research import view as unified_reliability_view

try:
    from .prospective_research_gate import verify as verify_prospective_capture
except ImportError:
    from prospective_research_gate import verify as verify_prospective_capture

try:
    from .lineup_onoff_research import evaluate as licensed_onoff_evaluate
except ImportError:
    from lineup_onoff_research import evaluate as licensed_onoff_evaluate

try:
    from .rebound_shadow_v1 import forecast as rebound_opportunity_v1
except ImportError:
    from rebound_shadow_v1 import forecast as rebound_opportunity_v1

try:
    from .tracking_opportunities_v1 import evaluate as tracking_opportunity_evaluate
except ImportError:
    from tracking_opportunities_v1 import evaluate as tracking_opportunity_evaluate

try:
    from .opponent_context_v2 import games_by_team as opponent_team_games, matchup as opponent_matchup, shadow as opponent_v2_shadow
    from .paper_pick_pipeline import expected_opponents
except ImportError:
    from opponent_context_v2 import games_by_team as opponent_team_games, matchup as opponent_matchup, shadow as opponent_v2_shadow
    from paper_pick_pipeline import expected_opponents

ROOT=Path(__file__).resolve().parents[1]
BOARD=ROOT/"docs/ai_comparisons.json"
INJURY=ROOT/"docs/injury_context.json"
PAPER=ROOT/"docs/paper_pick_ledger.json"
LEDGER=ROOT/"docs/projection_upgrade_ledger.json"
STATUS=ROOT/"docs/projection_upgrade_status.json"
ONOFF=ROOT/"docs/lineup_onoff_research.json"
PRIVATE_ONOFF=ROOT/"data/nba/private/lineup_onoff_research.json"
PRIVATE_TRACKING=ROOT/"data/nba/private/tracking_opportunities.json"
MARKETS=("PTS","REB","AST","PRA")
MIN_RESIDUALS=1000
SIMULATIONS=20000
SOURCE="RESEARCH_ONLY_PREGAME_LOCKED_CONDITIONAL_PROJECTIONS"


def valid(value):
    if value is None or isinstance(value,bool):return None
    try:
        n=float(value)
        return n if math.isfinite(n) and n>=0 else None
    except (ValueError,TypeError):return None


def identity(row):
    return "|".join((utc(row["event_start"]).isoformat(),
            str(row["player_id"]),str(row["market"]),
            format(float(row["line"]),".10g")))


def official_injuries(feed,game_start,capture):
    """Only event-day, earlier-issued, verified official NBA statuses."""
    if feed.get("status")!="OFFICIAL_NBA_REPORT_VERIFIED" or feed.get("injury_data_verified") is not True:
        return [],"UNVERIFIED_REPORT"
    try:
        issued=utc(feed["report_issued_at"])
        generated=utc(feed["generated_at"])
        if issued>capture or generated>capture:return [],"FUTURE_INJURY_REPORT"
        if (capture-issued).total_seconds()>24*3600:return [],"STALE_INJURY_REPORT"
    except (ValueError,KeyError,TypeError):
        return [],"UNVERIFIED_REPORT_DATE"
    # NBA injury rows must explicitly carry the calendar date of the game.
    game_day=game_start.astimezone(ZoneInfo("America/New_York")).date().isoformat()
    rows=[p for p in feed.get("players",[]) if p.get("game_date")==game_day
          and str(p.get("status","")).lower() in
          ("out","doubtful","questionable","probable","available")]
    return rows,"OFFICIAL_SAME_DAY_VERIFIED" if rows else "NO_SAME_DAY_PLAYER_STATUS"


def snapshot(board,injury,existing,at,game_history=None,onoff_feed=None,tracking_feed=None):
    captured=utc(at)
    if board.get("status")!="EXPERIMENTAL_NON_CALIBRATED" or board.get("verified_current_matchups") is not True:
        raise ValueError("Board not verified")
    age=(captured-utc(board["generated_at"])).total_seconds()
    if age<0 or age>45*60:raise ValueError("Board must be captured within 45 minutes of generation")
    old=list(existing)
    seen={identity(r) for r in old}
    counters=Counter()
    indexed=opportunity_histories(game_history or [])
    team_context_by_date={}
    for item in board.get("comparisons",[]):
        try:
            if item.get("stat") not in MARKETS:continue
            start=utc(item["start"])
            if start<=captured:continue
            pid=str(item["player_id"])
            original=valid(item.get("projection"))
            combined=valid(item.get("combined_projection"))
            line=valid(item.get("line"))
            if original is None or combined is None or line is None:continue
            row={"event_start":start.isoformat(),"captured_at":captured.isoformat(),
                 "player_id":pid,"player":str(item.get("player","")),
                 "team":str(item.get("team","")),
                 "game":str(item.get("game","")),
                 "market":item["stat"],"line":line,
                 "original_projection":original,
                 "combined_projection":combined,
                 "source":SOURCE,
                 "v4_shadow_projection":None,
                 "v4_shadow_status":"AWAITING_VERIFIED_2026_27_DEFENDER_ROTATIONS",
                 "applied_to_live_ai":False,"simulated_probability_modified":False}
            k=identity(row)
            if k in seen:continue
            # True forward shadow prediction: all feature rows are known
            # completed games strictly before this event's Eastern date.
            day=start.astimezone(ZoneInfo("America/New_York")).date().isoformat()
            opp=opportunity_forecast(indexed.get((pid,row["team"]),[]),day,row["team"])
            frozen=(opportunity_candidate(combined,opp["raw_stat_projections"][row["market"]])
                    if opp["status"]=="HISTORICAL_OPPORTUNITY_CANDIDATE" else None)
            row["assist_shadow"]=(
                assist_shadow(indexed.get((pid,row["team"]),[]),
                    day,row["team"],combined,opp.get("expected_minutes"))
                if item["stat"]=="AST"
                else {"status":"NON_ASSIST_MARKET","projection":None,"live_applied":False})
            if row["assist_shadow"]["projection"] is not None:
                counters["assist_shadow_locked"]+=1
            row["rebound_shadow_v1"]=(
                rebound_opportunity_v1(indexed.get((pid,row["team"]),[]),
                    team=row["team"],event_date=day,baseline=combined,
                    expected_minutes=opp.get("expected_minutes"))
                if item["stat"]=="REB" else
                {"status":"NON_REBOUND_MARKET","projection":None,
                    "research_only":True,"live_applied":False})
            if row["rebound_shadow_v1"].get("projection") is not None:
                counters["rebound_shadow_v1_locked"]+=1
            # Opportunity tracking is not a substitute for real box scores.
            # Only provider-authorized, historical game-level chances count.
            row["tracking_opportunity_shadow"]=(
                tracking_opportunity_evaluate(tracking_feed,player_id=pid,
                    team=row["team"],market=row["market"],event_date=day,
                    baseline=combined,expected_minutes=opp.get("expected_minutes"),
                    captured_at=captured.isoformat())
                if row["market"] in ("AST","REB") else
                {"status":"NON_TRACKING_MARKET","projection":None,
                    "research_only":True,"live_applied":False})
            if row["tracking_opportunity_shadow"].get("projection") is not None:
                counters["tracking_opportunity_shadow_locked"]+=1
            row["opportunity_shadow_projection"]=frozen
            row["stability_opportunity_shadow_projection"]=(
                stability_opportunity_candidate(combined,opp["raw_stat_projections"][row["market"]],opp)
                if opp["status"]=="HISTORICAL_OPPORTUNITY_CANDIDATE" else None)
            row["stability_opportunity_method"]="FIXED_VOLATILITY_SHRINKAGE_RESEARCH_ONLY"
            if row["stability_opportunity_shadow_projection"] is not None:
                counters["stability_opportunity_shadow_locked"]+=1
            row["opportunity_shadow_status"]=("PREGAME_LOCKED_UNVALIDATED_CHALLENGER"
               if frozen is not None else "INSUFFICIENT_PAST_PLAYER_GAMES")
            row["opportunity_shadow_prior_games"]=opp["history_games"]
            row["opportunity_shadow_last_game"]=opp.get("prior_latest_game_date")
            row["opportunity_shadow_minutes"]=opp.get("expected_minutes")
            row["opportunity_shadow_method"]="FIXED_25PCT_BLEND_BOUNDED_15PCT"
            if frozen is not None:counters["opportunity_shadow_locked"]+=1
            # Historical research data only, not evidence of current assignments.
            minutes=item.get("minutes_research") or {}
            injury_minutes=item.get("injury_minutes_research") or {}
            shots=item.get("shot_profile_research") or {}
            estimated=valid(minutes.get("expected_minutes"))
            volume=valid(shots.get("expected_fga"))
            original_min=valid(minutes.get("observed_l5"))
            row["opportunity"]={"projected_minutes_unverified":estimated,
                "observed_last5_minutes":original_min,
                "expected_fga_unverified":volume,
                "minutes_delta_unverified":(
                    round(estimated-original_min,2)
                    if estimated is not None and original_min is not None else None),
                "source":"PREGAME_RECENT_PLAYER_GAMES_NOT_LINEUP_CONFIRMED"}
            all_statuses,status=official_injuries(injury,start,captured)
            opposite=expected_opponents(item.get("game"),row["team"])
            opponent_code=opposite[0] if len(opposite)==1 else None
            if day not in team_context_by_date:
                team_context_by_date[day]=opponent_team_games(game_history or [],day)
            out_ids=([str(p["player_id"]) for p in all_statuses
                if p.get("team")==opponent_code
                and str(p.get("status","")).upper()=="OUT" and p.get("player_id")]
                if status=="OFFICIAL_SAME_DAY_VERIFIED" else [])
            matchup_v2=(opponent_matchup(team_context_by_date[day],
                row["team"],opponent_code,row["market"],out_ids)
                if opponent_code is not None else
                {"status":"UNVERIFIED_MATCHUP","relative_factor":None,"research_only":True})
            row["opponent_v2_context"]=matchup_v2
            row["opponent_v2_shadow_projection"]=opponent_v2_shadow(combined,matchup_v2)
            if row["opponent_v2_shadow_projection"] is not None:
                counters["opponent_v2_shadow_locked"]+=1
            row["selection_gate"]=pregame_gate(
                item["stat"],line,combined,original,
                valid(item.get("shadow_projection")),
                [h for h in indexed.get((pid,row["team"]),[])
                 if h["date"]<day],
                opp,status)
            if row["selection_gate"]["eligible"]:
                counters["selection_gate_paper_eligible"]+=1
            else:
                counters["selection_gate_abstained"]+=1
            verified_player = next((p for p in all_statuses
                if str(p.get("player_id"))==pid
                and str(p.get("team"))==row["team"]
                and str(p.get("status","")).upper()=="AVAILABLE"),None)
            row["sanity_shadow_v1"]=sanity_shadow(
                indexed.get((pid,row["team"]),[]),team=row["team"],
                market=row["market"],baseline=combined,
                event_start=start,captured_at=captured,
                minutes_context=item.get("minutes_research"),
                injury_status="AVAILABLE" if verified_player else "NOT_VERIFIED",
                injury_source="OFFICIAL_NBA_REPORT" if verified_player and
                    status=="OFFICIAL_SAME_DAY_VERIFIED" else None)
            row["stress_test_20k_v1"]=stress_check(
                indexed.get((pid,row["team"]),[]),team=row["team"],
                market=row["market"],projection=combined,line=line,
                event_start=start,captured_at=captured,
                expected_minutes=(item.get("minutes_research") or {}).get("expected_minutes"),
                injury_status="AVAILABLE" if verified_player else "NOT_VERIFIED",
                injury_source="OFFICIAL_NBA_REPORT" if verified_player and
                    status=="OFFICIAL_SAME_DAY_VERIFIED" else None,
                player_id=pid)
            if row["stress_test_20k_v1"]["status"]=="CONDITIONAL_STRESS_RESEARCH_ONLY":
                counters["stress_scenarios_locked"]+=1
                if row["stress_test_20k_v1"]["fragile_high_confidence"]:
                    counters["stress_high_confidence_fragile"]+=1
            else:
                counters["stress_insufficient_inputs"]+=1
            sanity=row["sanity_shadow_v1"]
            row["model_disagreement_v1"]=disagreement_detect(
                market=row["market"],line=line,original=original,
                opponent=item.get("shadow_projection"),
                opponent_verified=item.get("shadow_status")=="RESEARCH_SHADOW_ONLY",
                combined=combined,sanity=sanity.get("shadow_projection"),
                sanity_status=sanity.get("status"))
            if row["model_disagreement_v1"]["status"]=="MODEL_DISAGREEMENT_REVIEW":
                counters["model_disagreement_review"]+=1
            elif row["model_disagreement_v1"]["status"]=="PARTIAL_MODEL_COVERAGE":
                counters["model_disagreement_partial"]+=1
            row["injury_report_status"]=status
            # Only teammates explicitly marked OUT with the correct verified
            # report game date may be used to label a conditional scenario.
            out_team=[p for p in all_statuses if
                str(p.get("team",""))==row["team"] and
                str(p.get("player_id",""))!=pid and
                str(p.get("status","")).lower()=="out"]
            row["verified_out_teammate_ids"]=sorted({str(p["player_id"]) for p in out_team})
            # Only official date-matched OUT player and licensed past-only split
            # can trigger a shadow. Never infer that an unlisted player is OUT.
            row["licensed_onoff_shadow"]={"status":"NO_SINGLE_VERIFIED_OUT_TEAMMATE",
                "projection":None,"research_only":True}
            if len(row["verified_out_teammate_ids"])==1:
                row["licensed_onoff_shadow"]=licensed_onoff_evaluate(
                    onoff_feed or {},
                    player_id=pid,team=row["team"],
                    teammate_id=row["verified_out_teammate_ids"][0],
                    market=row["market"],baseline=combined,
                    expected_minutes=(item.get("minutes_research") or {}).get("expected_minutes"),
                    game_start=start.isoformat(),captured_at=captured.isoformat())
                if row["licensed_onoff_shadow"]["projection"] is not None:
                    counters["licensed_onoff_shadow_locked"]+=1
            # These are *observed* historical teammate on/off production
            # splits already computed pregame; retain provenance and coverage,
            # not a fabricated causal boost or a same-day learned outcome.
            observed=[]
            for split in item.get("teammate_absence_splits",[]):
                if not isinstance(split,dict):continue
                with_count=split.get("with_games")
                without_count=split.get("without_games")
                if not isinstance(with_count,int) or not isinstance(without_count,int):continue
                if min(with_count,without_count)<3:continue
                observed.append({"status":"OBSERVED_NON_CAUSAL_SPLIT",
                    "teammate":split.get("teammate"),
                    "with_games":with_count,"without_games":without_count,
                    "with_avg":valid(split.get("with_avg")),
                    "without_avg":valid(split.get("without_avg"))})
            row["teammate_on_off_observed"]=observed
            if observed:counters["observed_teammate_on_off"]+=1
            scenario=valid(injury_minutes.get("scenario_minutes"))
            scenario_id=str(injury_minutes.get("teammate_id") or "")
            scenario_ok=(status=="OFFICIAL_SAME_DAY_VERIFIED" and
                injury_minutes.get("status")=="HISTORICAL_SCENARIO_RESEARCH_ONLY" and
                scenario_id in row["verified_out_teammate_ids"] and
                estimated is not None and estimated>0 and scenario is not None)
            # Fixed bounded research challenge: minutes-only exposure ratio.
            # Production Combined AI may already account for minutes; this is
            # evaluated as a separate candidate to detect double counting.
            # No gameplay, bookmaker line or actual score is used in the math.
            injury_candidate=(round(max(0,combined*
                max(.90,min(1.10,scenario/estimated))),3)
                if scenario_ok else None)
            row["injury_scenario"]={
                "status":"PREGAME_CONDITIONAL_NOT_CAUSAL" if scenario_ok
                         else "NO_VERIFIED_PREGAME_MINUTES_SCENARIO",
                "candidate_teammate_id":scenario_id if scenario_ok else None,
                "scenario_minutes":scenario if scenario_ok else None,
                "baseline_minutes":estimated,
                "scenario_points_projection":injury_candidate if item["stat"]=="PTS" else None,
                "scenario_market_projection":injury_candidate,
                "candidate_method":"BOUNDED_MINUTES_RATIO_RESEARCH_ONLY_NOT_CAUSAL",
                "research_only":True}
            # Never copy minutes directly into scoring model without a
            # validated usage/efficiency relationship for this market.
            if scenario_ok:counters["conditional_minutes_scenarios"]+=1
            if status=="OFFICIAL_SAME_DAY_VERIFIED":counters["official_report_matched"]+=1
            if volume is not None:counters["shot_opportunity_available"]+=1
            if estimated is not None:counters["minutes_available"]+=1
            row["status"]="PREGAME_LOCKED"
            old.append(row)
            seen.add(k)
            counters["new"]+=1
        except (ValueError,KeyError,TypeError):
            counters["invalid_comparisons"]+=1
    return old,dict(counters)


def finished_unique(paper_rows):
    """Earliest locked independent book per player/event/market/side."""
    groups={}
    for r in paper_rows:
        if r.get("status")!="SETTLED" or r.get("market") not in MARKETS:continue
        try:
            start=utc(r["event_start"]);at=utc(r["captured_at"])
            if at>=start:continue
            p=valid(r.get("original_projection"))
            actual=valid(r.get("actual"))
            line=valid(r.get("line"))
            if p is None or actual is None or line is None:continue
            key=(str(r["player_id"]),start.isoformat(),r["market"])
            old=groups.get(key)
            if old is None or at<utc(old["captured_at"]):
                groups[key]=r
        except (ValueError,TypeError,KeyError):continue
    return list(groups.values())


def grade_injury_scenarios(ledger,paper_rows):
    """Paired scores for pregame-locked conditional injury candidate only."""
    actuals={}
    for r in finished_unique(paper_rows):
        key=(utc(r["event_start"]).isoformat(),str(r["player_id"]),r["market"])
        actuals[key]=float(r["actual"])
    grouped=defaultdict(list)
    for row in ledger:
        scenario=row.get("injury_scenario") or {}
        candidate=valid(scenario.get("scenario_market_projection"))
        if candidate is None:continue
        try:
            if utc(row["captured_at"])>=utc(row["event_start"]):continue
            key=(utc(row["event_start"]).isoformat(),str(row["player_id"]),row["market"])
            if key not in actuals:continue
            score=actuals[key]
            grouped[row["market"]].append((abs(score-row["combined_projection"]),
                                             abs(score-candidate)))
        except (ValueError,KeyError,TypeError):continue
    scores=[s for group in grouped.values() for s in group]
    def summary(rows):
        return {"paired_observations":len(rows),
          "baseline_mae":round(sum(r[0] for r in rows)/len(rows),4) if rows else None,
          "injury_candidate_mae":round(sum(r[1] for r in rows)/len(rows),4) if rows else None}
    return {"status":"DESCRIPTIVE_LOCKED_INJURY_SCENARIO_COMPARISON" if len(scores)>=30
            else "AWAITING_AT_LEAST_30_SETTLED_VERIFIED_INJURY_SCENARIOS",
            "overall":summary(scores),
            "by_market":{m:summary(grouped[m]) for m in MARKETS},
            "no_live_adjustment":True,
            "injury_causality_established":False}


def research_simulations(paper_rows):
    """20,000 seeded residual-bootstrap runs only if past out-of-time samples exist.

    For each chronological date, past settled outcomes are the ONLY eligible
    calibration distribution. Evaluation is prospective relative to the game,
    and no 100% probabilities can be asserted from finite bootstrap runs.
    """
    settled=finished_unique(paper_rows)
    by_market=defaultdict(list)
    for r in settled:by_market[r["market"]].append(r)
    report={}
    for stat in MARKETS:
        rows=sorted(by_market[stat],key=lambda r:(utc(r["event_start"]),str(r["player_id"])))
        days=sorted({utc(r["event_start"]).date().isoformat() for r in rows})
        results=[]
        past=[]
        for day in days:
            current=[r for r in rows if utc(r["event_start"]).date().isoformat()==day]
            if len(past)>=MIN_RESIDUALS:
                residuals=[float(r["actual"])-float(r["original_projection"]) for r in past]
                seed=int(hashlib.sha256((stat+day).encode()).hexdigest()[:15],16)
                rng=random.Random(seed)
                errors=rng.choices(residuals,k=SIMULATIONS)
                # Same 20k draw for all rows from this event date. Predictions
                # are evaluated against independently completed outcomes.
                for r in current:
                    original=float(r["original_projection"]);line=float(r["line"])
                    if original==line or float(r["actual"])==line:continue
                    want_over=original>line
                    prob=(sum((original+x>line) if want_over else (original+x<line) for x in errors)+.5)/(SIMULATIONS+1)
                    hit=int((float(r["actual"])>line)==want_over)
                    results.append((prob,hit))
            # SAME-DATE outcomes become available only after scoring the day.
            past.extend(current)
        n=len(results)
        report[stat]={"status":"PREGAME_CHRONOLOGICAL_20K_SIM_AUDIT" if n>=30 else
            "AWAITING_AT_LEAST_1000_PRIOR_SETTLED_GAMES_AND_30_LATER_TESTS",
            "completed_independent_markets":len(rows),
            "evaluated_later_markets":n,
            "simulation_count":SIMULATIONS,
            "brier_score":round(sum((p-y)**2 for p,y in results)/n,4) if n else None,
            "average_prediction":round(sum(p for p,_ in results)/n,4) if n else None,
            "observed_hit_rate":round(sum(y for _,y in results)/n,4) if n else None,
            "changes_live_probabilities":False}
    return report


def grade_assist_shadow(ledger,paper_rows):
    """Grade only truly pretip-locked assist forecasts on exact matching quotes."""
    outcomes={}
    for r in finished_unique(paper_rows):
        if r.get("market")!="AST":continue
        key=(utc(r["event_start"]).isoformat(),str(r["player_id"]),r["market"],
             float(r["line"]))
        outcomes[key]=float(r["actual"])
    seen=set()
    graded=[]
    for row in sorted(ledger,key=lambda x:str(x.get("captured_at",""))):
        try:
            saved=row.get("assist_shadow") or {}
            if saved.get("status")!="PREGAME_LOCKED_ASSIST_CHALLENGER":continue
            if row.get("market")!="AST":continue
            event=utc(row["event_start"])
            if utc(row["captured_at"])>=event:continue
            line=valid(row.get("line"))
            base=valid(row.get("combined_projection"))
            candidate=valid(saved.get("projection"))
            if line is None or base is None or candidate is None:continue
            key=(event.isoformat(),str(row["player_id"]),"AST",line)
            if key not in outcomes or key in seen:continue
            seen.add(key)
            actual=outcomes[key]
            graded.append({"date":event.astimezone(ZoneInfo("America/New_York")).date().isoformat(),
              "baseline":base,"shadow":candidate,"actual":actual,"line":line})
        except (TypeError,ValueError,KeyError):continue
    n=len(graded)
    wins=[0,0]
    for r in graded:
        if r["actual"]==r["line"]:continue
        for idx,which in enumerate(("baseline","shadow")):
            if r[which]!=r["line"] and (r[which]>r["line"])==(r["actual"]>r["line"]):
                wins[idx]+=1
    distinct=len({r["date"] for r in graded})
    return {"status":"PREGAME_LOCKED_ASSIST_SHADOW_RESEARCH_ONLY",
      "paired_assist_markets":n,"distinct_game_dates":distinct,
      "baseline_mae":round(sum(abs(r["baseline"]-r["actual"]) for r in graded)/n,3) if n else None,
      "shadow_mae":round(sum(abs(r["shadow"]-r["actual"]) for r in graded)/n,3) if n else None,
      "baseline_correct_direction":wins[0],
      "shadow_correct_direction":wins[1],
      "prospectively_ready_for_review":n>=100 and distinct>=10,
      "promoted":False,"production_probabilities_changed":False,
      "no_retroactive_shadow_generation":True}

def grade_selection_gate(ledger,paper_rows):
    """Prospective abstention effectiveness on frozen identical bookmaker lines.

    Score only selections whose gate result was snapshotted before tipoff,
    including abstentions, so we cannot cherry-pick or hide skipped losses.
    """
    outcomes={}
    for r in finished_unique(paper_rows):
        key=(utc(r["event_start"]).isoformat(),str(r["player_id"]),r["market"])
        outcomes[key]=(float(r["actual"]),float(r["line"]))
    seen=set()
    selected=[]
    skipped=[]
    for row in sorted(ledger,key=lambda r:str(r.get("captured_at",""))):
        gate=row.get("selection_gate")
        if not isinstance(gate,dict):continue
        try:
            if utc(row["captured_at"])>=utc(row["event_start"]):continue
            key=(utc(row["event_start"]).isoformat(),str(row["player_id"]),row["market"])
            if key in seen or key not in outcomes:continue
            seen.add(key)
            actual,line=outcomes[key]
            frozen_line=valid(row.get("line"))
            forecast=valid(row.get("combined_projection"))
            if (frozen_line is None or frozen_line!=line or
                    forecast is None or forecast==line or actual==line):
                continue
            decision={"date":utc(row["event_start"]).astimezone(ZoneInfo("America/New_York")).date().isoformat(),
              "market":row["market"],
              "win":int((forecast>line)==(actual>line))}
            (selected if gate.get("eligible") is True else skipped).append(decision)
        except (ValueError,KeyError,TypeError):continue
    def stat(rows):
        n=len(rows);wins=sum(x["win"] for x in rows)
        return {"markets":n,"wins":wins,"losses":n-wins,
           "hit_rate":round(wins/n,4) if n else None,
           "distinct_game_dates":len({x["date"] for x in rows})}
    return {"status":"PRETIP_ABSTENTION_RESEARCH_ONLY",
      "selected":stat(selected),"abstained":stat(skipped),
      "all_evaluated":stat(selected+skipped),
      "by_market":{m:{"selected":stat([r for r in selected if r["market"]==m]),
                        "abstained":stat([r for r in skipped if r["market"]==m])}
                   for m in MARKETS},
      "sufficient_prospective_validation":(
         len(selected)>=200 and len({x["date"] for x in selected})>=10
         and len(skipped)>=100),
      "production_applied":False,"wagers_recommended":0,
      "no_backfilling_older_game_gates":True}

def grade_opportunity_shadows(ledger,paper_rows):
    """Compare all four immutable pretip challengers with verified finals.

    MAE compares the same player's final total; hit rates require the exact
    originally quoted shadow line, not merely the same player/game/market.
    Prevent post-hoc reconstruction and count correlated books only once.
    """
    outcomes={}
    for r in finished_unique(paper_rows):
        try:
            k=(utc(r["event_start"]).isoformat(),str(r["player_id"]),r["market"])
            outcomes[k]=(float(r["actual"]),float(r["line"]))
        except (KeyError,ValueError,TypeError):continue
    seen=set()
    bymarket=defaultdict(list)
    coverage=Counter()
    pending=Counter()
    for row in sorted(ledger,key=lambda r:str(r.get("captured_at",""))):
        try:
            if row.get("market") not in MARKETS:continue
            event=utc(row["event_start"])
            if utc(row["captured_at"])>=event:
                coverage["late_capture_rejected"]+=1
                continue
            k=(event.isoformat(),str(row["player_id"]),row["market"])
            if k in seen:continue
            seen.add(k)
            shadow=valid(row.get("opportunity_shadow_projection"))
            baseline=valid(row.get("combined_projection"))
            line=valid(row.get("line"))
            if shadow is None or baseline is None or line is None:
                coverage["missing_locked_candidate_or_line"]+=1
                continue
            coverage["captured_candidate_markets"]+=1
            if k not in outcomes:
                pending[row["market"]]+=1
                continue
            actual,settled_line=outcomes[k]
            if not all(math.isfinite(n) for n in (actual,settled_line)):
                coverage["invalid_verified_result"]+=1
                continue
            # A final actual total is independent of the sportsbook quote.
            # Its direction, however, must be graded at the *saved* pretip
            # shadow line, never against a later or different bookmaker line.
            exact=abs(line-settled_line)<1e-9
            date=event.astimezone(ZoneInfo("America/New_York")).date().isoformat()
            stable=valid(row.get("stability_opportunity_shadow_projection"))
            bymarket[row["market"]].append({
                "baseline":baseline,"shadow":shadow,"stable":stable,"actual":actual,
                "line":line,"exact_line":exact,"date":date})
            if not exact:coverage["settled_quote_line_mismatch"]+=1
        except (KeyError,ValueError,TypeError,OverflowError):
            coverage["invalid_capture"]+=1
    def metrics(rows):
        n=len(rows)
        line_rows=[r for r in rows if r["exact_line"] and
                   r["actual"]!=r["line"] and
                   r["baseline"]!=r["line"] and r["shadow"]!=r["line"]]
        baseline_wins=sum((r["baseline"]>r["line"])==(r["actual"]>r["line"])
                          for r in line_rows)
        shadow_wins=sum((r["shadow"]>r["line"])==(r["actual"]>r["line"])
                        for r in line_rows)
        dates=len({r["date"] for r in rows})
        paired_dates=len({r["date"] for r in line_rows})
        stable_rows=[r for r in rows if r["stable"] is not None]
        stable_sides=[r for r in line_rows if r["stable"] is not None and r["stable"]!=r["line"]]
        stable_wins=sum((r["stable"]>r["line"])==(r["actual"]>r["line"]) for r in stable_sides)
        return {"paired_markets":n,
          "stability_shadow_paired_markets":len(stable_rows),
          "stability_shadow_mae":round(sum(abs(r["stable"]-r["actual"]) for r in stable_rows)/len(stable_rows),3) if stable_rows else None,
          "stability_shadow_same_line_eligible":len(stable_sides),
          "stability_shadow_correct_directions":stable_wins,
          "stability_shadow_same_line_hit_rate":round(stable_wins/len(stable_sides),4) if stable_sides else None,
          "distinct_game_dates":dates,
          "baseline_mae":round(sum(abs(r["baseline"]-r["actual"]) for r in rows)/n,3) if n else None,
          "opportunity_mae":round(sum(abs(r["shadow"]-r["actual"]) for r in rows)/n,3) if n else None,
          "baseline_correct_directions":baseline_wins,
          "opportunity_correct_directions":shadow_wins,
          "same_line_direction_eligible":len(line_rows),
          "same_line_distinct_game_dates":paired_dates,
          "baseline_same_line_hit_rate":round(baseline_wins/len(line_rows),4) if line_rows else None,
          "opportunity_same_line_hit_rate":round(shadow_wins/len(line_rows),4) if line_rows else None,
          "shadow_only_correct":sum(
             (r["shadow"]>r["line"])==(r["actual"]>r["line"]) and
             (r["baseline"]>r["line"])!=(r["actual"]>r["line"])
             for r in line_rows),
          "baseline_only_correct":sum(
             (r["baseline"]>r["line"])==(r["actual"]>r["line"]) and
             (r["shadow"]>r["line"])!=(r["actual"]>r["line"])
             for r in line_rows),
          "exact_line_matched_final_markets":sum(r["exact_line"] for r in rows),
          "line_mismatched_final_markets":sum(not r["exact_line"] for r in rows)}
    all_rows=[r for g in bymarket.values() for r in g]
    overall=metrics(all_rows)
    return {"status":"PREGAME_SHADOW_DESCRIPTIVE_ONLY" if len(all_rows)>=30
                    else "AWAITING_PRETIP_LOCKED_SHADOW_AND_SETTLED_GAMES",
            "overall":overall,
            "by_market":{m:metrics(bymarket[m]) for m in MARKETS},
            "capture_coverage":dict(coverage),
            "pending_by_market":{m:pending[m] for m in MARKETS},
            "same_line_required_for_direction_scoring":True,
            "stability_challenger_research_only":True,
            "mae_uses_same_player_verified_final_stat_only":True,
            "not_validated_by_future_game_dates":True,
            "live_applied":False,"eligible_for_live_promotion":False}

def grade_opponent_v2(ledger,paper_rows):
    """Score strictly locked V2 against same-game final, same quoted line."""
    outcomes={}
    for r in finished_unique(paper_rows):
        try:
            key=(utc(r["event_start"]).isoformat(),str(r["player_id"]),r["market"])
            outcomes[key]=(float(r["actual"]),float(r["line"]))
        except (KeyError,ValueError,TypeError):continue
    seen=set();segments=defaultdict(list);pending=Counter()
    for row in sorted(ledger,key=lambda r:str(r.get("captured_at",""))):
        try:
            when=utc(row["event_start"])
            if utc(row["captured_at"])>=when:continue
            key=(when.isoformat(),str(row["player_id"]),row["market"])
            if key in seen:continue
            seen.add(key)
            candidate=valid(row.get("opponent_v2_shadow_projection"))
            baseline=valid(row.get("combined_projection"))
            line=valid(row.get("line"))
            if candidate is None or baseline is None or line is None:continue
            if key not in outcomes:
                pending[row["market"]]+=1;continue
            actual,settled_line=outcomes[key]
            eastern=when.astimezone(ZoneInfo("America/New_York")).date().isoformat()
            exact=abs(line-settled_line)<1e-9
            segments[row["market"]].append((baseline,candidate,actual,line,exact,eastern))
        except (KeyError,ValueError,TypeError,OverflowError):continue
    def measures(items):
        n=len(items)
        same=[x for x in items if x[4] and x[2]!=x[3]
              and x[0]!=x[3] and x[1]!=x[3]]
        b=sum((x[0]>x[3])==(x[2]>x[3]) for x in same)
        c=sum((x[1]>x[3])==(x[2]>x[3]) for x in same)
        return {"paired_markets":n,
          "distinct_game_dates":len({x[5] for x in items}),
          "baseline_mae":round(sum(abs(x[0]-x[2]) for x in items)/n,4) if n else None,
          "v2_mae":round(sum(abs(x[1]-x[2]) for x in items)/n,4) if n else None,
          "exact_line_direction_eligible":len(same),
          "baseline_direction_wins":b,"v2_direction_wins":c,
          "baseline_hit_rate":round(b/len(same),4) if same else None,
          "v2_hit_rate":round(c/len(same),4) if same else None,
          "v2_only_correct":sum((x[1]>x[3])==(x[2]>x[3]) and
              (x[0]>x[3])!=(x[2]>x[3]) for x in same),
          "baseline_only_correct":sum((x[0]>x[3])==(x[2]>x[3]) and
              (x[1]>x[3])!=(x[2]>x[3]) for x in same)}
    allrows=[r for market in MARKETS for r in segments[market]]
    return {"status":"PREGAME_OPPONENT_V2_RESEARCH_ONLY",
        "overall":measures(allrows),
        "by_market":{m:measures(segments[m]) for m in MARKETS},
        "pending_by_market":{m:pending[m] for m in MARKETS},
        "same_line_only":True,"prospective_validation_required":True,
        "live_model_unchanged":True,"eligible_for_production":False}

def grade_tracking_opportunities(ledger,paper_rows):
    """Paired prospectively frozen AST/REB tracking shadows on exact same lines."""
    official={}
    for r in finished_unique(paper_rows):
        if r.get("market") not in ("AST","REB"):continue
        try:
            key=(utc(r["event_start"]).isoformat(),str(r["player_id"]),r["market"])
            official[key]=(float(r["actual"]),float(r["line"]))
        except (KeyError,ValueError,TypeError):continue
    seen=set();by=defaultdict(list);coverage=Counter()
    for r in sorted(ledger,key=lambda x:str(x.get("captured_at",""))):
        if r.get("market") not in ("AST","REB"):continue
        try:
            at=utc(r["captured_at"]);start=utc(r["event_start"])
            if at>=start:continue
            key=(start.isoformat(),str(r["player_id"]),r["market"])
            if key in seen:continue
            seen.add(key)
            alt=r.get("tracking_opportunity_shadow") or {}
            coverage[str(alt.get("status","LEGACY_NO_TRACKING_CAPTURE"))]+=1
            projection=valid(alt.get("projection"))
            base=valid(r.get("combined_projection"))
            line=valid(r.get("line"))
            if projection is None or base is None or line is None:continue
            if key not in official:continue
            actual,graded_line=official[key]
            by[r["market"]].append({"actual":actual,"base":base,"shadow":projection,
                "same_line":abs(line-graded_line)<1e-9,"line":line,
                "date":start.astimezone(ZoneInfo("America/New_York")).date().isoformat()})
        except (KeyError,ValueError,TypeError):continue
    def summary(rows):
        same=[x for x in rows if x["same_line"] and
              x["actual"]!=x["line"] and x["base"]!=x["line"] and x["shadow"]!=x["line"]]
        bw=sum((x["base"]>x["line"])==(x["actual"]>x["line"]) for x in same)
        sw=sum((x["shadow"]>x["line"])==(x["actual"]>x["line"]) for x in same)
        n=len(rows)
        return {"paired_markets":n,"exact_line_eligible":len(same),
                "distinct_game_dates":len(set(x["date"] for x in rows)),
                "baseline_mae":round(sum(abs(x["base"]-x["actual"]) for x in rows)/n,4) if n else None,
                "tracking_mae":round(sum(abs(x["shadow"]-x["actual"]) for x in rows)/n,4) if n else None,
                "baseline_wins":bw,"tracking_wins":sw,
                "baseline_hit_rate":round(bw/len(same),4) if same else None,
                "tracking_hit_rate":round(sw/len(same),4) if same else None}
    return {"status":"TRACKING_CHANCES_PRETIP_SHADOW_ONLY",
            "by_market":{m:summary(by[m]) for m in ("AST","REB")},
            "overall":summary(by["AST"]+by["REB"]),
            "coverage_statuses":dict(coverage),
            "source_rights_required":True,"production_applied":False,
            "eligible_for_production":False}


def grade_rebound_v1(ledger,paper_rows):
    """Exact frozen-line grading; no postgame model recalculation."""
    outcomes={}
    for r in finished_unique(paper_rows):
        if r.get("market")!="REB":continue
        try:
            k=(utc(r["event_start"]).isoformat(),str(r["player_id"]))
            outcomes[k]=(float(r["actual"]),float(r["line"]))
        except (KeyError,ValueError,TypeError):continue
    samples=[]
    pending=0
    coverage=Counter()
    seen=set()
    for row in sorted(ledger,key=lambda r:str(r.get("captured_at",""))):
        if row.get("market")!="REB":continue
        info=row.get("rebound_shadow_v1")
        if not isinstance(info,dict):continue
        try:
            start=utc(row["event_start"])
            if utc(row["captured_at"])>=start:continue
            key=(start.isoformat(),str(row["player_id"]))
            if key in seen:continue
            seen.add(key)
            coverage[str(info.get("status","UNKNOWN"))]+=1
            alt=valid(info.get("projection"))
            base=valid(row.get("combined_projection"))
            line=valid(row.get("line"))
            if alt is None or base is None or line is None:continue
            if key not in outcomes:
                pending+=1;continue
            actual,settled_line=outcomes[key]
            if not math.isfinite(actual):continue
            samples.append({"baseline":base,"shadow":alt,"actual":actual,
                "line":line,"exact":abs(line-settled_line)<1e-9,
                "date":start.astimezone(ZoneInfo("America/New_York")).date().isoformat()})
        except (ValueError,TypeError,KeyError,OverflowError):continue
    n=len(samples)
    valid_sides=[r for r in samples if r["exact"] and r["actual"]!=r["line"]
                 and r["baseline"]!=r["line"] and r["shadow"]!=r["line"]]
    wins_base=sum((r["baseline"]>r["line"])==(r["actual"]>r["line"])
                  for r in valid_sides)
    wins_alt=sum((r["shadow"]>r["line"])==(r["actual"]>r["line"])
                 for r in valid_sides)
    return {"status":"FROZEN_PREGAME_REBOUND_V1_RESEARCH_ONLY",
        "paired_markets":n,
        "distinct_game_dates":len({r["date"] for r in samples}),
        "same_frozen_line_eligible":len(valid_sides),
        "baseline_wins":wins_base,"shadow_wins":wins_alt,
        "baseline_hit_rate":round(wins_base/len(valid_sides),4) if valid_sides else None,
        "shadow_hit_rate":round(wins_alt/len(valid_sides),4) if valid_sides else None,
        "baseline_mae":round(sum(abs(r["baseline"]-r["actual"]) for r in samples)/n,4) if n else None,
        "shadow_mae":round(sum(abs(r["shadow"]-r["actual"]) for r in samples)/n,4) if n else None,
        "captured_statuses":dict(coverage),"pending":pending,
        "validated_for_live":False,"live_model_unchanged":True,
        "requires_more_distinct_game_dates":True}


def grade_licensed_onoff_shadows(ledger,paper_rows):
    """Prospective only, exact frozen line and verified player/event final."""
    actuals={}
    for r in finished_unique(paper_rows):
        try:
            k=(utc(r["event_start"]).isoformat(),str(r["player_id"]),r["market"])
            actuals[k]=(float(r["actual"]),float(r["line"]))
        except (KeyError,ValueError,TypeError):continue
    seen=set()
    segments=defaultdict(list)
    captured=Counter()
    pending=Counter()
    for row in sorted(ledger,key=lambda r:str(r.get("captured_at",""))):
        info=row.get("licensed_onoff_shadow")
        if not isinstance(info,dict):continue
        try:
            tip=utc(row["event_start"])
            if utc(row["captured_at"])>=tip:continue
            k=(tip.isoformat(),str(row["player_id"]),row["market"])
            if k in seen:continue
            seen.add(k)
            captured[str(info.get("status","UNKNOWN"))]+=1
            proposed=valid(info.get("projection"))
            baseline=valid(row.get("combined_projection"))
            line=valid(row.get("line"))
            if proposed is None or baseline is None or line is None:continue
            if k not in actuals:
                pending[row["market"]]+=1;continue
            final,quoted=actuals[k]
            exact=abs(quoted-line)<1e-9
            date=tip.astimezone(ZoneInfo("America/New_York")).date().isoformat()
            segments[row["market"]].append((baseline,proposed,final,line,exact,date))
        except (KeyError,ValueError,TypeError,OverflowError):continue
    def summarize(rows):
        eligible=[r for r in rows if r[4] and r[2]!=r[3]
                  and r[0]!=r[3] and r[1]!=r[3]]
        n=len(rows)
        bw=sum((r[0]>r[3])==(r[2]>r[3]) for r in eligible)
        cw=sum((r[1]>r[3])==(r[2]>r[3]) for r in eligible)
        return {"paired_markets":n,"distinct_game_dates":len({r[5] for r in rows}),
            "baseline_mae":round(sum(abs(r[0]-r[2]) for r in rows)/n,4) if n else None,
            "licensed_onoff_mae":round(sum(abs(r[1]-r[2]) for r in rows)/n,4) if n else None,
            "exact_line_eligible":len(eligible),
            "baseline_correct":bw,"licensed_onoff_correct":cw,
            "baseline_hit_rate":round(bw/len(eligible),4) if eligible else None,
            "licensed_onoff_hit_rate":round(cw/len(eligible),4) if eligible else None}
    allrows=[x for m in MARKETS for x in segments[m]]
    return {"status":"PRETIP_LICENSED_WOWY_SHADOW_RESEARCH_ONLY",
        "overall":summarize(allrows),
        "by_market":{m:summarize(segments[m]) for m in MARKETS},
        "captured_by_status":dict(captured),
        "pending_by_market":{m:pending[m] for m in MARKETS},
        "same_frozen_line_required":True,
        "live_model_unchanged":True,"eligible_for_production":False}

def stress_research_report(ledger,paper_rows):
    """Only pregame frozen warnings; settlements count market identities once."""
    settled=set()
    for p in finished_unique(paper_rows):
        try:
            settled.add((utc(p["event_start"]).isoformat(),str(p["player_id"]),p["market"]))
        except (KeyError,TypeError,ValueError):continue
    seen=set()
    bystatus=Counter()
    bywarning=Counter()
    covered=0
    fragile=0
    matched=0
    matched_fragile=0
    for row in sorted(ledger,key=lambda r:str(r.get("captured_at",""))):
        saved=row.get("stress_test_20k_v1")
        if not isinstance(saved,dict):continue
        try:
            event=utc(row["event_start"])
            if utc(row["captured_at"])>=event:continue
            key=(event.isoformat(),str(row["player_id"]),row["market"])
            if key in seen:continue
            seen.add(key)
            bystatus[str(saved.get("status","UNKNOWN"))]+=1
            for w in saved.get("warnings",[]):
                bywarning[str(w)]+=1
            if saved.get("status")=="CONDITIONAL_STRESS_RESEARCH_ONLY":
                covered+=1
                isfragile=saved.get("fragile_high_confidence") is True
                fragile+=int(isfragile)
                if key in settled:
                    matched+=1
                    matched_fragile+=int(isfragile)
        except (KeyError,ValueError,TypeError):continue
    return {"status":"PRETIP_CONDITIONAL_STRESS_DESCRIPTIVE_ONLY",
            "capture_statuses":dict(bystatus),"warnings":dict(bywarning),
            "independent_stress_tested_markets":covered,
            "fragile_high_confidence_flags":fragile,
            "paired_settled_stress_markets":matched,
            "paired_settled_fragile_flags":matched_fragile,
            "simulation_draws_per_scenario":20000,
            "calibrated_probability":False,
            "live_probabilities_changed":False,
            "live_picks_changed":False,
            "performance_improvement_established":False}


def grade_sanity_shadow(ledger,paper_rows):
    """Prospective paired MAE, separating actual adjustments from copied forecasts.

    The earliest immutable pregame observation wins. Old records cannot be
    retroactively reconstructed as predictions. Pending, uncertain and unchanged
    estimates are reported, never presented as evidence of uplift.
    """
    actuals={}
    for paper in finished_unique(paper_rows):
        try:
            key=(utc(paper["event_start"]).isoformat(),
                 str(paper["player_id"]),paper["market"])
            if paper.get("status")=="SETTLED":
                actuals[key]=float(paper["actual"])
        except (KeyError,ValueError,TypeError):continue
    seen=set()
    matched=defaultdict(list)
    adjusted=defaultdict(list)
    captured=Counter()
    pending=Counter()
    excluded=Counter()
    for row in sorted(ledger,key=lambda r:str(r.get("captured_at",""))):
        info=row.get("sanity_shadow_v1")
        if not isinstance(info,dict):continue
        try:
            event=utc(row["event_start"])
            if utc(row["captured_at"])>=event:
                excluded["late_capture"]+=1
                continue
            key=(event.isoformat(),str(row["player_id"]),row["market"])
            if key in seen:continue
            seen.add(key)
            kind=str(info.get("status","UNKNOWN"))
            captured[kind]+=1
            if key not in actuals:
                pending[kind]+=1
                continue
            candidate=valid(info.get("shadow_projection"))
            baseline=valid(row.get("combined_projection"))
            if candidate is None or baseline is None:
                excluded[kind]+=1
                continue
            actual=actuals[key]
            date=event.astimezone(ZoneInfo("America/New_York")).date().isoformat()
            pair=(abs(candidate-actual),abs(baseline-actual),date)
            matched[row["market"]].append(pair)
            # Unchanged projections are controls, not adjusted-shadow victories.
            if kind=="SHADOW_CANDIDATE_UNVALIDATED" and candidate!=baseline:
                adjusted[row["market"]].append(pair)
        except (ValueError,KeyError,TypeError):continue
    def score(rows):
        n=len(rows)
        return {"paired_markets":n,
                "distinct_game_dates":len({r[2] for r in rows}),
                "shadow_mae":round(sum(r[0] for r in rows)/n,4) if n else None,
                "combined_mae":round(sum(r[1] for r in rows)/n,4) if n else None}
    allrows=[v for group in matched.values() for v in group]
    changed=[v for group in adjusted.values() for v in group]
    return {"status":"UNVALIDATED_PREGAME_SANITY_SHADOW",
            "captured_independent_markets":sum(captured.values()),
            "captured_by_status":dict(captured),
            "pending_by_status":dict(pending),
            "overall":score(allrows),
            "adjusted_only":score(changed),
            "by_market":{m:score(matched[m]) for m in MARKETS},
            "adjusted_by_market":{m:score(adjusted[m]) for m in MARKETS},
            "excluded_uncertain_by_status":dict(excluded),
            "prospective_validation_needed":True,
            "live_applied":False,"accuracy_gain_established":False}


def grade_shadow(ledger,paper_rows):
    """Paired MAE only for actually captured V4 shadows; never backfill."""
    graded={}
    for row in finished_unique(paper_rows):
        key=(utc(row["event_start"]).isoformat(),str(row["player_id"]),row["market"])
        graded[key]=float(row["actual"])
    scores=[]
    for row in ledger:
        shadow=valid(row.get("v4_shadow_projection"))
        if shadow is None:continue
        try:
            if utc(row["captured_at"])>=utc(row["event_start"]):continue
            key=(utc(row["event_start"]).isoformat(),str(row["player_id"]),row["market"])
            if key in graded:
                actual=graded[key]
                scores.append((abs(actual-row["combined_projection"]),abs(actual-shadow),row["market"]))
        except (ValueError,TypeError,KeyError):continue
    return {"status":"PAIRED_V4_SHADOW_SCORED" if len(scores)>=30 else
            "AWAITING_CURRENT_SEASON_VERIFIED_V4_AND_SETTLED_GAMES",
            "paired_markets":len(scores),
            "combined_mae":round(sum(x[0] for x in scores)/len(scores),4) if scores else None,
            "v4_mae":round(sum(x[1] for x in scores)/len(scores),4) if scores else None,
            "v4_live_applied":False}


def run(board,injury,paper_rows,existing,at,game_history=None,onoff_feed=None,tracking_feed=None):
    ledger,counts=snapshot(board,injury,existing,at,game_history,onoff_feed,tracking_feed)
    capture_gate=verify_prospective_capture(ledger,len(existing),len(ledger))
    settled=finished_unique(paper_rows)
    return ledger,{"generated_at":utc(at).isoformat(),
        "status":"OPPORTUNITY_V4_SHADOW_AND_20K_CALIBRATION_RESEARCH_ONLY",
        "locked_samples":len(ledger),"new_samples":counts.get("new",0),
        "features_covered":counts,
        "prospective_capture_integrity":capture_gate,
        "settled_independent_paper_markets":len(settled),
        "injury_context":"VERIFIED_SAME_GAME_OFFICIAL_REPORT_ONLY",
        "lineup_confirmations_automated":False,
        "teammate_splits":"OBSERVATIONAL_AND_SAMPLE_GATED",
        "defender_v4":grade_shadow(ledger,paper_rows),
        "injury_opportunity":grade_injury_scenarios(ledger,paper_rows),
        "opportunity_shadow":grade_opportunity_shadows(ledger,paper_rows),
        "opponent_v2_shadow":grade_opponent_v2(ledger,paper_rows),
        "rebound_shadow_v1":grade_rebound_v1(ledger,paper_rows),
        "tracking_opportunity_shadow":grade_tracking_opportunities(ledger,paper_rows),
        "licensed_onoff_shadow":grade_licensed_onoff_shadows(ledger,paper_rows),
        "sanity_shadow_v1":grade_sanity_shadow(ledger,paper_rows),
        "stress_test_20k_v1":stress_research_report(ledger,paper_rows),
        "model_disagreement_v1":disagreement_report(ledger,paper_rows,finished_unique,utc),
        "unified_reliability_v1":unified_reliability_view(ledger,paper_rows,generated_at=at),
        "selection_gate_shadow":grade_selection_gate(ledger,paper_rows),
        "assist_shadow_v1":grade_assist_shadow(ledger,paper_rows),
        "simulation_audit":research_simulations(paper_rows),
        "live_combined_ai_unchanged":True,
        "live_simulated_hit_percentages_unchanged":True,
        "promotion_gate":"NO_LIVE_ADJUSTMENT_WITHOUT_PRE_GAME_VALIDATION"}


def main():
    board=json.loads(BOARD.read_text())
    injury=json.loads(INJURY.read_text()) if INJURY.exists() else {}
    paper=json.loads(PAPER.read_text()).get("records",[]) if PAPER.exists() else []
    existing=json.loads(LEDGER.read_text()).get("records",[]) if LEDGER.exists() else []
    now=datetime.now(timezone.utc).isoformat()
    source=PRIVATE_ONOFF if PRIVATE_ONOFF.exists() else ONOFF
    onoff=json.loads(source.read_text()) if source.exists() else {}
    tracking=json.loads(PRIVATE_TRACKING.read_text()) if PRIVATE_TRACKING.exists() else {}
    games_path=ROOT/"data/nba/current/current_games.json"
    game_history=json.loads(games_path.read_text()) if games_path.exists() else []
    try:
        ledger,report=run(board,injury,paper,existing,now,game_history,onoff,tracking)
    except ValueError as error:
        # A scheduled research-only refresh can update settlement diagnostics
        # even if there is no fresh pregame AI feed to freeze. It may never
        # fabricate a historical capture from a stale postgame board.
        if "within 45 minutes" not in str(error) and "Board must be" not in str(error):
            raise
        ledger=list(existing)
        report={"generated_at":utc(now).isoformat(),
            "status":"RESEARCH_AUDIT_ONLY_NO_FRESH_PREGAME_BOARD",
            "capture_notice":str(error),
            "locked_samples":len(ledger),"new_samples":0,
            "features_covered":{},
            "settled_independent_paper_markets":len(finished_unique(paper)),
            "injury_context":"VERIFIED_SAME_GAME_OFFICIAL_REPORT_ONLY",
            "lineup_confirmations_automated":False,
            "teammate_splits":"OBSERVATIONAL_AND_SAMPLE_GATED",
            "defender_v4":grade_shadow(ledger,paper),
            "injury_opportunity":grade_injury_scenarios(ledger,paper),
            "opportunity_shadow":grade_opportunity_shadows(ledger,paper),
            "opponent_v2_shadow":grade_opponent_v2(ledger,paper),
            "rebound_shadow_v1":grade_rebound_v1(ledger,paper),
            "tracking_opportunity_shadow":grade_tracking_opportunities(ledger,paper),
            "licensed_onoff_shadow":grade_licensed_onoff_shadows(ledger,paper),
            "sanity_shadow_v1":grade_sanity_shadow(ledger,paper),
            "stress_test_20k_v1":stress_research_report(ledger,paper),
            "model_disagreement_v1":disagreement_report(ledger,paper,finished_unique,utc),
            "unified_reliability_v1":unified_reliability_view(ledger,paper,generated_at=now),
            "selection_gate_shadow":grade_selection_gate(ledger,paper),
            "assist_shadow_v1":grade_assist_shadow(ledger,paper),
            "simulation_audit":research_simulations(paper),
            "live_combined_ai_unchanged":True,
            "live_simulated_hit_percentages_unchanged":True,
            "promotion_gate":"NO_LIVE_ADJUSTMENT_WITHOUT_PRE_GAME_VALIDATION"}
    LEDGER.write_text(json.dumps({"version":1,"records":ledger},indent=2)+"\n")
    STATUS.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,sort_keys=True),flush=True)


if __name__=="__main__":main()
