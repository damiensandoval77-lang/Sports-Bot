"""Research-only current-season player prop baselines, independently refreshed.

Allows the AI Board to show honest, pregame *form-baseline* comparisons on
all available sportsbook games without pretending to run the trained AI model.
No odds-derived projection, calibrated probability, injury adjustment, or wager.
"""
import json
import math
from collections import defaultdict
from datetime import datetime,timezone
from pathlib import Path
from statistics import median
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
FORM=ROOT/"docs/current_form.json"
ODDS=ROOT/"docs/odds_compact.json"
OUT=ROOT/"docs/ai_form_fallback.json"
TEAM={
"Atlanta Hawks":"ATL","Boston Celtics":"BOS","Brooklyn Nets":"BKN",
"Charlotte Hornets":"CHA","Chicago Bulls":"CHI","Cleveland Cavaliers":"CLE",
"Dallas Mavericks":"DAL","Denver Nuggets":"DEN","Detroit Pistons":"DET",
"Golden State Warriors":"GSW","Houston Rockets":"HOU","Indiana Pacers":"IND",
"LA Clippers":"LAC","Los Angeles Clippers":"LAC","Los Angeles Lakers":"LAL",
"Memphis Grizzlies":"MEM","Miami Heat":"MIA","Milwaukee Bucks":"MIL",
"Minnesota Timberwolves":"MIN","New Orleans Pelicans":"NOP","New York Knicks":"NYK",
"Oklahoma City Thunder":"OKC","Orlando Magic":"ORL","Philadelphia 76ers":"PHI",
"Phoenix Suns":"PHX","Portland Trail Blazers":"POR","Sacramento Kings":"SAC",
"San Antonio Spurs":"SAS","Toronto Raptors":"TOR","Utah Jazz":"UTA",
"Washington Wizards":"WAS"}
MARKETS={"Points":"PTS","Rebounds":"REB","Assists":"AST",
         "Points Rebounds Assists":"PRA"}

def key(name):
    return "".join(c for c in str(name).casefold() if c.isalnum())

def number(value):
    if value is None or isinstance(value,bool):return None
    try:v=float(value)
    except (ValueError,TypeError):return None
    return v if math.isfinite(v) and v>=0 else None

def baseline(form,stat):
    if form.get("games",0)<5:return None
    data=form.get("metrics",{}).get(stat,{})
    recent=number(data.get("l5"))
    season=number(data.get("season"))
    longer=number(data.get("l10"))
    if recent is None or season is None:return None
    # Fixed formula chosen ahead of research results; no same-day outcomes.
    estimate=.50*recent+.30*(longer if longer is not None else season)+.20*season
    return round(max(0,estimate),2)

