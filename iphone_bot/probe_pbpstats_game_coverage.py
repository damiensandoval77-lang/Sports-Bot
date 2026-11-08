"""Single, non-recurring current-season ON/OFF source-consistency research check.

Twelve bounded public GET requests, four per three injury-related pairs:
two dated WOWY requests plus two playing-time distribution requests for
each pair. Strictly one-time research validation, not recurring polling. Raw third-party rows stay in memory;
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
# Three additional injury-related pairs, one-time bounded diagnostic only.
# No licensed data persisted, no recurring ingestion, and no API keys.
PAIRS=(
    ("1628973","1628404","NYK"),  # Brunson / Josh Hart
    ("1630532","1631094","ORL"),  # Franz Wagner / Paolo Banchero
    ("1629027","203076","WAS"),   # Trae Young / Anthony Davis
)
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

def one_time_probe(player_id,teammate_id,team):
    plan=request_plan(player_id,teammate_id,team,cutoff_date=DATE)
    outcome={"checked_at":dt.datetime.now(dt.timezone.utc).isoformat(),
             "season":"2026-27","cutoff":DATE,
             "sample_player_id":player_id,"sample_teammate_id":teammate_id,
             "purpose":"BOUNDED_INJURY_PAIR_GAME_LEVEL_COVERAGE_VALIDATION",
             "raw_player_stats_published":False,"automatic_ingestion_enabled":False,
             "license_asserted":False}
    try:
        wowy={}
        for kind in ("with","without"):
            wowy[kind]=get_json(plan["endpoint"],plan["requests"][kind])
        dist_url="https://api.pbpstats.com/get-playing-time-distribution/nba"
        distributions={}
        for target in (player_id,teammate_id):
            distributions[target]=get_json(dist_url,{
              "TeamId":TEAM_IDS[team],"Season":"2026-27",
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
            "target":time_schema(summarized[player_id]),
            "teammate":time_schema(summarized[teammate_id])}
        coverage=audit_pair(summarized[player_id],summarized[teammate_id],
            player_id=player_id,teammate_id=teammate_id,cutoff_date=DATE,
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
            row=_rows(wowy[kind],player_id)
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
    result={"status":"ONE_TIME_THREE_PAIR_PUBLIC_SOURCE_RESEARCH_ONLY",
       "checked_at":dt.datetime.now(dt.timezone.utc).isoformat(),
       "raw_stats_saved":False,"licensed_use_verified":False,
       "historical_cutoff":DATE,"pairs":[]}
    for player,teammate,team in PAIRS:
        result["pairs"].append(one_time_probe(player,teammate,team))
    OUTPUT.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,sort_keys=True))

if __name__=="__main__":main()
