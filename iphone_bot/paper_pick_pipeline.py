"""Immutable pregame paper-pick snapshots and real postgame grading.

Only quotes seen before scheduled start are eligible. Each tracked paper pick
locks a model projection, chosen OVER/UNDER side, actual bookmaker price, and
game/player identity. Settlement NEVER re-runs a model or selects a side after
observing game results. No money is wagered or assumed.
"""
import json
import math
from datetime import datetime,timezone
from pathlib import Path
from collections import defaultdict
try:
    from .model_performance import compute_performance
    from .weight_research import walkforward_weights
    from .accuracy_feedback import evaluate as accuracy_feedback
    from .probability_audit import audit as probability_audit
except ImportError:
    from model_performance import compute_performance
    from weight_research import walkforward_weights
    from accuracy_feedback import evaluate as accuracy_feedback
    from probability_audit import audit as probability_audit

ROOT=Path(__file__).resolve().parents[1]
LEDGER=ROOT/"docs/paper_pick_ledger.json"
RESULTS=ROOT/"docs/paper_results.json"
STATS={"PTS","REB","AST","PRA"}
METHOD="PRE_GAME_LOCKED_PROJECTION_REAL_BOOK_PRICE_PAPER_ONLY"

def utc(value):
    d=datetime.fromisoformat(str(value).replace("Z","+00:00"))
    if d.tzinfo is None:raise ValueError("Timestamp has no timezone")
    return d.astimezone(timezone.utc)

def payout(american):
    odds=int(american)
    if odds>=100:return odds/100.0
    if odds<=-100:return 100.0/abs(odds)
    raise ValueError("Invalid American odds")

def identity(row):
    # JSON and Python represent the SAME UTC instant differently:
    # 2026-11-07T00:40:00.000Z vs 2026-11-07T00:40:00+00:00.
    # Canonicalize timestamps and lines so repeated workflow runs never
    # double-count a previously locked sportsbook offer.
    return "|".join((
        utc(row["event_start"]).isoformat(),
        str(row["player_id"]).strip(),
        str(row["team"]).strip().upper(),
        str(row["market"]).strip().upper(),
        str(row["bookmaker"]).strip().casefold(),
        format(float(row["line"]),".10g")
    ))

def snapshot(comparisons,generated_at,existing=None):
    """Freeze quoted side, observed price, projection and estimated P at capture.

    Deduplication is per event/player/team/market/book/line.
    The first saved quote and side win; later opposite-side forecasts do not replace it.
    """
    created=utc(generated_at)
    rows=[]
    seen=set()
    for prior in sorted(existing or [],key=lambda r:utc(r["captured_at"])):
        ident=identity(prior)
        if ident in seen:continue
        rows.append(prior)
        seen.add(ident)
    for market in comparisons:
        if market.get("stat") not in STATS:continue
        start=utc(market["start"])
        if created>=start:continue
        for book in market.get("book_quotes",[]):
            try:
                chosen_projection=float(market.get("combined_projection",market["projection"]))
                original_projection=float(market["projection"])
                line=float(book["line"])
                if not (math.isfinite(chosen_projection) and math.isfinite(original_projection)
                        and math.isfinite(line) and chosen_projection>=0 and
                        original_projection>=0 and line>=0):
                    continue
                if not expected_opponents(market["game"],str(market["team"])):
                    continue
                if chosen_projection==line:continue
                side="OVER" if chosen_projection>line else "UNDER"
                odds=book.get("over" if side=="OVER" else "under")
                payout(odds)
            except (TypeError,ValueError,KeyError,OverflowError):
                continue
            record={"event_start":start.isoformat(),"captured_at":created.isoformat(),
                "player_id":str(market["player_id"]),
                "player":str(market["player"]),"team":str(market["team"]),
                "game":str(market["game"]),"market":market["stat"],
                "bookmaker":str(book["name"]),"line":line,"side":side,
                "american_odds":int(odds),
                "over_odds":int(book["over"]) if book.get("over") is not None else None,
                "under_odds":int(book["under"]) if book.get("under") is not None else None,
                "original_projection":original_projection,
                "combined_projection":chosen_projection,
                "model":"TWO_MODEL_MEDIAN_RESEARCH" if market.get("combined_model_count")==2 else "PROVISIONAL_ORIGINAL",
                "projection_method":market.get("combined_method","ORIGINAL_AI_FALLBACK"),
                "status":"PENDING",
                "method":METHOD,
                "paper_only":True,
                "original_probability_side":("OVER" if original_projection>line else
                    "UNDER" if original_projection<line else None),
                "original_probability_estimate":book.get(
                    "over_model_probability" if original_projection>line else
                    "under_model_probability" if original_projection<line else
                    "unavailable_probability"),
                "original_probability_method":"CHRONOLOGICAL_VALIDATION_EMPIRICAL_RESIDUALS_UNCALIBRATED",
                "experimental_estimate_model":"PROVISIONAL_ORIGINAL_ONLY",
                "experimental_estimate":book.get(
                    "over_model_probability" if side=="OVER" else "under_model_probability"),
                "hypothetical_ev_pct":book.get("hypothetical_over_ev_pct" if side=="OVER" else "hypothetical_under_ev_pct"),
                "opponent_shadow_projection":market.get("shadow_projection")}
            ident=identity(record)
            if ident not in seen:
                rows.append(record)
                seen.add(ident)
    rows.sort(key=lambda x:(x["event_start"],x["player"],x["market"],x["bookmaker"],x["captured_at"]))
    return rows

