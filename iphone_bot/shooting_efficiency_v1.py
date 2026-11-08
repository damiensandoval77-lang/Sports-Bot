"""Shooting Efficiency V1 shadow: lagged attempt-weighted scoring, defense and minutes.

Research-only. Last 5/10 and season efficiencies, separate projected 2PA,
3PA and FTA, shrinkage, conservative opponent adjustment, and fixed blend.
No actual target-game attempts, makes, outcomes or current injuries as input.
"""
import bisect
import math
from collections import defaultdict
from statistics import mean

try:
    from .shot_profile_research import normalized,predict_points
except ImportError:
    from shot_profile_research import normalized,predict_points

VERSION="SHOOTING_EFFICIENCY_OPPONENT_SHADOW_V1"
MIN_PRIOR=8

def ratio(makes,attempts):
    return round(makes/attempts,4) if attempts>0 else None

def rates(history,day,team):
    valid=[]
    for g in sorted(history,key=lambda g:str(g.get("date",""))):
        if g.get("team")!=team or str(g.get("date",""))>=str(day):
            continue
        obs=normalized(g,require_makes=True)
        if obs:valid.append(obs)
    if len(valid)<MIN_PRIOR:return None
    def window(rows):
        fga=sum(x["FGA"] for x in rows);fgm=sum(x["FG2M"]+x["FG3M"] for x in rows)
        three=sum(x["FG3A"] for x in rows)
        three_m=sum(x["FG3M"] for x in rows)
        two=sum(x["FG2A"] for x in rows);two_m=sum(x["FG2M"] for x in rows)
        fta=sum(x["FTA"] for x in rows);ftm=sum(x["FTM"] for x in rows)
        pts=sum(x["PTS"] for x in rows)
        return {"games":len(rows),"fg_pct":ratio(fgm,fga),"three_pct":ratio(three_m,three),
            "two_pct":ratio(two_m,two),"ft_pct":ratio(ftm,fta),
            "effective_fg_pct":ratio(fgm+.5*three_m,fga),
            "true_shooting_pct":ratio(pts,2*(fga+.44*fta)),
            "fga_per_game":round(fga/len(rows),3),
            "three_pa_per_game":round(three/len(rows),3),
            "fta_per_game":round(fta/len(rows),3),
            "field_goal_attempts":fga,"three_point_attempts":three,
            "free_throw_attempts":fta}
    return {"last5":window(valid[-5:]),"last10":window(valid[-10:]),
        "season":window(valid),"history_games":len(valid),
        "method":"ATTEMPT_WEIGHTED_COMPLETED_PRIOR_SAME_TEAM_GAMES",
        "last_history_game":max(str(g.get("date","")) for g in history
                              if g.get("team")==team and str(g.get("date",""))<str(day))}

def opponent_defense_index(games):
    """Observed opponent shooting efficiency allowed from actual complete team boxes.

    Store one aggregate per offensive team-game; use this only as a lagged
    descriptive proxy, not individual defender or shot-location tracking.
    """
    grouped=defaultdict(list)
    for g in games:
        day=g.get("date");opponent=g.get("opponent");team=g.get("team")
        if day and opponent and team and opponent!=team:
            normalized_box=normalized(g,require_makes=True)
            if normalized_box:
                season=g.get("season") or g.get("SEASON_ID") or str(day)[:4]
                grouped[(season,str(day),str(team),str(opponent))].append(normalized_box)
    index=defaultdict(list)
    for (season,day,team,defense),rows in grouped.items():
        if len(rows)<7:continue
        two=sum(g["FG2A"] for g in rows);three=sum(g["FG3A"] for g in rows)
        if two<20 or three<8:continue
        index[(season,defense)].append((day,sum(g["FG2M"] for g in rows),
                                        two,sum(g["FG3M"] for g in rows),three))
    for k in index:index[k].sort(key=lambda r:r[0])
    return index

