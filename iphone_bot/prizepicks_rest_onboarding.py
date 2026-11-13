"""One-time authenticated PrizePicks REST onboarding and model-data sample.

Runs ONLY in a server-side GitHub Actions runner. The secret is read from
PRIZEPICKS_API_KEY, never committed, printed, or sent to the browser.
CSV data and diagnostic summaries are artifacts; only redacted health may
be committed. All authenticated REST calls include X-User-Request.
"""
import csv
import io
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime,timezone
from pathlib import Path

BASE="https://prizepicksapi.com"
CONTEXT="Set up PrizePicks API for NBA prop model training, historical game logs, grading and price comparison"
OUT=Path(os.getenv("PRIZEPICKS_SETUP_OUTPUT","artifacts/prizepicks_rest_setup"))
OUT.mkdir(parents=True,exist_ok=True)
KEY=os.getenv("PRIZEPICKS_API_KEY","").strip()

def put_json(name,data):
    (OUT/name).write_text(json.dumps(data,indent=2,ensure_ascii=False)+"\n")

def fetch(path,params=None,post=None):
    if not KEY:raise RuntimeError("MISSING_PRIZEPICKS_API_KEY")
    url=BASE+path
    if params:
        url+="?"+urllib.parse.urlencode(params)
    headers={"Authorization":"Bearer "+KEY,
             "X-User-Request":urllib.parse.quote(CONTEXT,safe=" -_,."),
             "Accept":"application/json",
             "User-Agent":"Sports-Bot-NBA-Research/1.0"}
    data=None
    if post is not None:
        data=json.dumps(post).encode("utf-8")
        headers["Content-Type"]="application/json"
    req=urllib.request.Request(url,data=data,headers=headers,
                               method="POST" if post is not None else "GET")
    try:
        with urllib.request.urlopen(req,timeout=25) as response:
            raw=response.read(2_000_000)
            return response.status,json.loads(raw),{
                "remaining_credits":response.headers.get("X-Credits-Remaining"),
                "usage_unit":response.headers.get("X-Usage-Unit"),
                "plan_limit":response.headers.get("X-Plan-Limit"),
                "observed_at":response.headers.get("Date")}
    except urllib.error.HTTPError as err:
        # Never echo raw provider error bodies, which may contain echoed headers.
        return err.code,{"error":"HTTP_"+str(err.code)},{"remaining_credits":
                    err.headers.get("X-Credits-Remaining"),"usage_unit":
                    err.headers.get("X-Usage-Unit"),
                    "plan_limit":err.headers.get("X-Plan-Limit")}

def nested(row,*names):
    for name in names:
        val=row
        for key in name.split("."):
            val=val.get(key) if isinstance(val,dict) else None
        if val not in (None,""):return val
    return None

def csvfile(name,records):
    if not records:return
    cols=sorted({str(k) for row in records for k in row})
    with (OUT/name).open("w",newline="",encoding="utf-8") as f:
        writer=csv.DictWriter(f,fieldnames=cols,extrasaction="ignore")
        writer.writeheader()
        for row in records:
            writer.writerow({k:json.dumps(row[k],ensure_ascii=False)
                             if isinstance(row.get(k),(list,dict))
                             else row.get(k,"") for k in cols})

def flatten_game(g):
    player=nested(g,"player.name","player")
    stats=g.get("stats") or {}
    return {"game_date":g.get("game_date"),
            "stats_player_id":nested(g,"player.stats_player_id","stats_player_id"),
            "stats_event_id":g.get("stats_event_id"),
            "player":player,
            "team":nested(g,"team.abbreviation","team"),
            "opponent":nested(g,"opponent.abbreviation","opponent"),
            "minutes":g.get("minutes"),"points":stats.get("points"),
            "assists":stats.get("assists"),"rebounds":stats.get("rebounds"),
            "confirmed":g.get("confirmed")}

def parse_date(value):
    try:return datetime.fromisoformat(str(value)[:10]).date()
    except (TypeError,ValueError):return None

def first_join(samples,logs):
    """Join by provider stats id when available, otherwise exact name + team.

    Every input game must have a date strictly BEFORE the recorded prop
    start. Never use target outcome, minutes, actual or postgame labels
    as an input feature.
    """
    # Prefer assists/rebounds for the bot's immediate model-development work.
    ranking={"Assists":0,"Rebounds":1,"Points":2}
    candidates=sorted(samples,key=lambda r:ranking.get(str(r.get("stat")),10))
    for r in candidates:
        player_id=nested(r,"stats_player_id","player.stats_player_id")
        player=nested(r,"player","player_name")
        if isinstance(player,dict):player=player.get("name")
        player=str(player or "").strip().casefold()
        team=str(nested(r,"team","player.team") or "").strip().upper()
        day=parse_date(nested(r,"game_date","date"))
        if not day or not player:continue
        prior=[]
        for g in logs:
            gday=parse_date(g.get("game_date"))
            if not gday or gday>=day:continue
            if (player_id and g.get("stats_player_id")==player_id) or (
                not player_id and str(g.get("player") or "").strip().casefold()==player and
                str(g.get("team") or "").strip().upper()==team):
                prior.append(g)
        prior.sort(key=lambda x:x["game_date"])
        if not prior:continue
        tail=prior[-5:]
        def av(k):
            numbers=[float(x[k]) for x in tail if x.get(k) is not None]
            return round(sum(numbers)/len(numbers),3) if numbers else None
        return {"game_date":day.isoformat(),"player":nested(r,"player","player_name"),
                "stats_player_id":prior[-1].get("stats_player_id"),
                "join_method":"STATS_PLAYER_ID" if player_id else "EXACT_PLAYER_NAME_AND_TEAM",
                "training_projection_id":nested(r,"projection_id","id"),
                "stat":nested(r,"stat","market.stat"),
                "closing_line":nested(r,"closing_line","line"),
                "closing_observed_at":r.get("closing_observed_at"),
                "label_result":r.get("result"),
                "prior_games":len(tail),
                "last_prior_game":tail[-1]["game_date"],
                "prior_points_mean":av("points"),"prior_assists_mean":av("assists"),
                "prior_rebounds_mean":av("rebounds"),
                "actual_value_label_only":r.get("actual_value"),
                "leakage_safe":True}
    return None