def settle(rows,completed_games,now=None):
    """Grade ONLY locked pregame snapshots against exact completed player games."""
    now=utc(now or datetime.now(timezone.utc).isoformat())
    by_id=defaultdict(list)
    for g in completed_games:
        by_id[(str(g["id"]),str(g["date"]))].append(g)
    result=[]
    for original in rows:
        r=dict(original)
        if r["status"]!="PENDING":
            result.append(r);continue
        start=utc(r["event_start"])
        # Avoid interpreting partial in-progress box scores as final. The third
        # party feed contains completed logs but a 5h buffer adds protection.
        if now.timestamp()-start.timestamp()<5*3600:
            result.append(r);continue
        if utc(r["captured_at"])>=start:
            r["status"]="INVALID_LATE_CAPTURE"
            result.append(r);continue
        gameday=start.astimezone(__import__("zoneinfo").ZoneInfo("America/New_York")).date().isoformat()
        candidates=[g for g in by_id.get((str(r["player_id"]),gameday),[])
                    if g.get("team")==r["team"] and g.get("opponent") in [
                        # Need opposing roster team verification before settlement.
                        gteam for gteam in expected_opponents(r["game"],r["team"])]]
        if len(candidates)!=1:
            result.append(r);continue
        try:
            game=candidates[0]
            # The source may contain an in-progress, malformed, or duplicate
            # player row. Require a plausible completed player stat line.
            minutes=float(game["MIN"])
            actual=float(game[r["market"]])
            line=float(r["line"])
            if not (math.isfinite(minutes) and 0<minutes<=60
                    and math.isfinite(actual) and actual>=0
                    and math.isfinite(line) and line>=0):
                result.append(r);continue
            if r["market"]=="PRA" and all(x in game for x in ("PTS","REB","AST")):
                parts=[float(game[x]) for x in ("PTS","REB","AST")]
                if not all(math.isfinite(x) and x>=0 for x in parts) or abs(actual-sum(parts))>0.01:
                    result.append(r);continue
            payout_unit=payout(r["american_odds"])
            if actual>line:outcome="OVER"
            elif actual<line:outcome="UNDER"
            else:outcome="PUSH"
            profit=0.0 if outcome=="PUSH" else (payout_unit if outcome==r["side"] else -1.0)
        except (ValueError,TypeError,KeyError,OverflowError):
            result.append(r);continue
        r.update({"status":"SETTLED","settled_at":now.isoformat(),
                  "actual":actual,"result":"PUSH" if outcome=="PUSH" else ("WIN" if outcome==r["side"] else "LOSS"),
                  "paper_profit_units":round(profit,6)})
        result.append(r)
    return result

