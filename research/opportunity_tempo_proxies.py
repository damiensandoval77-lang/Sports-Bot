"""Prospective, descriptive opponent tempo and shot involvement from real completed boxes.

Research-only. FGA+TOV is NOT official USG%, touches, or possessions; no FTA,
OREB, lineup/starter, injury split or true pace available from this local source.
Never substitute these proxies for validated full Hit Estimate factors.
"""
import argparse
import json
from collections import Counter,defaultdict
from datetime import datetime,timezone
from pathlib import Path
from statistics import mean

MIN_PLAYERS=7
MIN_GAMES=5

def when(s):
    if not isinstance(s,str):raise ValueError("timestamp missing")
    t=datetime.fromisoformat(s.replace("Z","+00:00"))
    if t.tzinfo is None:raise ValueError("naive timestamp")
    return t.astimezone(timezone.utc)

def num(v):
    return type(v) in (float,int) and 0<=v<float("inf")

def build(logs,form,joined,*,captured_at):
    now=when(captured_at)
    if when(form["updated_at"])>now or when(joined["captured_at"])>now:
        raise ValueError("future source")
    if form.get("season")!="2026-27" or joined.get("status")!="SOURCED_MATCHUP_CONTEXT_RESEARCH_NOT_LIVE":
        raise ValueError("source mismatch")
    if not form.get("source_url") or joined.get("production_hit_estimate_eligible") is not False:
        raise ValueError("source/provenance unverifiable")
    if not isinstance(logs,list):raise ValueError("missing game log")
    raw=defaultdict(list)
    unsafe=set()
    for r in logs:
        if not isinstance(r,dict):continue
        day,team,opp,pid=r.get("date"),r.get("team"),r.get("opponent"),str(r.get("id") or "")
        if not day or not team or not opp or team==opp or not pid:continue
        k=(day,team,opp)
        if any(not num(r.get(x)) for x in ("FGA","TOV","MIN")) or r["MIN"]<=0 or r["MIN"]>60:
            unsafe.add(k);continue
        raw[k].append(r)
    by_game=defaultdict(list)
    for (day,team,opp),members in raw.items():
        if (day,team,opp) in unsafe:continue
        if len(members)<MIN_PLAYERS or len({str(x["id"]) for x in members})!=len(members):
            continue
        rev=raw.get((day,opp,team),[])
        if (day,opp,team) in unsafe or len(rev)<MIN_PLAYERS or len({str(x["id"]) for x in rev})!=len(rev):
            continue
        total=sum(float(x["FGA"])+float(x["TOV"]) for x in members)
        other=sum(float(x["FGA"])+float(x["TOV"]) for x in rev)
        if total<=0 or other<=0:continue
        key=(day,team,opp)
        shares={str(x["id"]):(float(x["FGA"])+float(x["TOV"]))/total for x in members}
        by_game[(team,opp)].append((day,total,other,shares))
    for k in by_game:by_game[k].sort(key=lambda x:x[0])
    outputs=[]
    missing=Counter()
    identities=set()
    for rec in joined["player_records"]:
        gid,pid,team,opp=map(str,[rec.get("game_id"),rec.get("player_id"),
                                  rec.get("team"),rec.get("opponent")])
        identity=(gid,pid,team,opp)
        if identity in identities:raise ValueError("ambiguous joined player identity")
        identities.add(identity)
        if when(rec["start"])<=now:continue
        if when(rec["captured_at"])>now:raise ValueError("joined record after capture")
        day=rec["start"][:10]
        # Derive the explicit matchup's original ET day from the joined game
        # only after validating its game ID; source features still filter earlier dates.
        date=rec.get("date_eastern")
        if not date:
            from zoneinfo import ZoneInfo
            date=when(rec["start"]).astimezone(ZoneInfo("America/New_York")).date().isoformat()
        relevant=[x for x in by_game.get((team,opp),[]) if x[0]<date]
        # Player opportunity can use team games against ANY prior opponent, not
        # just previous games against today's opponent.
        all_team=[v for (t,o),series in by_game.items() if t==team for v in series if v[0]<date]
        all_team.sort(key=lambda x:x[0])
        all_opp=[v for (t,o),series in by_game.items() if t==opp for v in series if v[0]<date]
        all_opp.sort(key=lambda x:x[0])
        team_last=all_team[-MIN_GAMES:]
        opp_last=all_opp[-MIN_GAMES:]
        player_shares=[v[3][pid] for v in all_team if pid in v[3]][-MIN_GAMES:]
        shot_share=round(mean(player_shares),4) if len(player_shares)>=MIN_GAMES else None
        # Each team's own FGA+TOV per completed game: activity index, not actual pace.
        tempo=(round((mean(v[1] for v in team_last)+mean(v[1] for v in opp_last))/2,3)
               if len(team_last)>=MIN_GAMES and len(opp_last)>=MIN_GAMES else None)
        if shot_share is None:missing["insufficient_player_shot_involvement_games"]+=1
        if tempo is None:missing["insufficient_team_tempo_proxy_games"]+=1
        outputs.append({"game_id":gid,"player_id":pid,"team":team,"opponent":opp,
          "start":rec["start"],"captured_at":captured_at,
          "source":form["source_url"],"source_updated_at":form["updated_at"],
          "fga_plus_tov_share_research":shot_share,
          "fga_plus_tov_team_activity_index":tempo,
          "is_official_usage_pct":False,"is_verified_possessions_pace":False,
          "teammate_injury_usage_adjustment":None,
          "depth_chart_starter_evidence":None,
          "production_hit_estimate_eligible":False})
    return {"status":"OPPORTUNITY_TEMPO_PROXY_RESEARCH_ONLY","captured_at":captured_at,
      "records":outputs,"count":len(outputs),
      "with_both_descriptive_proxies":sum(x["fga_plus_tov_share_research"] is not None
        and x["fga_plus_tov_team_activity_index"] is not None for x in outputs),
      "blockers":dict(sorted(missing.items())),
      "true_usage_pct_attested":False,"true_possessions_pace_attested":False,
      "verified_teammate_splits":False,"verified_depth_chart":False,
      "production_hit_estimate_eligible":False,
      "note":"Do not treat FGA+TOV as USG% or pace in possessions/48; proxies are not approved model factors."}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--logs",default="data/nba/current/current_games.json")
    p.add_argument("--form",default="docs/current_form.json")
    p.add_argument("--joined",default="joined-matchup-features-research.json")
    p.add_argument("--output",default="opportunity-tempo-research.json")
    a=p.parse_args()
    r=build(json.loads(Path(a.logs).read_text()),json.loads(Path(a.form).read_text()),
      json.loads(Path(a.joined).read_text()),captured_at=datetime.now(timezone.utc).isoformat())
    Path(a.output).write_text(json.dumps(r,indent=2,sort_keys=True)+"\n")
    print(json.dumps({k:r[k] for k in ("status","count","with_both_descriptive_proxies",
            "blockers","production_hit_estimate_eligible")},indent=2))
if __name__=="__main__":main()
