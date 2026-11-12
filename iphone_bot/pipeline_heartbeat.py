"""Compare deployed Dame's Picks feeds with game schedule and frozen records."""
import datetime as dt
import json
import sys
import urllib.request
from pathlib import Path

SITE="https://damiensandoval77-lang.github.io/Sports-Bot"
FILES=["prizepicks.json","prizepicks_site.json","lagged_matchup_all_market_ledger.json",
       "lagged_matchup_live_all_markets.json","nba_schedule.json",
       "nba_scoreboard_independent.json","nba_player_tracking_independent.json"]
REPAIR={"lines_publish":"nba-prizepicks-site-publish.yml",
        "picks_frozen":"nba-new-ai-all-markets.yml",
        "live_scores":"independent_scoreboard_refresh.yml",
        "live_players":"independent_nba_player_boxscores.yml",
        "settlement":"nba-new-ai-multimarket-grade.yml"}
def ts(value):
    try:
        v=dt.datetime.fromisoformat(str(value).replace("Z","+00:00"))
        return v if v.tzinfo else v.replace(tzinfo=dt.timezone.utc)
    except (ValueError,TypeError):return None
def age(now,value):
    v=ts(value)
    return (now-v).total_seconds()/60 if v else None
def check(name,status,detail,**evidence):
    return {"stage":name,"status":status,"detail":detail,"recovery_workflow":REPAIR.get(name),"evidence":evidence}
def evaluate(now,site,espn=None):
    out=[]
    pp=site.get("prizepicks.json") or {}
    published=site.get("prizepicks_site.json") or {}
    ledger=site.get("lagged_matchup_all_market_ledger.json") or {}
    model=site.get("lagged_matchup_live_all_markets.json") or {}
    schedule=site.get("nba_schedule.json") or {}
    p_at=ts(pp.get("generated_at"))
    s_at=ts(published.get("source_generated_at") or published.get("generated_at"))
    lag=(p_at-s_at).total_seconds()/60 if p_at and s_at else None
    out.append(check("lines_publish","FAIL" if not s_at or (lag is not None and lag>45) else "OK",
                     "Published line snapshot freshness",lag_minutes=lag))
    soon=[]
    for game in schedule.get("games",[]):
        start=ts(game.get("start"))
        if start and -3*3600 <= (start-now).total_seconds() <=6*3600 and game.get("game"):
            soon.append((game["game"],start))
    a=age(now,pp.get("generated_at"))
    out.append(check("lines_fresh","WARN" if soon and (a is None or a>240) else "OK",
                     "Source line age; paid provider refresh is alert-only",age_minutes=a))
    lines={v.get("game") for d in (pp,published) for v in d.get("board_offers",[]) if isinstance(v,dict)}
    frozen={(r.get("game"),ts(r.get("start"))) for r in ledger.get("records",[]) if ts(r.get("start"))}
    missing=[(g,s) for g,s in soon if g in lines and (g,s) not in frozen]
    failures=[f"{g} @ {s.isoformat()}" for g,s in missing if (s-now).total_seconds()<=3*3600]
    warnings=[f"{g} @ {s.isoformat()}" for g,s in missing if (s-now).total_seconds()>3*3600]
    model_at=ts(model.get("generated_at"))
    current=bool(model_at and s_at and model_at>=s_at)
    # A recent model timestamp is not proof of complete per-game capture.
    # Near-tip missing picks must still page recovery even when model ran.
    st="FAIL" if failures else "WARN" if warnings else "OK"
    missing_detail={g:(model.get("game_diagnostics") or {}).get(g) for g,_ in missing}
    out.append(check("picks_frozen",st,"Missing picks by game; model current does not prove every game was covered",
                     missing=failures+warnings,model_after_lines=current,
                     excluded_by_game=missing_detail))
    live=[]
    for event in (espn or {}).get("events",[]):
        if event.get("status",{}).get("type",{}).get("state")!="in":continue
        competitors=event.get("competitions",[{}])[0].get("competitors",[])
        name={c.get("homeAway"):c.get("team",{}).get("displayName") for c in competitors}
        if name.get("away") and name.get("home"):live.append(f"{name['away']} @ {name['home']}")
    scores=site.get("nba_scoreboard_independent.json") or {}
    score_games={g.get("game") for g in scores.get("games",[]) if g.get("game_state")=="in"}
    score_age=age(now,scores.get("generated_at"))
    bad=bool(live and (score_age is None or score_age>30 or not set(live)<=score_games))
    out.append(check("live_scores","FAIL" if bad else "OK","Live scoreboard coverage",
                     live=live,age_minutes=score_age,missing=sorted(set(live)-score_games)))
    players=site.get("nba_player_tracking_independent.json") or {}
    player_games={g.get("game") for g in players.get("games",[]) if g.get("player_rows")}
    player_age=age(now,players.get("captured_at"))
    bad=bool(live and (player_age is None or player_age>30 or not set(live)<=player_games))
    out.append(check("live_players","FAIL" if bad else "OK","Live player-box coverage",
                     age_minutes=player_age,missing=sorted(set(live)-player_games)))
    overdue=[r for r in ledger.get("records",[]) if r.get("grade")=="PENDING"
             and ts(r.get("start")) and (now-ts(r["start"])).total_seconds()>8*3600]
    out.append(check("settlement","FAIL" if overdue else "OK","Unsettled picks >8h after tip",
                     count=len(overdue),games=sorted({r.get("game") for r in overdue})[:15]))
    overall="FAIL" if any(x["status"]=="FAIL" for x in out) else "WARN" if any(x["status"]=="WARN" for x in out) else "OK"
    return {"checked_at":now.isoformat(),"overall":overall,"site":SITE,"stages":out}
def fetch(url):
    req=urllib.request.Request(url+"?hb="+str(int(dt.datetime.now().timestamp())),headers={"Cache-Control":"no-cache","User-Agent":"DamesPicks-Heartbeat"})
    with urllib.request.urlopen(req,timeout=20) as response:return json.load(response)
def main():
    site={}
    for name in FILES:
        try:site[name]=fetch(f"{SITE}/{name}")
        except Exception as exc:
            print("Unreadable deployed feed",name,str(exc),file=sys.stderr)
            site[name]=None
    try:espn=fetch("https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard")
    except Exception:espn=None
    result=evaluate(dt.datetime.now(dt.timezone.utc),site,espn)
    dest=Path(sys.argv[1] if len(sys.argv)>1 else "pipeline_heartbeat.json")
    dest.write_text(json.dumps(result,indent=2)+"\n")
    print(result["overall"],[(x["stage"],x["status"]) for x in result["stages"]])
    return 1 if result["overall"]=="FAIL" else 0
if __name__=="__main__":raise SystemExit(main())