def build(form,odds,now=None):
    if now is None:now=datetime.now(timezone.utc)
    updated=datetime.fromisoformat(odds["updated_at"].replace("Z","+00:00"))
    form_updated=datetime.fromisoformat(form["updated_at"].replace("Z","+00:00"))
    if form.get("season")!="2026-27":raise ValueError("Current-season form required")
    if (now-updated).total_seconds()>6*3600 or (now-form_updated).total_seconds()>48*3600:
        raise ValueError("Refusing to publish fallback from stale sources")
    if not odds.get("is_live") or odds.get("source")!="THE_ODDS_API_VERIFIED_COMPACT_PLAYER_PROPS":
        raise ValueError("Only real paired sportsbook markets allowed")
    roster=defaultdict(list)
    for p in form.get("players",[]):roster[key(p.get("player",""))].append(p)
    pairs=defaultdict(dict)
    skipped=defaultdict(int)
    for r in odds.get("picks",[]):
        market=MARKETS.get(r.get("stat"))
        if not market:
            skipped["unsupported_market"]+=1;continue
        game=r.get("game","")
        teams=game.split(" @ ")
        if len(teams)!=2 or teams[0] not in TEAM or teams[1] not in TEAM:
            skipped["unknown_team"]+=1;continue
        try:
            start=datetime.fromisoformat(r["start"].replace("Z","+00:00"))
            line=number(r.get("line"))
            price=int(r.get("odds"))
            if start.tzinfo is None:raise ValueError("Naive game date")
        except (ValueError,TypeError,KeyError):
            skipped["invalid_quote"]+=1;continue
        if start<=now:
            skipped["already_started"]+=1;continue
        if start>now.replace(hour=23,minute=59)+__import__("datetime").timedelta(days=2):
            skipped["distant_game"]+=1;continue
        if line is None or price==0:
            skipped["invalid_quote"]+=1;continue
        people=roster.get(key(r.get("player")),[])
        if len(people)!=1:
            skipped["ambiguous_player"]+=1;continue
        p=people[0]
        if p.get("team") not in {TEAM[teams[0]],TEAM[teams[1]]}:
            skipped["team_mismatch"]+=1;continue
        predicted=baseline(p,market)
        if predicted is None:
            skipped["insufficient_history"]+=1;continue
        side=r.get("direction")
        if side not in ("More","Less"):continue
        bucket=(str(p["player_id"]),game,r["start"],market)
        source=str(r.get("source",""))
        if not source:continue
        quote_key=(source,line)
        item=pairs[bucket].setdefault(quote_key,{
            "player":p["player"],"player_id":str(p["player_id"]),"team":p["team"],
            "game":game,"start":r["start"],"stat":market,
            "line":line,"source":source,"projection":predicted,
            "sample_games":p["games"],"latest_game":p.get("latest_game"),
            "over":None,"under":None})
        item["over" if side=="More" else "under"]=price
    output=[]
    for _,books in pairs.items():
        valid=[b for b in books.values() if b["over"] is not None and b["under"] is not None]
        if not valid:continue
        # One live line per book, then median by independent books.
        unique={}
        for q in valid:unique.setdefault(q["source"].casefold(),q)
        entries=list(unique.values())
        mid=float(median(b["line"] for b in entries))
        first=entries[0]
        combined=first["projection"]
        output.append({
            "player":first["player"],"player_id":first["player_id"],"team":first["team"],
            "game":first["game"],"start":first["start"],"stat":first["stat"],
            "line":mid,"projection":combined,"combined_projection":combined,
            "difference":round(combined-mid,2),
            "combined_model_count":0,"sample_games":first["sample_games"],
            "sportsbook":("Consensus ("+str(len(entries))+" books)" if len(entries)>1 else first["source"]),
            "line_book_count":len(entries),
            "line_type":"MULTIBOOK_MEDIAN" if len(entries)>1 else "SINGLE_BOOK_FALLBACK",
            "book_quotes":[{"name":b["source"],"line":b["line"],
                            "over":b["over"],"under":b["under"]} for b in entries],
            "over_odds":entries[0]["over"] if len(entries)==1 else None,
            "under_odds":entries[0]["under"] if len(entries)==1 else None,
            "projection_source":"CURRENT_SEASON_FORM_BASELINE_NOT_TRAINED_AI",
            "estimated_selected_probability":None,"probability_method":"UNAVAILABLE",
            "injury_status":"NOT_VERIFIED",
            "injury_status_source":"UNAVAILABLE_OR_NOT_GAME_DAY",
            "requires_lineup_review":True,
            "minutes_context":None,"minutes_research":None,
            "projection_explanation":{"sentences":[
                "This is a recent-form baseline, not the trained NBA AI.",
                "It combines current-season last-five, last-ten when available, and season averages.",
                "Opponent rotation and player availability are not verified."]}})
    output.sort(key=lambda x:(x["start"],x["game"],x["player"],x["stat"]))
    covered={r["game"] for r in output}
    return {"generated_at":now.isoformat(),
            "status":"FORM_BASELINE_RESEARCH_ONLY",
            "source":"2026-27 observed player-game aggregates + paired real sportsbook odds",
            "sportsbook_updated_at":odds["updated_at"],
            "form_updated_at":form["updated_at"],
            "verified_current_matchups":True,
            "is_trained_ai":False,
            "probabilities_calibrated":False,
            "live_ai_model_unchanged":True,
            "comparisons":output,
            "comparison_rows_published":len(output),
            "games_with_fallback":len(covered),
            "skipped":dict(skipped),
            "method":"0.50*L5 + 0.30*L10-or-season + 0.20*season; no sportsbook-driven projection"}


def main():
    report=build(json.loads(FORM.read_text()),json.loads(ODDS.read_text()))
    OUT.write_text(json.dumps(report,separators=(",",":"))+"\n",encoding="utf-8")
    print("Form-based NBA research:",len(report["comparisons"]),
          "markets on",report["games_with_fallback"],"games",flush=True)
    print("Skipped:",report["skipped"],flush=True)


if __name__=="__main__":main()
