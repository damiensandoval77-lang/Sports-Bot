"""Read-only live ESPN NBA scoreboard/summary smoke check.

Runs on GitHub Actions, no sportsbook API key, no predictions touched.
If there is no active or completed game today, report SKIPPED rather than
pretending the tracker was tested against a boxscore.
"""
import datetime as dt
import json
import urllib.request
from zoneinfo import ZoneInfo

BASE="https://site.api.espn.com/apis/site/v2/sports/basketball/nba"
ET=ZoneInfo("America/New_York")

def get(path):
    request=urllib.request.Request(BASE+path,headers={
        "User-Agent":"Mozilla/5.0",
        "Accept":"application/json"})
    with urllib.request.urlopen(request,timeout=20) as response:
        return json.load(response)

def game_name(event):
    sides=event.get("competitions",[{}])[0].get("competitors",[])
    by={x.get("homeAway"):x.get("team",{}).get("displayName") for x in sides}
    return f'{by.get("away")} @ {by.get("home")}' if by.get("away") and by.get("home") else None

def main():
    day=dt.datetime.now(dt.timezone.utc).astimezone(ET).strftime("%Y%m%d")
    board=get("/scoreboard?dates="+day+"&limit=100")
    games=board.get("events",[])
    print("ESPN scoreboard:",day,"games",len(games))
    if not games:raise RuntimeError("Scoreboard returned no games for today's slate")
    eligible=[e for e in games if e.get("status",{}).get("type",{}).get("state") in ("in","post")]
    if not eligible:
        print("NO LIVE/FINAL GAME YET; scoreboard reachable, boxscore smoke deferred")
        return
    # Prefer active game: test user-facing current player totals.
    eligible.sort(key=lambda e:e.get("status",{}).get("type",{}).get("state")!="in")
    event=eligible[0]
    event_id=str(event.get("id",""))
    if not event_id.isdecimal():raise RuntimeError("Invalid ESPN event ID")
    summary=get("/summary?event="+event_id)
    name=game_name(event)
    header=summary.get("header",{}).get("competitions",[])
    if not header:raise RuntimeError("Summary missing competition header")
    name2=game_name({"competitions":header})
    if not name or name!=name2:raise RuntimeError("Summary matchup does not match scoreboard")
    players=summary.get("boxscore",{}).get("players",[])
    print("Summary:",event_id,name,"state",event["status"]["type"]["state"],
          "team boxscore groups",len(players))
    if not players:raise RuntimeError("No player boxscore groups in active/finished game")
    count=0
    for group in players:
        for statblock in group.get("statistics",[]):
            labels=statblock.get("labels",[])
            if all(key in labels for key in ("PTS","REB","AST")):
                count+=len(statblock.get("athletes",[]))
    print("ESPN PTS/REB/AST-ready player rows:",count)
    if count==0:raise RuntimeError("No statblock with PTS, REB and AST labels")
    print("LIVE ESPN BOX SCORE SMOKE PASSED (read-only; no simulated predictions)")

if __name__=="__main__":main()