def main():
    report={"status":"STARTED","checked_at":datetime.now(timezone.utc).isoformat(),
            "provider":"prizepicksapi.com",
            "data_wanted":"NBA PrizePicks prop lines and tiers, recorded timestamps and line history, graded labeled player props, prior game box scores, and matching sportsbook price comparisons",
            "use_case":"Sports-Bot iPhone NBA prop prediction research: train and backtest assists, rebounds, points and PRA, archive pretip projections, and grade outcomes",
            "training_rows":0,"game_log_rows":0,"earlier_game_join":None,
            "observed_at":None,
            "key_logged":False,"key_committed":False}
    if not KEY:
        report["status"]="MISSING_KEY"
        put_json("setup_status.json",report)
        print("PrizePicks REST setup: MISSING_KEY (set GitHub Actions secret PRIZEPICKS_API_KEY)")
        return 2
    try:
        # How the user discovered the API is intentionally omitted unless
        # explicitly supplied; user found_us is never inferred.
        onboard={"agent":"Other agent","data_wanted":report["data_wanted"],
                 "use_case":report["use_case"]}
        status,body,headers=fetch("/api/v1/onboarding",post=onboard)
        report["onboarding_http"]=status
        report["onboarding_status"]="OK" if status in (200,201,204) else "HTTP_"+str(status)
        # Setup should not depend on an unrelated optional onboarding survey.
        if status not in (200,201,204):
            report["status"]="ONBOARDING_FAILED"
            put_json("setup_status.json",report)
            print("PrizePicks onboarding returned HTTP",status)
            return 1
        status,coverage,headers=fetch("/api/v1/coverage")
        report["coverage_http"]=status
        if status!=200:
            report["status"]="COVERAGE_FAILED"
            put_json("setup_status.json",report)
            print("PrizePicks coverage returned HTTP",status)
            return 1
        meta=coverage.get("meta") or {}
        report["coverage"]={"observed_at":nested(meta,"coverage_at","observed_at",
                  "latest_observation_at") or nested(coverage,"coverage_at"),
                 "source_status":meta.get("source_status"),
                 "stats_leagues":meta.get("stats_leagues"),
                 "top_level_keys":sorted(coverage.keys())}
        report["observed_at"]=report["coverage"]["observed_at"]
        # Fixed small Free-compatible request, avoiding large paid pagination.
        status,training,headers=fetch("/api/v1/training-set",
                 {"league":"NBA","tier":"standard","limit":20,"format":"json"})
        report["training_http"]=status
        report["remaining_credits"]=headers.get("remaining_credits")
        if status!=200:
            report["status"]="TRAINING_SAMPLE_UNAVAILABLE"
            report["plan_limit"]=headers.get("plan_limit")
            put_json("setup_status.json",report)
            print("PrizePicks training sample returned HTTP",status,
                  "see setup status; no key or response body logged")
            return 0
        samples=training.get("data") or []
        report["training_rows"]=len(samples)
        report["training_meta"]={k:(training.get("meta") or {}).get(k) for k in
             ("count","next_cursor","plan_limit","source_status")}
        csvfile("nba_training_sample.csv",samples)
        logs=[]
        attempted=[]
        # Find an athlete with an observed stats id; request at most two
        # separate athletes to establish an earlier-game join.
        for row in samples:
            player_id=nested(row,"stats_player_id","player.stats_player_id")
            player=nested(row,"player","player_name")
            if isinstance(player,dict):player=player.get("name")
            identity=str(player_id or player or "")
            if not identity or identity in attempted:continue
            attempted.append(identity)
            params={"league":"NBA","last":10}
            if player_id:params["player_id"]=str(player_id)
            else:params["player"]=str(player)
            code,game_data,gh=fetch("/api/v1/game-logs",params)
            report["game_logs_http"]=code
            if code==200:
                logs.extend(flatten_game(x) for x in game_data.get("data",[])
                            if isinstance(x,dict))
            if len(attempted)>=2 or first_join(samples,logs):
                break
        csvfile("nba_prior_game_logs.csv",logs)
        report["game_log_rows"]=len(logs)
        join=first_join(samples,logs)
        report["earlier_game_join"]=join
        if join:csvfile("nba_earlier_game_feature_join.csv",[join])
        report["status"]="SAMPLE_AND_PRIOR_GAMES_READY" if join else (
            "SAMPLE_READY_NO_EARLIER_GAME_JOIN" if samples else
            "NO_TRAINING_ROWS_RETURNED")
        print("PrizePicks REST setup:",report["status"],
              "training_rows=",len(samples),"game_log_rows=",len(logs),
              "earlier_game_join=",bool(join))
        put_json("setup_status.json",report)
        return 0
    except (OSError,ValueError,TypeError) as error:
        # Suppress URL and request headers; keep only the exception class.
        report["status"]="TRANSPORT_OR_SCHEMA_ERROR"
        report["error_type"]=type(error).__name__
        put_json("setup_status.json",report)
        print("PrizePicks REST setup:",report["status"],report["error_type"])
        return 1

if __name__=="__main__":sys.exit(main())
