"""Single, non-recurring current-season ON/OFF source-consistency research check.

Five bounded public GET requests: two dated WOWY requests, two time-distribution
requests, one current-season game-list request (if needed in later revisions).
This version makes only FOUR requests. Raw third-party rows stay in memory;
publish only derived count/coverage diagnostics. Never enable paid/live model
ingestion from a reachability test.
"""
import datetime as dt
import json
import pathlib
import urllib.error
import urllib.parse
import urllib.request
try:
    from .pbpstats_request_plan import request_plan,TEAM_IDS
    from .pbpstats_game_coverage import audit_pair
    from .pbpstats_wowy_adapter import _rows
    from .lineup_onoff_research import positive
except ImportError:
    from pbpstats_request_plan import request_plan,TEAM_IDS
    from pbpstats_game_coverage import audit_pair
    from pbpstats_wowy_adapter import _rows
    from lineup_onoff_research import positive

ROOT=pathlib.Path(__file__).resolve().parents[1]
OUTPUT=ROOT/"docs/pbpstats_onoff_coverage_probe.json"
MAX_BYTES=5*1024*1024
PLAYER="201939"       # Example: one pair, not the entire league
TEAMMATE="203110"
TEAM="GSW"
DATE="2026-11-06"

def get_json(url,params):
    request=urllib.request.Request(
        url+"?"+urllib.parse.urlencode(params),
        headers={"Accept":"application/json","User-Agent":"SportsBot-OneTime-Lineup-Research/1.0"})
    with urllib.request.urlopen(request,timeout=18) as result:
        if result.status!=200:
            raise ValueError("HTTP "+str(result.status))
        data=result.read(MAX_BYTES+1)
        if len(data)>MAX_BYTES:raise ValueError("Response exceeds safe diagnostic size")
        return json.loads(data)

def one_time_probe():
    plan=request_plan(PLAYER,TEAMMATE,TEAM,cutoff_date=DATE)
    outcome={"checked_at":dt.datetime.now(dt.timezone.utc).isoformat(),
             "season":"2026-27","cutoff":DATE,
             "sample_player_id":PLAYER,"sample_teammate_id":TEAMMATE,
             "purpose":"SINGLE_PAIR_GAME_LEVEL_COVERAGE_VALIDATION",
             "raw_player_stats_published":False,"automatic_ingestion_enabled":False,
             "license_asserted":False}
    try:
        wowy={}
        for kind in ("with","without"):
            wowy[kind]=get_json(plan["endpoint"],plan["requests"][kind])
        dist_url="https://api.pbpstats.com/get-playing-time-distribution/nba"
        distributions={}
        for target in (PLAYER,TEAMMATE):
            distributions[target]=get_json(dist_url,{
              "TeamId":TEAM_IDS[TEAM],"Season":"2026-27",
              "SeasonType":"Regular Season","PlayerId":target})
        summarized={}
        for target,payload in distributions.items():
            if not isinstance(payload,dict) or not isinstance(payload.get("results"),list):
                raise ValueError("Distribution response missing list of games")
            games=[r for r in payload["results"] if isinstance(r,dict)
                 and str(r.get("Date",""))<=DATE]
            summarized[target]=[{**r,"PlayerId":target} for r in games]
        def time_schema(items):
            start=[];end=[];invalid=0;examples=[]
            for g in items:
                for p in g.get("Possessions",[]):
                    a=p.get("StartTime");b=p.get("EndTime")
                    if isinstance(a,(int,float)) and isinstance(b,(int,float)):
                        start.append(a);end.append(b)
                        if not(0<=a<b<=4000):
                            invalid+=1
                            if len(examples)<3:
                                examples.append({"start":a,"end":b,"duration":b-a})
            return {"game_count":len(items),"interval_count":len(start),
                    "min_start":min(start) if start else None,
                    "max_start":max(start) if start else None,
                    "min_end":min(end) if end else None,
                    "max_end":max(end) if end else None,
                    "invalid_range_count":invalid,
                    "example_ranges":examples}
        outcome["time_schema"]={
            "target":time_schema(summarized[PLAYER]),
            "teammate":time_schema(summarized[TEAMMATE])}
        coverage=audit_pair(summarized[PLAYER],summarized[TEAMMATE],
            player_id=PLAYER,teammate_id=TEAMMATE,cutoff_date=DATE,
            min_games=1,min_minutes=1)
        outcome["game_level_coverage"]={
            "status":coverage["status"],
            "with_games":coverage["with"]["games"],
            "without_games":coverage["without"]["games"],
            "with_minutes":coverage["with"]["minutes"],
            "without_minutes":coverage["without"]["minutes"],
            "meets_model_sample_threshold":all(
              coverage[k]["games"]>=5 and coverage[k]["minutes"]>=120
              for k in ("with","without"))}
        comparison={}
        for kind in ("with","without"):
            row=_rows(wowy[kind],PLAYER)
            seconds=positive(row.get("SecondsPlayed"))
            minutes=seconds/60 if seconds is not None else positive(row.get("Minutes"))
            independent=coverage[kind]["minutes"]
            comparison[kind]={"target_entity_unique":True,
              "provider_minutes":round(minutes,4) if minutes is not None else None,
              "independent_minutes":independent,
              "minute_difference":round(abs(minutes-independent),4) if minutes is not None else None,
              "minutes_reconcile":minutes is not None and
                abs(minutes-independent)<=max(3,.03*independent)}
        outcome["provider_minutes_comparison"]=comparison
        outcome["status"]="RECONCILED" if all(x["minutes_reconcile"] for x in comparison.values()) else "COVERAGE_MISMATCH"
    except (ValueError,KeyError,TypeError,urllib.error.HTTPError,urllib.error.URLError,TimeoutError,OSError) as error:
        outcome["status"]="NOT_VALIDATED"
        outcome["error_type"]=type(error).__name__
        outcome["error_summary"]=str(error)[:140] if isinstance(error,ValueError) else None
    return outcome

def main():
    result=one_time_probe()
    OUTPUT.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,sort_keys=True))

if __name__=="__main__":main()
