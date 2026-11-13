"""Immutable pregame paper-pick snapshots and real postgame grading.

Only quotes seen before scheduled start are eligible. Each tracked paper pick
locks a model projection, chosen OVER/UNDER side, actual bookmaker price, and
game/player identity. Settlement NEVER re-runs a model or selects a side after
observing game results. No money is wagered or assumed.
"""
import json
import copy
import math
import re
import unicodedata
from datetime import datetime,timezone
from pathlib import Path
from collections import defaultdict
try:
    from .model_performance import compute_performance
    from .weight_research import walkforward_weights
    from .accuracy_feedback import evaluate as accuracy_feedback
    from .probability_audit import audit as probability_audit
    from .selective_challenger import screen as research_screen, evaluate as selective_evaluate, minutes_risk
    from .season_average_research import report as season_average_report
except ImportError:
    from model_performance import compute_performance
    from weight_research import walkforward_weights
    from accuracy_feedback import evaluate as accuracy_feedback
    from probability_audit import audit as probability_audit
    from selective_challenger import screen as research_screen, evaluate as selective_evaluate, minutes_risk
    from season_average_research import report as season_average_report

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
                "combined_probability_proxy_side":side,
                "combined_probability_proxy_estimate":book.get(
                    "over_model_probability" if side=="OVER" else "under_model_probability"),
                "combined_probability_proxy_method":"ORIGINAL_RESIDUAL_PROXY_FOR_COMBINED_DIRECTION_UNCALIBRATED",
                "experimental_estimate_model":"PROVISIONAL_ORIGINAL_ONLY",
                "experimental_estimate":book.get(
                    "over_model_probability" if side=="OVER" else "under_model_probability"),
                "hypothetical_ev_pct":book.get("hypothetical_over_ev_pct" if side=="OVER" else "hypothetical_under_ev_pct"),
                "opponent_shadow_projection":market.get("shadow_projection"),
                "research_selective_v1":research_screen(market["stat"],line,
                    original_projection,market.get("shadow_projection"),chosen_projection),
                "research_minutes_risk_v1":minutes_risk(market.get("minutes_research"),
                    market.get("minutes_v2_research"),market.get("injury_status")),
                "season_average_challenger":market.get("season_average_challenger"),
                # Immutable pretip Shooting V1 shadow for prospective grading.
                # Never recompute this field using postgame outcomes.
                "shooting_efficiency_v1":copy.deepcopy(
                    market.get("shooting_efficiency_v1"))
                    if market.get("stat")=="PTS" else None,
                "minutes_v3_research":copy.deepcopy(
                    market.get("minutes_v3_research")),
                "opportunity_v2_research":copy.deepcopy(
                    market.get("opportunity_v2_research"))
                    if market.get("stat") in ("AST","REB") else None,
                "model_feature_audit":copy.deepcopy(market.get("model_feature_audit")),
                "frozen_minutes_research":copy.deepcopy(market.get("minutes_research")),
                "frozen_minutes_v2_research":copy.deepcopy(market.get("minutes_v2_research")),
                "frozen_injury_status":market.get("injury_status"),
                "forensic_data_collected_pregame":True}
            ident=identity(record)
            if ident not in seen:
                rows.append(record)
                seen.add(ident)
    rows.sort(key=lambda x:(x["event_start"],x["player"],x["market"],x["bookmaker"],x["captured_at"]))
    return rows

def strict_player_name(value):
    """Compare complete player names, allowing only casing, accents and punctuation."""
    ascii_name=unicodedata.normalize("NFKD",str(value or "")).casefold()
    ascii_name="".join(x for x in ascii_name if not unicodedata.combining(x))
    return re.sub(r"[^a-z0-9]","",ascii_name)


