"""Research-only exact pregame join: NBA minutes, listed-position allowance and injury.

No bets, no past-line frequencies, no synthetic availability, and NO promotion
into the published Hit Estimate. Joins independently captured as-of features
only for exact scheduled player/team/opponent/game identities.
"""
import argparse
import json
from collections import Counter
from datetime import datetime,timezone
from math import isfinite
from pathlib import Path

REMAINING = ("usage_opportunities","teammate_availability",
             "depth_role","pace_possessions")
STATS=("PTS","REB","AST","PRA")

def stamp(value):
    if not isinstance(value,str):raise ValueError("timestamp missing")
    t=datetime.fromisoformat(value.replace("Z","+00:00"))
    if t.tzinfo is None:raise ValueError("timezone missing")
    return t.astimezone(timezone.utc)

def key(p):
    return (str(p.get("game_id") or ""),str(p.get("player_id") or ""),
            str(p.get("team") or ""),str(p.get("opponent") or ""))

def index(rows, what):
    out={}
    for r in rows:
        k=key(r)
        if not all(k):
            raise ValueError("incomplete "+what+" identity")
        if k in out:raise ValueError("ambiguous duplicate "+what+" identity")
        out[k]=r
    return out

def assemble(evidence, minutes, defense, *, captured_at):
    now=stamp(captured_at)
    for item in (evidence,minutes.get("prospective",{}),defense):
        moment=stamp(item["captured_at"])
        if moment>now:raise ValueError("postcapture source")
    if (evidence.get("status")!="SOURCE_LINKED_PREGAME_RESEARCH_ONLY" or
        minutes.get("prospective",{}).get("status")!="RESEARCH_MINUTES_ONLY" or
        defense.get("status")!="POSITIONAL_BOX_SCORE_RESEARCH_ONLY"):
        raise ValueError("unexpected source status")
    if (evidence.get("production_hit_estimate_eligible") or
        minutes["prospective"].get("production_approved") or
        defense.get("production_hit_estimate_eligible")):
        raise ValueError("unexpected research promotion")
    minu=index(minutes["prospective"]["predictions"],"minutes")
    positions=[]
    for game in defense["future_games"]:
        for p in game["player_positional_context"]:
            positions.append({**p,"game_id":game["game_id"],"start":game["start"]})
    pos=index(positions,"position defense")
    known_games={str(g["game_id"]):g for g in evidence.get("future_games",[])}
    results=[]
    missing=Counter()
    for player in evidence.get("research_players",[]):
        k=key(player)
        game=known_games.get(k[0])
        if not game or game["start"]!=player["start"] or not (
           {k[2],k[3]}=={game["home"],game["away"]}):
            missing["unmatched_fixture"]+=1;continue
        if stamp(game["start"])<=now:
            missing["game_started_before_joint_capture"]+=1;continue
        p=pos.get(k)
        m=minu.get(k)
        if not p:missing["no_position_source"]+=1
        if not m:missing["no_pretip_minutes_model"]+=1
        if p and (p["start"]!=game["start"] or stamp(p["source_observed_at"])>now):
            raise ValueError("position source mismatched or future")
        if m and (m["start"]!=game["start"] or stamp(m["captured_at"])>now):
            raise ValueError("minutes source mismatched or future")
        if m and m["source_published_at"]!=player["minutes_source_published_at"]:
            raise ValueError("incompatible player source versions")
        candidate={}
        if p and p.get("status")=="THIRD_PARTY_LISTED_POSITION_ALLOWANCE_RESEARCH":
            baseline=p.get("league_listed_position_baseline")
            allowed=p.get("defense_last5_per_listed_player")
            if not isinstance(baseline,dict) or not isinstance(allowed,dict):
                raise ValueError("position source missing comparable rates")
            for stat in STATS:
                b,a=baseline.get(stat),allowed.get(stat)
                if (type(b) not in (int,float) or not isfinite(b) or b<=0 or
                    type(a) not in (int,float) or not isfinite(a) or a<0):
                    raise ValueError("invalid defense context rate")
                candidate[stat]=round(a/b,4)
        if not candidate:missing["no_sampled_position_rates"]+=1
        if player.get("injury_status")=="UNKNOWN_NOT_LISTED":
            missing["player_injury_unlisted"]+=1
        details={
            "game_id":k[0],"player_id":k[1],"team":k[2],"opponent":k[3],
            "start":game["start"],"captured_at":captured_at,
            "player_injury_status":player.get("injury_status"),
            "observed_minutes_last3":player.get("observed_minutes_last3"),
            "research_minutes_forecast":m.get("predicted_minutes_research") if m else None,
            "minutes_model_id":m.get("model_id") if m else None,
            "listed_position":p.get("listed_position") if p else None,
            "opponent_defense_sample_games":p.get("defense_games") if p else 0,
            "opponent_position_allowance_ratio_by_stat_research":candidate or None,
            "model_validated_position_effect":False,
            "asof_source_times":{
                "player_form":player.get("minutes_source_published_at"),
                "position_source":p.get("source_observed_at") if p else None,
                "minutes_snapshot":m.get("captured_at") if m else None,
                "injury_report":player.get("injury_report_issued_at")},
            "missing_required_model_factors":list(REMAINING),
            "opponent_aware_hit_estimate_ready":False,
            "production_approved":False}
        results.append(details)
    return {"status":"SOURCED_MATCHUP_CONTEXT_RESEARCH_NOT_LIVE",
      "captured_at":captured_at,
      "player_records":results,"record_count":len(results),
      "players_with_both_position_and_minutes":sum(x["research_minutes_forecast"] is not None
          and x["opponent_position_allowance_ratio_by_stat_research"] is not None
          for x in results),
      "blockers":dict(sorted(missing.items())),
      "remaining_unverified":list(REMAINING),
      "production_hit_estimate_eligible":False,
      "probabilities_generated":0,
      "note":"These ratios are descriptive per listed position and observational minutes forecasts. Effects not fitted or calibrated. Same-game identity and source-as-of validated; no retroactive pick modification."}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--evidence",default="pregame-evidence-research.json")
    parser.add_argument("--minutes",default="minutes-forecast-research.json")
    parser.add_argument("--position",default="positional-defense-research.json")
    parser.add_argument("--output",default="joined-matchup-features-research.json")
    args=parser.parse_args()
    data=assemble(json.loads(Path(args.evidence).read_text()),
       json.loads(Path(args.minutes).read_text()),
       json.loads(Path(args.position).read_text()),
       captured_at=datetime.now(timezone.utc).isoformat())
    Path(args.output).write_text(json.dumps(data,indent=2,sort_keys=True)+"\n")
    print(json.dumps({k:data[k] for k in ("status","record_count",
       "players_with_both_position_and_minutes","blockers",
       "production_hit_estimate_eligible","probabilities_generated")},indent=2))

if __name__=="__main__":main()
