"""Independent assist / rebound opportunity candidates using genuine tracking.

Never train on or observe the target game. These are candidate projections,
not verified better forecasts, not calibrated hit rates and not live weights.
"""
import math
from statistics import mean
try:
    from .tracking_opportunity_features import MIN_GAMES
except ImportError:
    from tracking_opportunity_features import MIN_GAMES

VERSION="TRACKING_OPPORTUNITY_SHADOW_V1"
CONFIG={"AST":("potential_assists","AST"),"REB":("rebound_chances","REB")}

def _valid(x):
    try:
        v=float(x)
        return v if math.isfinite(v) and v>=0 else None
    except (ValueError, TypeError):return None

def forecast_opportunity(tracking, player_id, team, upcoming_date,
                         observed_box_games, expected_minutes=None):
    """Compute independent AST and REB forecasts, using only date < start.

    Both histories must match athlete and team. Need three paired, completed
    tracking+box-score player games, with valid minutes and opportunity stats.
    """
    current=[r for r in tracking.get((str(player_id),str(team).upper()),[])
             if r["date"]<str(upcoming_date)]
    boxes={r.get("date"):r for r in observed_box_games
           if r.get("date","")<str(upcoming_date) and
              str(r.get("id") or r.get("player_id"))==str(player_id) and
              str(r.get("team","")).upper()==str(team).upper()}
    paired=[(t,boxes[t["date"]]) for t in current if t["date"] in boxes]
    minutes=_valid(expected_minutes)
    if minutes is None or minutes<=0:
        recent=[_valid(box["MIN"]) for _,box in paired[-5:]]
        recent=[x for x in recent if x is not None and x>0]
        minutes=round(mean(recent),2) if len(recent)>=MIN_GAMES else None
    results={}
    for stat,(chance_key,box_key) in CONFIG.items():
        available=[]
        for t,box in paired:
            chance=_valid(t.get(chance_key))
            actual=_valid(box.get(box_key))
            m=_valid(box.get("MIN"))
            if chance is not None and actual is not None and m is not None and m>0:
                available.append((t,box,chance,actual,m))
        base={"status":"INSUFFICIENT_TRACKED_GAMES","stat":stat,
              "chance_metric":chance_key,"games":len(available),
              "projection":None,"production_applied":False,
              "method":VERSION}
        if len(available)<MIN_GAMES or minutes is None:
            results[stat]=base
            continue
        observations=available[-10:]
        total_chances=sum(x[2] for x in observations)
        total_actual=sum(x[3] for x in observations)
        total_minutes=sum(x[4] for x in observations)
        if total_chances<=0 or total_minutes<=0:
            results[stat]=base
            continue
        # Shrink conversion toward a neutral 50% rate by 8 pseudo chances;
        # prevents division by zero and extreme rates with small opportunity.
        # Uses fixed prior for research; evaluate on heldout dates before use.
        conversion=min(1.0,(total_actual+4.0)/(total_chances+8.0))
        per_min=total_chances/total_minutes
        candidate=max(0.0,minutes*per_min*conversion)
        results[stat]={**base,"status":"PREGAME_OPPORTUNITY_SHADOW",
            "projection":round(candidate,2),
            "expected_minutes":round(minutes,2),
            "chances_per_minute":round(per_min,4),
            "conversion_rate":round(conversion,4),
            "historical_chances":round(total_chances,2),
            "historical_actual":round(total_actual,2),
            "games":len(observations),
            "latest_paired_game":observations[-1][0]["date"],
            "source":"OBSERVED_PLAYER_GAME_TRACKING_AND_BOX_SCORES"}
    return results

def backtest_opportunity(tracking, game_logs, min_date=None):
    """Chronological rolling audit. At least 3 strictly prior matches required.

    Reports identical player-game market observations for candidate and naive
    baseline. This is retrospective research, not pre-registered forward proof.
    """
    groups={}
    for game in game_logs:
        key=(str(game.get("id") or game.get("player_id")),str(game.get("team","")).upper())
        if not game.get("date") or not key[0] or not key[1]:
            continue
        groups.setdefault(key,[]).append(game)
    samples={s:[] for s in CONFIG}
    for (pid,team),games in groups.items():
        games.sort(key=lambda v:v.get("date",""))
        for game in games:
            day=game["date"]
            if min_date and day<min_date:continue
            previous=[x for x in games if x["date"]<day]
            mins=[_valid(x.get("MIN")) for x in previous[-5:]]
            mins=[m for m in mins if m is not None and m>0]
            expected=mean(mins) if len(mins)>=MIN_GAMES else None
            preds=forecast_opportunity(tracking,pid,team,day,previous,expected)
            for stat in CONFIG:
                pred=preds[stat]
                actual=_valid(game.get(stat))
                prior=[_valid(x.get(stat)) for x in previous[-5:]]
                prior=[v for v in prior if v is not None]
                if pred["projection"] is None or actual is None or len(prior)<MIN_GAMES:
                    continue
                baseline=mean(prior)
                samples[stat].append((day,abs(pred["projection"]-actual),
                                      abs(baseline-actual),pred["projection"],
                                      baseline,actual))
    result={}
    for stat,items in samples.items():
        n=len(items)
        result[stat]={"status":"RETROSPECTIVE_RESEARCH_ONLY" if n else "NO_PAIRED_TRACKING_SAMPLES",
            "paired_player_games":n,
            "distinct_game_dates":len(set(x[0] for x in items)),
            "shadow_mae":round(mean(x[1] for x in items),3) if n else None,
            "recent5_baseline_mae":round(mean(x[2] for x in items),3) if n else None,
            "candidate_lower_mae":sum(x[1]<x[2] for x in items),
            "baseline_lower_mae":sum(x[1]>x[2] for x in items),
            "production_applied":False}
    return {"method":VERSION,"by_market":result,
            "baseline":"RECENT_5_PLAYER_GAMES", "production_applied":False,
            "source_status":"ACTUAL_TRACKING_REQUIRED"}