def settle(rows,completed_games,now=None):
    """Grade ONLY locked pregame snapshots against exact completed player games."""
    now=utc(now or datetime.now(timezone.utc).isoformat())
    by_id=defaultdict(list)
    by_name=defaultdict(list)
    for g in completed_games:
        if g.get("source") in ("NBA_CDN_FINAL","ESPN_FINAL","CBS_FINAL_VERIFIED","FANTASYDATA_FINAL_CROSSCHECKED","CBS_SPORTS_LIVE_FINAL","NBA_OFFICIAL_WEB_FINAL_CROSSCHECKED"):
            if g.get("final_confirmed") is True:
                key=(strict_player_name(g.get("player")),str(g.get("date")))
                if key[0]:by_name[key].append(g)
        elif "id" in g and "date" in g:
            by_id[(str(g["id"]),str(g["date"]))].append(g)
    result=[]
    for original in rows:
        r=dict(original)
        if r["status"]!="PENDING":
            result.append(r);continue
        start=utc(r["event_start"])
        if utc(r["captured_at"])>=start:
            r["status"]="INVALID_LATE_CAPTURE"
            result.append(r);continue
        age=(now-start).total_seconds()
        gameday=start.astimezone(__import__("zoneinfo").ZoneInfo("America/New_York")).date().isoformat()
        opponents=expected_opponents(r["game"],r["team"])
        # Direct NBA/ESPN rows are usable only when the game is explicitly
        # FINAL and at least two hours have passed from scheduled tipoff.
        # Final status comes from the verified provider, NOT the elapsed time.
        # CSV rows retain the more conservative five-hour threshold.
        direct=[g for g in by_name.get((strict_player_name(r["player"]),gameday),[])
                if g.get("team")==r["team"] and g.get("opponent") in opponents
                and g.get("final_confirmed") is True]
        dnp_direct=[g for g in direct if g.get("dnp_final_verified") is True]
        playable_direct=[g for g in direct if not g.get("dnp_final_verified")]
        if dnp_direct and playable_direct:
            # Contradictory providers cannot be used to grade or void.
            result.append(r);continue
        if len(dnp_direct)==1 and age>=2*3600:
            evidence=dnp_direct[0]
            r.update({"status":"VOID_DNP","result":"VOID",
                      "void_reason":evidence.get("dnp_reason","Verified no-play"),
                      "void_source_url":"https://www.nba.com/game/"+
                        str(evidence.get("source_game_id","")),
                      "void_recorded_at":now.isoformat()})
            result.append(r);continue
        direct=playable_direct
        # Multiple providers can observe the same final game.
        # Identical pts/reb/ast are corroboration, not ambiguity.
        # Conflicting providers must not be graded arbitrarily.
        if len(direct)>1:
            signatures={(float(g["PTS"]),float(g["REB"]),float(g["AST"]))
                        for g in direct if all(g.get(k) is not None
                        for k in ("PTS","REB","AST"))}
            if len(signatures)==1 and len(direct)==len([
                g for g in direct if all(g.get(k) is not None
                for k in ("PTS","REB","AST"))]):
                priority={"NBA_CDN_FINAL":0,"ESPN_FINAL":1,
                          "CBS_FINAL_VERIFIED":2,
                          "FANTASYDATA_FINAL_CROSSCHECKED":3,
                          "CBS_SPORTS_LIVE_FINAL":4,"NBA_OFFICIAL_WEB_FINAL_CROSSCHECKED":1}
                direct=[min(direct,key=lambda g:priority.get(g.get("source"),99))]
            else:
                direct=[]
        csv=[g for g in by_id.get((str(r["player_id"]),gameday),[])
             if g.get("team")==r["team"] and g.get("opponent") in opponents]
        if age>=2*3600 and len(direct)==1:
            candidates=direct
        elif age>=5*3600 and len(csv)==1:
            candidates=csv
        else:
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
                  "settlement_source":game.get("source","HISTORICAL_CSV_COMPLETED_GAME"),
                  "source_game_id":game.get("source_game_id"),
                  "actual":actual,"actual_minutes":round(minutes,4),"result":"PUSH" if outcome=="PUSH" else ("WIN" if outcome==r["side"] else "LOSS"),
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
       "void_dnp":sum(r.get("status")=="VOID_DNP" for r in rows),
       "performance":compute_performance(rows),
       "selective_challenger":selective_evaluate(rows),
       "season_average_research":season_average_report(rows),
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