TEAM_ABBREVIATIONS={
    "Atlanta Hawks":"ATL","Boston Celtics":"BOS","Brooklyn Nets":"BKN",
    "Charlotte Hornets":"CHA","Chicago Bulls":"CHI","Cleveland Cavaliers":"CLE",
    "Dallas Mavericks":"DAL","Denver Nuggets":"DEN","Detroit Pistons":"DET",
    "Golden State Warriors":"GSW","Houston Rockets":"HOU","Indiana Pacers":"IND",
    "Los Angeles Clippers":"LAC","LA Clippers":"LAC","Los Angeles Lakers":"LAL",
    "Memphis Grizzlies":"MEM","Miami Heat":"MIA","Milwaukee Bucks":"MIL",
    "Minnesota Timberwolves":"MIN","New Orleans Pelicans":"NOP",
    "New York Knicks":"NYK","Oklahoma City Thunder":"OKC","Orlando Magic":"ORL",
    "Philadelphia 76ers":"PHI","Phoenix Suns":"PHX","Portland Trail Blazers":"POR",
    "Sacramento Kings":"SAC","San Antonio Spurs":"SAS","Toronto Raptors":"TOR",
    "Utah Jazz":"UTA","Washington Wizards":"WAS"}

def expected_opponents(game,team):
    halves=str(game).split(" @ ")
    if len(halves)!=2:return []
    pair=tuple(TEAM_ABBREVIATIONS.get(x.strip()) for x in halves)
    if None in pair or pair[0]==pair[1] or team not in pair:return []
    return [pair[0] if pair[1]==team else pair[1]]

def pipeline_health(rows,source=None,now=None):
    """Operational visibility, never inferred game results or retroactive grades."""
    now=utc(now or datetime.now(timezone.utc).isoformat())
    pending=[r for r in rows if r.get("status")=="PENDING"]
    # A gap is actionable only when the matchup has passed the 5-hour buffer.
    # Source-date lag does not prove that any individual player's game is final.
    eligible=[r for r in pending if (now-utc(r["event_start"])).total_seconds()>=5*3600]
    old=[r for r in eligible if (now-utc(r["event_start"])).total_seconds()>=48*3600]
    late_teams={identity(r) for r in old}
    meta=source if isinstance(source,dict) else {}
    version=meta.get("source_version")
    latest=meta.get("latest_game_date")
    status="OK_AWAITING_MATCHUPS"
    if old:status="OVERDUE_UNSETTLED_PICKS"
    elif eligible:status="WAITING_FOR_COMPLETED_PLAYER_LOGS"
    if not latest:status="NO_VALIDATED_BOXSCORE_SOURCE"
    return {
        "status":status,
        "boxscore_source_version":version,
        "latest_completed_player_game_date":latest,
        "source_last_checked_at":meta.get("updated_at"),
        "pending_total":len(pending),
        "pending_past_game_buffer":len(eligible),
        "pending_over_48_hours":len(late_teams),
        "notice":"Overdue does not mean a loss; missing or delayed box scores must not be guessed."
    }

