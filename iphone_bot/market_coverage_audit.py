"""Explain why two-sided listed NBA sportsbook markets lack an AI card.

Audit only. Never invent missing lines or player projections. Compare exact
current-season identities using the same Unicode-normalized matcher as the AI.
Report eligible player/market coverage per game and explicit failure reasons.
"""
import json
from collections import Counter,defaultdict
from datetime import datetime,timezone
from pathlib import Path
try:
    from .compare_live_models import key,matchup
except ImportError:
    from compare_live_models import key,matchup

ROOT=Path(__file__).resolve().parents[1]
ODDS=ROOT/"docs/odds_compact.json"
FORM=ROOT/"docs/current_form.json"
BOARD=ROOT/"docs/ai_comparisons.json"
OUT=ROOT/"docs/ai_market_coverage.json"

def audit(odds,form,board):
    roster=defaultdict(list)
    for p in form.get("players",[]):
        roster[key(p.get("player"))].append(p)
    cards={(str(c.get("player_id")),c.get("stat"),c.get("game")) for c in board.get("comparisons",[])}
    paired=defaultdict(set)
    metadata={}
    types={"Points":"PTS","Rebounds":"REB","Assists":"AST","Points Rebounds Assists":"PRA"}
    for q in odds.get("picks",[]):
        stat=types.get(q.get("stat"))
        if not stat or not q.get("game") or not q.get("start"):continue
        identity=(key(q.get("player")),stat,q["game"],q["start"],str(q.get("source")),q.get("line"))
        paired[identity].add(q.get("direction"))
        metadata[identity]=q
    by_game=defaultdict(lambda:{"listed":0,"published":0,"missing":[],"reasons":Counter()})
    for ident,sides in sorted(paired.items(),key=lambda x:str(x[0])):
        if not {"More","Less"}.issubset(sides):continue
        norm,stat,game,start,book,line=ident
        bucket=by_game[game]
        people=roster.get(norm,[])
        match=matchup(game)
        if len(people)!=1:
            reason="PLAYER_ABSENT_FROM_FORM" if len(people)==0 else "AMBIGUOUS_PLAYER_IDENTITY"
            person_id=None
        elif not match or people[0].get("team") not in match:
            reason="ROSTER_TEAM_MISMATCH";person_id=str(people[0].get("player_id"))
        else:
            person_id=str(people[0].get("player_id"))
            reason="PUBLISHED" if (person_id,stat,game) in cards else "NOT_PUBLISHED"
        bucket["listed"]+=1
        bucket["reasons"][reason]+=1
        if reason=="PUBLISHED":bucket["published"]+=1
        else:
            q=metadata[ident]
            bucket["missing"].append({"player":q.get("player"),"stat":stat,
                 "book":book,"line":line,"reason":reason,
                 "player_id":person_id})
    games={}
    for name,v in sorted(by_game.items()):
        seen=set();missing=[]
        for item in v["missing"]:
            marker=(item["player"],item["stat"],item["reason"])
            if marker in seen:continue
            seen.add(marker);missing.append(item)
        games[name]={"paired_listed_books":v["listed"],
            "paired_published_books":v["published"],
            "coverage_pct":round(100*v["published"]/v["listed"],1) if v["listed"] else None,
            "reasons":dict(v["reasons"]),
            "missing_unique_player_markets":missing[:200]}
    return {"status":"DESCRIPTIVE_MARKET_COVERAGE_NOT_A_MODEL_PREDICTION",
       "generated_at":datetime.now(timezone.utc).isoformat(),
       "odds_source_time":odds.get("updated_at"),"ai_board_time":board.get("generated_at"),
       "note":"Includes quoted games that may now be in progress or stale; compare source times before interpreting omissions.",
       "games":games,
       "limitations":["Matched published cards are not guarantees of current sportsbook availability.",
          "Unmatched player names, team mismatches, insufficient games, stale quotes, and unavailable model features require independent diagnosis.",
          "Does not modify or fabricate sports prices or forecasts."]}

def main():
    data=audit(json.loads(ODDS.read_text()),json.loads(FORM.read_text()),
               json.loads(BOARD.read_text()))
    OUT.write_text(json.dumps(data,indent=2)+"\n")
    print("MARKET COVERAGE",json.dumps({g:{"listed":v["paired_listed_books"],
        "matched":v["paired_published_books"],"reasons":v["reasons"]}
        for g,v in data["games"].items()},sort_keys=True))

if __name__=="__main__":main()