def cross_checked_final_boxscores(path):
    """Read only explicitly transcribed, matchup-locked third-party FINAL games.

    Do not accept this as official NBA data. The source, score, complete
    identity and player totals are preserved for post-hoc auditing.
    """
    if not path.exists():return []
    payload=json.loads(path.read_text())
    if payload.get("status")!="THIRD_PARTY_FINAL_BOXSCORE_MANUALLY_CROSS_CHECKED":
        raise ValueError("Manual final-game audit not verified")
    if not str(payload.get("source_url","")).startswith("https://qa.img.cbssports.com/nba/gametracker/"):
        raise ValueError("Unexpected final boxscore attribution")
    if not payload.get("cross_check_url") or not payload.get("game_id"):
        raise ValueError("Missing independent final-game verification")
    date=payload.get("game_date_eastern")
    matchup=payload.get("matchup")
    if not isinstance(date,str) or not isinstance(matchup,str) or " @ " not in matchup:
        raise ValueError("Missing completed matchup identity")
    away,home=matchup.split(" @ ")
    a=TEAM_ABBREVIATIONS.get(away)
    h=TEAM_ABBREVIATIONS.get(home)
    if not a or not h or a==h:
        raise ValueError("Unknown confirmed matchup teams")
    totals={}
    rows=payload.get("records") or []
    seen=set()
    for row in rows:
        if (row.get("date")!=date or row.get("source")!="CBS_FINAL_VERIFIED"
            or str(row.get("source_game_id"))!=str(payload["game_id"])
            or row.get("final_confirmed") is not True):
            raise ValueError("Unverified individual player identity")
        team=row.get("team")
        if team not in (a,h) or row.get("opponent")!=(h if team==a else a):
            raise ValueError("Player team/opponent mismatch")
        k=(strict_player_name(row.get("player")),team)
        if not k[0] or k in seen:raise ValueError("Ambiguous verified player")
        seen.add(k)
        if not (0<float(row["MIN"])<=60 and
                all(float(row[x])>=0 for x in ("PTS","REB","AST")) and
                abs(float(row["PRA"])-(float(row["PTS"])+float(row["REB"])+float(row["AST"])))<.001):
            raise ValueError("Invalid verified final stat line")
        totals[team]=totals.get(team,0)+float(row["PTS"])
    # A partial player list is allowed, but must not exceed final team points.
    for team,total in totals.items():
        if total>float(payload["final_team_score"][team]):
            raise ValueError("Player points exceed verified team final")
    return rows

def fantasydata_cross_checked_final(path):
    """Require separately sourced final result and complete game identity.

    This manually audited fallback is NOT an automatically available official
    NBA boxscore. Every included player is matched exactly to a stored pick.
    Non-participants are omitted rather than invented as zero-stat games.
    """
    if not path.exists():return []
    payload=json.loads(path.read_text())
    if payload.get("status")!="THIRD_PARTY_FINAL_BOXSCORE_MANUALLY_CROSS_CHECKED":
        raise ValueError("Unverified third party player boxscore status")
    url=str(payload.get("source_url") or "")
    confirm=str(payload.get("cross_check_url") or "")
    if (not url.startswith("https://fantasydata.com/nba/boxscore/") or
        not confirm.startswith("https://www.cbssports.com/nba/gametracker/boxscore/")):
        raise ValueError("Independent source verification missing")
    date=payload.get("game_date_eastern")
    away_name,sep,home_name=str(payload.get("matchup") or "").partition(" @ ")
    a=TEAM_ABBREVIATIONS.get(away_name)
    h=TEAM_ABBREVIATIONS.get(home_name)
    if not sep or not a or not h or a==h or not date:
        raise ValueError("Unrecognized manual match identity")
    score=payload.get("final_team_score",{})
    if not all(isinstance(score.get(x),int) and score[x]>0 for x in (a,h)):
        raise ValueError("No confirmed final team scores")
    seen=set()
    totals={a:0,h:0}
    rows=payload.get("records",[])
    if not rows:raise ValueError("No finalized player boxscore rows")
    for row in rows:
        code=row.get("team")
        if (row.get("date")!=date or
            row.get("source")!="FANTASYDATA_FINAL_CROSSCHECKED" or
            row.get("final_confirmed") is not True or
            row.get("source_game_id")!=payload.get("game_id") or
            code not in (a,h) or
            row.get("opponent")!=(h if code==a else a)):
            raise ValueError("Unverified player identity/fixture")
        ident=(strict_player_name(row.get("player")),code)
        if not ident[0] or ident in seen:raise ValueError("Ambiguous player")
        seen.add(ident)
        vals=[float(row[field]) for field in ("PTS","REB","AST","PRA","MIN")]
        if (not all(math.isfinite(v) and v>=0 for v in vals) or
            not 0<vals[4]<=60 or abs(vals[3]-sum(vals[:3]))>.01):
            raise ValueError("Invalid player totals or minutes")
        totals[code]+=vals[0]
    if any(totals[code]>score[code] for code in (a,h)):
        raise ValueError("Player scoring exceeds confirmed final")
    return rows