def summary(rows,now=None,source=None):
    now=utc(now or datetime.now(timezone.utc).isoformat())
    settled=[r for r in rows if r.get("status")=="SETTLED"]
    pending=[r for r in rows if r.get("status")=="PENDING"]
    unique_games=len({(r["player_id"],r["event_start"],r["market"]) for r in settled})
    unique_pending=len({(r["player_id"],r["event_start"],r["market"]) for r in pending})
    wins=sum(r["result"]=="WIN" for r in settled)
    losses=sum(r["result"]=="LOSS" for r in settled)
    pushes=sum(r["result"]=="PUSH" for r in settled)
    profits=round(sum(r["paper_profit_units"] for r in settled),4)
    record={"generated_at":now.isoformat(),
       "status":"REAL_SPORTSBOOK_QUOTES_PAPER_ONLY",
       "model":"PROVISIONAL_ORIGINAL",
       "method":METHOD,"real_money_wagered":False,
       "captured":len(rows),"pending":len(pending),"settled":len(settled),
       "performance":compute_performance(rows),
       "accuracy_feedback":accuracy_feedback(rows),
       "probability_audit":probability_audit(rows),
       "weight_research":walkforward_weights(rows),
       "pipeline_health":pipeline_health(rows,source,now),
       "independent_player_game_markets":unique_games,
       "independent_pending_player_game_markets":unique_pending,
       "wins":wins,"losses":losses,"pushes":pushes,
       "win_rate_ex_push":round(wins/(wins+losses),4) if wins+losses else None,
       "paper_profit_units":profits,
       "paper_roi_per_graded_unit":round(profits/len(settled),4) if settled else None,
       "results":list(reversed(sorted(settled,key=lambda r:(r["event_start"],r["captured_at"]))))[:100],
       "limitations":[
         "Paper records are NOT actual placed bets or cash profits.",
         "Every book/line for the same player and game is correlated; ROI is descriptive, not independent wagers.",
         "Quotes and pregame projections must be saved before start; old quotes cannot be retroactively graded as locked model picks.",
         "No real-market calibration, injury confirmation, verified primary defenders, or PrizePicks line/payout access.",
         "Third-party completed player-game logs may lag official NBA corrections.",
         "No real-money execution or gambling automation."]}
    return record

def main():
    # Settlement is strictly read-only with respect to the pregame forecast
    # set. Only capture_ai_board.py may add records using the ACTUAL capture
    # timestamp before tipoff. Never reconstruct historical locks here.
    games_path=ROOT/"data/nba/current/current_games.json"
    rows=json.loads(LEDGER.read_text()).get("records",[]) if LEDGER.exists() else []
    if games_path.exists():
        rows=settle(rows,json.loads(games_path.read_text()))
    LEDGER.write_text(json.dumps({"version":1,"records":rows},indent=2)+"\n")
    source_path=ROOT/"docs/current_form.json"
    source=json.loads(source_path.read_text()) if source_path.exists() else None
    report=summary(rows,source=source)
    RESULTS.write_text(json.dumps(report,indent=2)+"\n")
    # Diagnostics are observational only: never alter or retroactively grade picks.
    pending=[r for r in rows if r.get("status")=="PENDING"]
    now=datetime.now(timezone.utc)
    diagnostics={"pending_total":len(pending),"within_five_hour_buffer":0,
                 "awaiting_matching_completed_player_game":0,
                 "late_capture_invalid":0,"missing_or_ambiguous_player_match":0,
                 "over_48_hours_unsettled":0}
    completed=json.loads(games_path.read_text()) if games_path.exists() else []
    by_id=defaultdict(list)
    for g in completed:
        by_id[(str(g.get("id")),str(g.get("date")))].append(g)
    for r in pending:
        start=utc(r["event_start"])
        age=(now-start).total_seconds()
        if age<5*3600:
            diagnostics["within_five_hour_buffer"]+=1
            continue
        if age>=48*3600:
            diagnostics["over_48_hours_unsettled"]+=1
        if utc(r["captured_at"])>=start:
            diagnostics["late_capture_invalid"]+=1
            continue
        day=start.astimezone(__import__("zoneinfo").ZoneInfo("America/New_York")).date().isoformat()
        opponents=expected_opponents(r["game"],r["team"])
        matches=[g for g in by_id.get((str(r["player_id"]),day),[])
                 if g.get("team")==r["team"] and g.get("opponent") in opponents]
        if len(matches)!=1:
            diagnostics["missing_or_ambiguous_player_match"]+=1
        else:
            diagnostics["awaiting_matching_completed_player_game"]+=1
    print("SETTLEMENT DIAGNOSTICS:",json.dumps(diagnostics,sort_keys=True),flush=True)
    print("PAPER PIPELINE:",json.dumps({x:report[x] for x in
          ("captured","pending","settled","wins","losses","pushes","paper_roi_per_graded_unit")}),flush=True)

if __name__=="__main__":main()
