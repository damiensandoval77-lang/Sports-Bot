"""Strict date-ordered, paired research comparison of positional adjustment vs player L5.

NO sportsbook hit-rate estimates or live probability publication. No training
on target game. Retrospective source export may have been revised after target;
not equivalent to prospective as-of feature validation.
"""
import argparse
import json
from collections import defaultdict,Counter
from datetime import date,datetime,timezone,timedelta
from math import isfinite
from pathlib import Path
from statistics import mean
from research.position_defense_current_season import role

MARKETS=("PTS","REB","AST","PRA")
MIN_PLAYER_GAMES=5
MIN_DEFENSE_GAMES=5
MIN_LEAGUE_ROLE_GAMES=30

def numeric(v):
    return type(v) in (int,float) and isfinite(v) and v>=0

def prepare(rows):
    by_match=defaultdict(list)
    invalid=set()
    for r in rows:
        if not isinstance(r,dict):continue
        d,team,opp,pid=r.get("date"),r.get("team"),r.get("opponent"),str(r.get("id") or "")
        if not d or not team or not opp or not pid or team==opp:continue
        key=(d,team,opp)
        try:day=date.fromisoformat(d)
        except ValueError:
            invalid.add(key);continue
        if (not all(numeric(r.get(k)) for k in (*MARKETS,"MIN"))
            or not 0<r["MIN"]<=60 or abs(r["PRA"]-r["PTS"]-r["REB"]-r["AST"])>.01):
            invalid.add(key);continue
        by_match[key].append(r)
    clean=[]
    seen=set()
    rejected=Counter()
    for (d,team,opp),members in sorted(by_match.items()):
        pair=(d,tuple(sorted((team,opp))))
        if pair in seen:continue
        seen.add(pair)
        other=by_match.get((d,opp,team),[])
        if ((d,team,opp) in invalid or (d,opp,team) in invalid):
            rejected["corrupt_team_stats"]+=1;continue
        if min(len(members),len(other))<7:
            rejected["partial_reciprocal_box"]+=1;continue
        if (len({str(r["id"]) for r in members})!=len(members) or
            len({str(r["id"]) for r in other})!=len(other)):
            rejected["duplicate_player_identity"]+=1;continue
        clean.extend(members)
        clean.extend(other)
    clean.sort(key=lambda r:(r["date"],r["team"],str(r["id"])))
    return clean,dict(rejected)

def make_indexes(clean):
    players=defaultdict(list)
    posgame=defaultdict(list)
    game_rows=defaultdict(list)
    for r in clean:
        players[(str(r["id"]),r["team"])].append(r)
        game_rows[(r["date"],r["team"],r["opponent"])].append(r)
    for (d,team,opp),rs in game_rows.items():
        for pos in ("PG","SG","SF","PF","C"):
            matching=[r for r in rs if role(r.get("position"))==pos]
            if matching:
                vals={market:mean(r[market] for r in matching) for market in MARKETS}
                # DEFENSE=opp, i.e. offense by team permitted vs opp
                posgame[(opp,pos)].append((d,vals))
    for k in players:players[k].sort(key=lambda r:r["date"])
    for k in posgame:posgame[k].sort(key=lambda x:x[0])
    return players,posgame

def matchup_projection(row,player_history,posgame,stat,*,min_opponent=MIN_DEFENSE_GAMES,
                       min_league=MIN_LEAGUE_ROLE_GAMES):
    """Both outputs use identical prior player observations, never target data."""
    d=row["date"]
    prior=[x for x in player_history if x["date"]<d]
    if len(prior)<MIN_PLAYER_GAMES:return None
    stable=[role(x.get("position")) for x in prior[-5:]]
    if None in stable or len(set(stable))!=1:return None
    player_role=stable[0]
    opp=row["opponent"]
    opponent_prior=[v[1][stat] for v in posgame.get((opp,player_role),[]) if v[0]<d]
    league_prior=[v[1][stat] for (def_team,pos),vs in posgame.items()
                  if pos==player_role for v in vs if v[0]<d]
    if len(opponent_prior)<min_opponent or len(league_prior)<min_league:
        return None
    prior_base=mean(float(x[stat]) for x in prior[-5:])
    league=mean(league_prior)
    if league<=0:return None
    raw_ratio=mean(opponent_prior[-5:])/league
    # Fixed, predeclared cap avoids enormous small-sample multipliers.
    ratio=max(.85,min(1.15,raw_ratio))
    return prior_base,prior_base*ratio,ratio

def evaluate(rows,*,holdout_days=7,min_opponent=MIN_DEFENSE_GAMES,
             min_league=MIN_LEAGUE_ROLE_GAMES):
    if not 1<=holdout_days<=30:raise ValueError("bad holdout")
    clean,rejected=prepare(rows)
    if not clean:
        return {"status":"NO_RECIPROCAL_GAME_DATA","production_approved":False,
                "rejected":rejected,"markets":{}}
    last=max(date.fromisoformat(r["date"]) for r in clean)
    cutoff=(last-timedelta(days=holdout_days-1)).isoformat()
    players,posgame=make_indexes(clean)
    totals=defaultdict(lambda:{"n":0,"base_absolute":0.0,"candidate_absolute":0.0,
                              "candidate_wins":0,"candidate_losses":0,"ties":0})
    for row in clean:
        if row["date"]<cutoff:continue
        history=players[(str(row["id"]),row["team"])]
        for market in MARKETS:
            out=matchup_projection(row,history,posgame,market,
                                   min_opponent=min_opponent,min_league=min_league)
            if out is None:continue
            base,candidate,_=out
            actual=float(row[market])
            e0=abs(base-actual)
            e1=abs(candidate-actual)
            t=totals[market]
            t["n"]+=1;t["base_absolute"]+=e0;t["candidate_absolute"]+=e1
            if e1<e0:t["candidate_wins"]+=1
            elif e1>e0:t["candidate_losses"]+=1
            else:t["ties"]+=1
    metrics={}
    for market,t in totals.items():
        if not t["n"]:continue
        b=t["base_absolute"]/t["n"]
        c=t["candidate_absolute"]/t["n"]
        metrics[market]={"paired_player_games":t["n"],
                         "player_l5_mae":round(b,4),
                         "position_adjusted_mae":round(c,4),
                         "candidate_mae_improvement":round(b-c,4),
                         "candidate_wins":t["candidate_wins"],
                         "candidate_losses":t["candidate_losses"],
                         "ties":t["ties"]}
    return {"status":"RETROSPECTIVE_DATE_ORDERED_POSITION_ADJUSTMENT_HOLDOUT",
      "holdout_start":cutoff,"holdout_through":last.isoformat(),
      "last_n_days":holdout_days,"reciprocal_player_game_rows":len(clean),
      "paired_markets":metrics,"rejected":rejected,
      "source_available_during_historical_games_verified":False,
      "live_predictions_or_grades_modified":False,
      "production_approved":False,
      "probability_calibrated":False,
      "note":"Each target prediction uses strictly earlier player and opponent data, same player-game compared to L5 baseline. Source is retrospectively published, not a timestamped historical live freeze; statistical MAE is not a calibrated standard-line betting hit probability."}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--logs",default="data/nba/current/current_games.json")
    p.add_argument("--output",default="paired-positional-holdout-research.json")
    a=p.parse_args()
    report=evaluate(json.loads(Path(a.logs).read_text()))
    Path(a.output).write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print(json.dumps({k:report.get(k) for k in
      ("status","holdout_start","holdout_through","reciprocal_player_game_rows",
       "paired_markets","production_approved")},indent=2))
if __name__=="__main__":main()