def official_web_cross_checked_final(path):
    """Verify a manually transcribed official NBA final player box score.

    Require an official NBA game URL, independent corroboration, game identity,
    finite played minutes, unique full player names, matching teams, and PRA.
    This source is explicitly labeled manual official-web cross-check, not CDN.
    """
    if not path.exists():return []
    payload=json.loads(path.read_text())
    if payload.get("status")!="OFFICIAL_NBA_WEB_FINAL_MANUALLY_CROSS_CHECKED":
        raise ValueError("Unverified official final boxscore")
    gameid=str(payload.get("game_id",""))
    url=str(payload.get("source_url",""))
    check=str(payload.get("cross_check_url",""))
    if (not gameid.isdigit() or len(gameid)!=10 or
        not url.startswith("https://www.nba.com/") or
        gameid not in url or
        not check.startswith("https://www.basketusa.com/resultats/boxscore_")):
        raise ValueError("Official and corroborating sources missing")
    away,sep,home=str(payload.get("matchup","")).partition(" @ ")
    a,h=TEAM_ABBREVIATIONS.get(away),TEAM_ABBREVIATIONS.get(home)
    day=payload.get("game_date_eastern")
    if not sep or not a or not h or a==h or not day:
        raise ValueError("Invalid matchup identity")
    scores=payload.get("final_team_score") or {}
    if not all(isinstance(scores.get(t),int) and scores[t]>0 for t in (a,h)):
        raise ValueError("Final team scores missing")
    rows=payload.get("records") or []
    if not rows:raise ValueError("Missing completed player lines")
    seen=set()
    totals={a:0.,h:0.}
    for row in rows:
        team=row.get("team")
        if (row.get("source")!="NBA_OFFICIAL_WEB_FINAL_CROSSCHECKED" or
            row.get("source_game_id")!=gameid or
            row.get("final_confirmed") is not True or
            row.get("date")!=day or team not in (a,h) or
            row.get("opponent")!=(h if team==a else a)):
            raise ValueError("Final boxscore identity mismatch")
        ident=(strict_player_name(row.get("player")),team)
        if not ident[0] or ident in seen:raise ValueError("Duplicate or absent player")
        seen.add(ident)
        vals=[float(row[k]) for k in ("PTS","REB","AST","PRA","MIN")]
        if (not all(math.isfinite(v) and v>=0 for v in vals) or
            not 0<vals[4]<=60 or abs(vals[3]-sum(vals[:3]))>.001):
            raise ValueError("Malformed official player total")
        totals[team]+=vals[0]
    if any(totals[t]>scores[t] for t in (a,h)):
        raise ValueError("Player points exceed official final score")
    return rows


def main():
    # Settlement is strictly read-only with respect to the pregame forecast
    # set. Only capture_ai_board.py may add records using the ACTUAL capture
    # timestamp before tipoff. Never reconstruct historical locks here.
    games_path=ROOT/"data/nba/current/current_games.json"
    rows=json.loads(LEDGER.read_text()).get("records",[]) if LEDGER.exists() else []
    completed=json.loads(games_path.read_text()) if games_path.exists() else []
    direct_path=ROOT/"data/nba/current/final_boxscores.json"
    if direct_path.exists():
        completed.extend(json.loads(direct_path.read_text()))
    completed.extend(cross_checked_final_boxscores(ROOT/"docs/verified_postgame_boxscores.json"))
    completed.extend(fantasydata_cross_checked_final(ROOT/"docs/verified_wizards_hawks_boxscores.json"))
    completed.extend(official_web_cross_checked_final(ROOT/"docs/verified_spurs_kings_boxscores.json"))
    cbs_path=ROOT/"data/nba/current/cbs_final_boxscores.json"
    if cbs_path.exists():
        completed.extend(json.loads(cbs_path.read_text()))
    rows=settle(rows,completed)
    try:
        from .dnp_settlement import apply_verified_dnp,load_fixture
    except ImportError:
        from dnp_settlement import apply_verified_dnp,load_fixture
    rows=apply_verified_dnp(rows,load_fixture())
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
