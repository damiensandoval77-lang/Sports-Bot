"""Current-season listed-position opponent context from downloaded game logs.

The collector's *local* current_games.json includes listed Pos, team, opponent,
date, minutes and stats; compact docs/current_form.json intentionally omits Pos.
This module reports strictly earlier role-level boxscore allowances, NOT actual
defender assignments, official tracking, a verified betting edge, or a HIT EST.
"""
import argparse
import json
from collections import Counter,defaultdict
from datetime import datetime,timezone
from pathlib import Path
from statistics import mean
from zoneinfo import ZoneInfo

MARKETS=("PTS","REB","AST","PRA")
ROLES=("PG","SG","SF","PF","C")
MIN_ROLE_GAMES=5
MIN_TEAM_PLAYERS=7

def time(value):
    t=datetime.fromisoformat(str(value).replace("Z","+00:00"))
    if t.tzinfo is None:raise ValueError("naive timestamp")
    return t.astimezone(timezone.utc)

def role(value):
    if not isinstance(value,str):return None
    v=value.strip().upper()
    return v if v in ROLES else None

def sane(x):
    return type(x) in (int,float) and 0<=x<float("inf")

def build(logs,form,schedule,*,captured_at):
    clock=time(captured_at)
    observed=time(form["updated_at"])
    sched_time=time(schedule["generated_at"])
    if observed>clock or sched_time>clock or not form.get("source_url") or not schedule.get("source_url"):
        raise ValueError("source timing or provenance not verified")
    if form.get("season")!="2026-27" or not isinstance(logs,list):
        raise ValueError("source season/schema mismatch")
    rows={}
    unsafe_team_games=set()
    by_player=defaultdict(list)
    rejected=Counter()
    for g in logs:
        if not isinstance(g,dict):continue
        d,pid,team,opp=g.get("date"),str(g.get("id") or ""),g.get("team"),g.get("opponent")
        if not d or not pid or not team or not opp or team==opp:
            rejected["missing_identity"]+=1;continue
        if not all(sane(g.get(stat)) for stat in (*MARKETS,"MIN")) or not 0<g["MIN"]<=60:
            rejected["invalid_box_stat"]+=1
            unsafe_team_games.add((d,team,opp))
            continue
        if abs(g["PTS"]+g["REB"]+g["AST"]-g["PRA"])>.01:
            rejected["invalid_pra"]+=1
            unsafe_team_games.add((d,team,opp))
            continue
        if d>clock.astimezone(ZoneInfo("America/New_York")).date().isoformat():
            rejected["future_observation"]+=1;continue
        key=(d,team,pid)
        if key in rows:
            rejected["duplicate_observation"]+=1
            unsafe_team_games.add((d,team,opp))
            rows[key]=None
            continue
        rows[key]=g
    validated=[g for g in rows.values() if g]
    for g in validated:
        by_player[(str(g["id"]),g["team"])].append(g)
    games=defaultdict(list)
    for g in validated:
        games[(g["date"],g["team"],g["opponent"])].append(g)
    role_allowed=defaultdict(list)
    accepted=0
    seen=set()
    for (day,team,opp),offense in sorted(games.items()):
        opposing=games.get((day,opp,team),[])
        identity=(day,tuple(sorted((team,opp))))
        if identity in seen:continue
        seen.add(identity)
        if (day,team,opp) in unsafe_team_games or (day,opp,team) in unsafe_team_games:
            rejected["corrupt_or_duplicate_team_game"]+=1;continue
        if min(len(offense),len(opposing))<MIN_TEAM_PLAYERS:
            rejected["partial_team_game"]+=1;continue
        if any(len({str(x["id"]) for x in part})!=len(part) for part in (offense,opposing)):
            rejected["ambiguous_player_game"]+=1;continue
        accepted+=1
        for offense_team,defense_team,players in ((team,opp,offense),(opp,team,opposing)):
            for pos in ROLES:
                in_role=[p for p in players if role(p.get("position"))==pos]
                if not in_role:continue
                role_allowed[(defense_team,pos)].append({
                    "date":day,"game_identity":identity,
                    **{stat:mean(float(p[stat]) for p in in_role) for stat in MARKETS}})
    for key in role_allowed:
        role_allowed[key].sort(key=lambda x:(x["date"],x["game_identity"]))
    future=[]
    for fixture in schedule.get("games",[]):
        tip=time(fixture["start"])
        if tip<=clock:continue
        day=fixture["date_eastern"]
        if tip.astimezone(ZoneInfo("America/New_York")).date().isoformat()!=day:
            raise ValueError("fixture Eastern date mismatch")
        home,away=fixture["home_abbreviation"],fixture["away_abbreviation"]
        out={"game_id":fixture["id"],"game_date":day,"start":fixture["start"],
             "player_positional_context":[]}
        for team,opp in ((home,away),(away,home)):
            for (pid,pteam),history in by_player.items():
                if pteam!=team:continue
                prior=sorted([x for x in history if x["date"]<day],key=lambda x:x["date"])
                positions=[role(x.get("position")) for x in prior[-5:]]
                if len(prior)<3 or None in positions or len(set(positions))!=1:
                    rejected["unverified_stable_listed_position"]+=1;continue
                pos=positions[0]
                samples=[x for x in role_allowed.get((opp,pos),[]) if x["date"]<day]
                samples=samples[-5:]
                record={"player_id":pid,"team":team,"opponent":opp,"listed_position":pos,
                    "status":"INSUFFICIENT_POSITIONAL_DEFENSE_DATA",
                    "source":form["source_url"],
                    "source_observed_at":form["updated_at"],
                    "prior_position_games":len(prior),
                    "defense_games":len(samples),
                    "opponent_aware_verified":False}
                if len({x["game_identity"] for x in samples})>=MIN_ROLE_GAMES:
                    reference=[v for (defense,p),series in role_allowed.items() if p==pos
                               for v in series if v["date"]<day]
                    if len(reference)>=30:
                        record.update({
                            "status":"THIRD_PARTY_LISTED_POSITION_ALLOWANCE_RESEARCH",
                            "defense_last5_per_listed_player":{
                               stat:round(mean(x[stat] for x in samples),3) for stat in MARKETS},
                            "league_listed_position_baseline":{
                               stat:round(mean(x[stat] for x in reference),3) for stat in MARKETS},
                            "prior_opponent_game_dates":[x["date"] for x in samples],
                            "opponent_aware_verified":False})
                out["player_positional_context"].append(record)
        future.append(out)
    return {"status":"POSITIONAL_BOX_SCORE_RESEARCH_ONLY",
        "captured_at":captured_at,
        "source":form["source_url"],"source_updated_at":form["updated_at"],
        "source_kind":"THIRD_PARTY_LISTED_POSITION_NOT_DEFENDER_ASSIGNMENT",
        "reciprocal_completed_games":accepted,
        "future_game_count":len(future),"future_games":future,
        "position_context_records":sum(len(g["player_positional_context"]) for g in future),
        "position_context_with_samples":sum(x["status"]=="THIRD_PARTY_LISTED_POSITION_ALLOWANCE_RESEARCH"
          for g in future for x in g["player_positional_context"]),
        "rejections":dict(sorted(rejected.items())),
        "actual_defender_assignments_available":False,
        "production_hit_estimate_eligible":False,
        "note":"Listed PG/SG/SF/PF/C role is not assigned defender. Historical aggregate source may change; capture time only proves availability from now onward. No ratio automatically applied to model or historical picks."}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--logs",default="data/nba/current/current_games.json")
    p.add_argument("--form",default="docs/current_form.json")
    p.add_argument("--schedule",default="docs/nba_schedule.json")
    p.add_argument("--output",default="positional-defense-research.json")
    a=p.parse_args()
    now=datetime.now(timezone.utc).isoformat()
    res=build(json.loads(Path(a.logs).read_text()),json.loads(Path(a.form).read_text()),
              json.loads(Path(a.schedule).read_text()),captured_at=now)
    Path(a.output).write_text(json.dumps(res,indent=2,sort_keys=True)+"\n")
    print(json.dumps({k:res[k] for k in ("status","reciprocal_completed_games","future_game_count",
        "position_context_records","position_context_with_samples",
        "production_hit_estimate_eligible")},indent=2))
if __name__=="__main__":main()