def defense_adjustment(index,opponent,day,season=None):
    key=(season or str(day)[:4],opponent)
    games=index.get(key,[])
    dates=[r[0] for r in games]
    end=bisect.bisect_left(dates,str(day))
    prior=games[max(0,end-10):end]
    result={"status":"NO_VERIFIED_OPPONENT_SHOOTING_SAMPLE",
            "games":len(prior),"two_multiplier":1.0,"three_multiplier":1.0,
            "individual_defender_inferred":False,
            "actual_shot_location_inferred":False}
    if len(prior)<5:return result
    def scaled(made,att,league_prior):
        # Fixed shrinkage of opposing observed conversion toward generic
        # league-style reference, then bounded 5% efficiency effect.
        pct=(made+league_prior*80)/(att+80)
        return round(min(1.05,max(.95,1+.2*(pct/league_prior-1))),4)
    return {**result,"status":"LAGGED_OPPONENT_TEAM_SHOOTING_PROXY",
       "two_multiplier":scaled(sum(x[1] for x in prior),sum(x[2] for x in prior),.52),
       "three_multiplier":scaled(sum(x[3] for x in prior),sum(x[4] for x in prior),.35),
       "latest_defense_game":prior[-1][0],
       "games":len(prior)}

def forecast(history,day,team,opponent=None,expected_minutes=None,
             defense_index=None,season=None,combined_baseline=None,
             verified_absence_minutes=None):
    out={"status":"INSUFFICIENT_SHOOTING_DATA","model":VERSION,
        "projection":None,"raw_points":None,"blended_projection":None,
        "season_shooting":None,"expected_minutes":None,
        "opponent_adjustment_applied":False,
        "injury_usage_adjustment_applied":False,
        "production_applied":False}
    shooting=rates(history,day,team)
    if not shooting:return out
    # Minutes provider independent of target-game production.
    history_mins=[g["MIN"] for g in history if
         g.get("team")==team and str(g.get("date",""))<str(day) and
         isinstance(g.get("MIN"),(int,float)) and 0<float(g["MIN"])<=60]
    mins=expected_minutes
    if mins is None and len(history_mins)>=8:mins=mean(history_mins[-5:])
    if mins is None or not 0<float(mins)<=60:return out
    shot=predict_points(history,day,team,float(mins))
    if not shot:return out
    context=(defense_adjustment(defense_index,opponent,day,season)
             if defense_index is not None and opponent else
             {"status":"OPPONENT_DATA_NOT_AVAILABLE","games":0,
              "two_multiplier":1.0,"three_multiplier":1.0})
    pts=(2*shot["expected_2pa"]*shot["expected_2p_pct"]*
          context["two_multiplier"]+
          3*shot["expected_3pa"]*shot["expected_3p_pct"]*
          context["three_multiplier"]+
          shot["expected_fta"]*shot["expected_ft_pct"])
    # No inferred injury impact; expected_minutes may already be an
    # external pretip minutes estimate. Never add unverified usage boosts.
    pts=max(0,pts)
    base=combined_baseline
    blended=None
    if base is not None:
        try:
            base=float(base)
            if not math.isfinite(base) or base<0:raise ValueError
            blended=round(max(0,base+.25*max(-.15*max(1,base),
                             min(.15*max(1,base),pts-base))),3)
        except (ValueError,TypeError):pass
    return {**out,"status":"PREGAME_SHOOTING_SHADOW_RESEARCH",
        "projection":round(pts,3),"raw_points":round(pts,3),
        "unadjusted_points":shot["expected_points"],
        "blended_projection":blended,
        "expected_minutes":round(float(mins),3),
        "season_shooting":shooting,
        "expected_2pa":shot["expected_2pa"],
        "expected_3pa":shot["expected_3pa"],
        "expected_fta":shot["expected_fta"],
        "expected_2p_pct":shot["expected_2p_pct"],
        "expected_3p_pct":shot["expected_3p_pct"],
        "expected_ft_pct":shot["expected_ft_pct"],
        "opponent_shooting":context,
        "opponent_adjustment_applied":context["status"]=="LAGGED_OPPONENT_TEAM_SHOOTING_PROXY",
        "last_prior_game":shooting["last_history_game"],
        "baseline_source":"FROZEN_COMBINED_PROJECTION" if blended is not None else None,
        "shot_location_quality":"2PA_AND_3PA_ONLY",
        "teammate_absence_usage_recalculated":False}
