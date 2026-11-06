"""Experimental trained-model comparisons with VERIFIED current NBA market identities.

No claim of calibrated betting odds, EV, injury adjustments or PrizePicks lines.
Only show upcoming two-sided sportsbook markets where the player roster team
matches one of the game's teams. Training feature gaps are flagged.
"""
import json
import re
from datetime import datetime,timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import joblib
import numpy as np
import pandas as pd
from matchup_context import team_allowances, defense_context, minutes_context

ROOT=Path(__file__).resolve().parents[1]
GAMES=ROOT/"data/nba/current/current_games.json"
FORM=ROOT/"docs/current_form.json"
ODDS=ROOT/"docs/data.json"
MODELS=ROOT/"models/nba/provisional"
OUTPUT=ROOT/"docs/ai_comparisons.json"
MARKETS={"Points":"PTS","Rebounds":"REB","Assists":"AST","Points Rebounds Assists":"PRA"}
TEAM={
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
def key(x):return re.sub(r"[^a-z0-9]","",str(x).casefold())
def utc(s):return datetime.fromisoformat(str(s).replace("Z","+00:00")).astimezone(timezone.utc)
def matchup(x):
    parts=str(x).split(" @ ")
    if len(parts)!=2:return None
    away,home=(TEAM.get(x.strip()) for x in parts)
    if not away or not home or away==home:return None
    return away,home
def predict_features(game_rows,game_date,home):
    by_stat={}
    for stat in ("PTS","REB","AST","MIN","FGA","FG3A","TOV"):
        values=[float(r[stat]) for r in game_rows if r.get(stat) is not None]
        if len(values)<5:return None
        by_stat[stat+"_L5"]=float(np.mean(values[-5:]))
        by_stat[stat+"_L10"]=float(np.mean(values[-10:])) if len(values)>=10 else float(np.mean(values))
        by_stat[stat+"_Season"]=float(pd.Series(values).ewm(span=30,adjust=False).mean().iloc[-1])
    dates=[datetime.fromisoformat(r["date"]).date() for r in game_rows]
    gap=(game_date-dates[-1]).days
    if gap<1 or gap>9:return None
    recent7=sum(0<(game_date-d).days<=7 for d in dates)
    last6=sum(0<(game_date-d).days<=6 for d in dates)
    by_stat.update({"DAYS_REST":min(gap,7),"IS_HOME":int(home),"IS_B2B":int(gap==1),
      "IS_FRESH":int(gap>=3),"GAMES_7D":recent7,"IS_4_IN_6":int(last6>=3)})
    return by_stat

def main():
    now=datetime.now(timezone.utc)
    form=json.loads(FORM.read_text())
    odds=json.loads(ODDS.read_text())
    if form.get("season")!="2026-27":raise ValueError("Not current season")
    form_time=utc(form["updated_at"])
    market_time=utc(odds["updated_at"])
    if (now-form_time).total_seconds()>48*3600 or (now-market_time).total_seconds()>6*3600:
        raise SystemExit("Refusing to publish comparisons from stale player stats or market feed")
    if not odds.get("is_live"):raise ValueError("Sportsbook feed not live")
    roster={}
    for player in form["players"]:
        identity=key(player["player"])
        roster.setdefault(identity,[]).append(player)
    by_id={}
    all_games=json.loads(GAMES.read_text())
    for r in all_games:
        by_id.setdefault(str(r["id"]),{})[r["date"]]=r
    raw_markets={}
    skipped={"not_upcoming":0,"team_mismatch":0,"player_ambiguous":0,"insufficient_stats":0,
             "unsupported_market":0,"stale_market_quote":0}
    for r in odds.get("picks",[]):
        stat=MARKETS.get(r.get("stat"))
        if not stat:
            skipped["unsupported_market"]+=1;continue
        try:
            start=utc(r["start"])
            line=float(r["line"])
            updated=utc(r.get("market_updated") or odds["updated_at"])
        except (TypeError,ValueError,KeyError):
            continue
        if start<=now or start>now.replace(hour=23,minute=59)+pd.Timedelta(days=5):
            skipped["not_upcoming"]+=1;continue
        if updated>now+pd.Timedelta(minutes=10) or (now-updated).total_seconds()>6*3600:
            skipped["stale_market_quote"]+=1;continue
        pair=matchup(r.get("game",""))
        player_id=key(r.get("player",""))
        people=roster.get(player_id,[])
        if len(people)!=1:
            skipped["player_ambiguous"]+=1;continue
        person=people[0]
        if not pair or person["team"] not in pair:
            skipped["team_mismatch"]+=1;continue
        side=r.get("direction")
        if side not in ("More","Less"):continue
        game_date=start.astimezone(ZoneInfo("America/New_York")).date()
        history=sorted(by_id.get(str(person["player_id"]),{}).values(),key=lambda x:x["date"])
        history=[g for g in history if datetime.fromisoformat(g["date"]).date()<game_date]
        if len(history)<5:
            skipped["insufficient_stats"]+=1;continue
        features=predict_features(history,game_date,person["team"]==pair[1])
        if features is None:
            skipped["insufficient_stats"]+=1;continue
        market_key=(person["player_id"],stat,line,r.get("source",""),r["start"])
        market=raw_markets.setdefault(market_key,{"player":person["player"],"player_id":str(person["player_id"]),"team":person["team"],
           "stat":stat,"line":line,"sportsbook":r.get("source",""),"game":r.get("game",""),
           "start":r["start"],"over_odds":None,"under_odds":None,"features":features,
           "sample_games":len(history),"last_game":history[-1]["date"]})
        market["over_odds" if side=="More" else "under_odds"]=r.get("odds")
    valid=[v for v in raw_markets.values() if isinstance(v["over_odds"],int) and isinstance(v["under_odds"],int)]
    models={}
    for target in ("PTS","REB","AST","PRA"):
        models[target]=joblib.load(MODELS/f"{target}_model.joblib")
    defense_cache={}
    for row in valid:
        target=row["stat"];model=models[target]
        features=model["features"];fill=model["fill_values"]
        input_data={name:row["features"].get(name,fill.get(name,0)) for name in features}
        x=pd.DataFrame([input_data])[features].apply(pd.to_numeric,errors="coerce").fillna(0)
        projection=max(0,float(model["model"].predict(x)[0]))
        # Source-derived matchup context is descriptive only: the historical
        # models were NOT trained with opponent defensive features.
        pair=matchup(row["game"])
        upcoming_date=utc(row["start"]).astimezone(ZoneInfo("America/New_York")).date().isoformat()
        if upcoming_date not in defense_cache:
            defense_cache[upcoming_date]=team_allowances(all_games,upcoming_date)
        opponent=pair[0] if pair[1]==row["team"] else pair[1]
        row["opponent"]=opponent
        row["opponent_defense"]=defense_context(defense_cache[upcoming_date],opponent,target)
        history=sorted(by_id.get(str(row["player_id"]),{}).values(),key=lambda x:x["date"])
        history=[g for g in history if g["date"]<upcoming_date]
        row["minutes_context"]=minutes_context(history)
        row["injury_status"]="NOT_VERIFIED"
        row["requires_lineup_review"]=True
        row["defense_in_model"]=False
        row["projection"]=round(projection,1)
        row["difference"]=round(projection-row["line"],1)
        row["lean"]="Over" if row["difference"]>0 else "Under" if row["difference"]<0 else "Neutral"
        row["missing_features"]=[name for name in features if name not in row["features"]]
        del row["features"]
    valid.sort(key=lambda r:abs(r["difference"]),reverse=True)
    output={"generated_at":now.isoformat(),"last_form_update":form["updated_at"],
       "last_odds_update":odds["updated_at"],"status":"EXPERIMENTAL_NON_CALIBRATED",
       "verified_current_matchups":True,"is_prizepicks":False,
       "injury_data_verified":False,"opponent_defense_applied_to_model":False,
       "disclaimer":"Experimental historical-model point estimates with DESCRIPTIVE recent opponent team totals and observed minutes context. Defense is not a trained input or projection adjustment. Injury status is not verified; lineup review required. Not calibrated hit probabilities, +EV, or PrizePicks lines.",
       "comparisons":valid[:150],"skipped":skipped}
    OUTPUT.write_text(json.dumps(output,indent=2)+"\n")
    print("Wrote",len(valid),"team-verified experimental model comparisons",flush=True)
    print("With descriptive opponent defense",sum(v["opponent_defense"] is not None for v in valid),flush=True)
    print("Rejected/unavailable",skipped,flush=True)

if __name__=="__main__":main()
