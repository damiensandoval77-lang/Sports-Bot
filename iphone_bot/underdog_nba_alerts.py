"""Authenticated UnderdogNBA X alert ingestion, no web scraping or fake news.

Uses X's documented API with an optional server-side bearer token. Never
accepts copied tweet text as author proof, and never equates a third-party
post with an official NBA injury report. All events require an exact roster
identity and scheduled pretip team/game match. Sources and error codes
remain visible; no token is ever serialized or logged.
"""
import datetime as dt
import json
import os
import re
import unicodedata
import urllib.error
import urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/"docs/underdog_nba_injury_alerts.json"
UTC=dt.timezone.utc
ET=ZoneInfo("America/New_York")
HANDLE="UnderdogNBA"
STATUS_RE=re.compile(r"\b(ruled\s+out|listed\s+out|downgraded\s+to\s+out|will\s+not\s+play|won't\s+play|not\s+playing|out\s+for\s+(?:tonight|today|monday|tuesday|wednesday|thursday|friday|saturday|sunday)|available\s+to\s+play|will\s+play|upgraded\s+to\s+available|ruled\s+in)\b",re.I)
NEGATE_RE=re.compile(r"\b(not\s+ruled\s+out|hasn't\s+been\s+ruled\s+out|isn't\s+ruled\s+out|questionable|doubtful|probable|game-time\s+decision|not\s+yet\s+ruled\s+out)\b",re.I)

def norm(value):
    s=unicodedata.normalize("NFKD",str(value or "")).casefold()
    return "".join(c for c in s if c.isalnum() and not unicodedata.combining(c))

def utc(value):
    x=dt.datetime.fromisoformat(str(value).replace("Z","+00:00"))
    if x.tzinfo is None:raise ValueError("Need aware post timestamp")
    return x.astimezone(UTC)

def x_get(path,token,query=""):
    req=urllib.request.Request("https://api.x.com"+path+query,headers={
        "Authorization":"Bearer "+token,
        "Accept":"application/json",
        "User-Agent":"SportsBot-Injury-Watch/1.0"})
    with urllib.request.urlopen(req,timeout=12) as response:
        if response.status!=200:raise ValueError("Unexpected X HTTP response")
        body=response.read(450000)
        data=json.loads(body)
        if not isinstance(data,dict):raise ValueError("X response malformed")
        return data

def retrieve(token):
    user=x_get("/2/users/by/username/"+HANDLE,token).get("data",{})
    if str(user.get("username","")).casefold()!=HANDLE.casefold() or not str(user.get("id","")).isdigit():
        raise ValueError("UnderdogNBA account identity unavailable")
    owner=str(user["id"])
    payload=x_get("/2/users/"+owner+"/tweets",token,
                  "?max_results=50&tweet.fields=created_at,author_id,referenced_tweets")
    if not isinstance(payload.get("data",[]),list):raise ValueError("X tweet array invalid")
    verified=[]
    for tweet in payload.get("data",[]):
        if (str(tweet.get("author_id"))==owner and
            str(tweet.get("id","")).isdigit() and
            isinstance(tweet.get("text"),str) and tweet.get("created_at")):
            if any(r.get("type")=="retweeted" for r in tweet.get("referenced_tweets",[])):
                continue
            verified.append(tweet)
    return verified,owner

def player_alerts(posts,roster,schedule,now,*,verified_author_id):
    """A single, explicit player-status tweet + uniquely scheduled match."""
    now=utc(now)
    names={}
    for p in roster:
        name=norm(p.get("player"));team=str(p.get("team","")).upper()
        if not name or len(name)<7 or len(str(p.get("player_id","")))<4:continue
        names.setdefault(name,[]).append(p)
    games={}
    for match in schedule:
        if match.get("game_state")!="pre":continue
        try:tip=utc(match["start"])
        except (ValueError,KeyError,TypeError):continue
        if not now<tip<=now+dt.timedelta(hours=32):continue
        for team in (match.get("home_abbreviation"),match.get("away_abbreviation")):
            games.setdefault(str(team),[]).append(match)
    candidates={}
    for post in posts:
        if str(post.get("author_id"))!=str(verified_author_id):continue
        try:published=utc(post["created_at"])
        except (ValueError,KeyError,TypeError):continue
        if not 0<=(now-published).total_seconds()<=8*3600:continue
        txt=" ".join(post.get("text","").split())
        if NEGATE_RE.search(txt) or not STATUS_RE.search(txt):continue
        # Direct reports only, no quotes, fan questions, multi-player tables,
        # or editorial summaries that may be missing subject/status grammar.
        if txt.startswith("RT ") or len(txt)>300:continue
        matched=[p for name,people in names.items()
                 if re.search(r"(?<![\w])"+re.escape(" ".join(str(people[0]["player"]).split()))+r"(?![\w])",txt,re.I)
                 for p in people]
        if len(matched)!=1:continue
        p=matched[0]
        team=str(p["team"]).upper()
        fixtures=games.get(team,[])
        if len(fixtures)!=1:continue
        event=fixtures[0]
        tip=utc(event["start"])
        if published>=tip:continue
        # Only accept an explicit status attached near the named player;
        # don't misattribute a teammate's OUT to this player.
        m=re.search(re.escape(str(p["player"])),txt,re.I)
        if m is None:continue
        fragment=txt[m.end():m.end()+95]
        fragment=re.sub(r"^\s*\([^)]{0,65}\)\s*"," ",fragment)
        status=STATUS_RE.search(fragment)
        if status is None or status.start()>35:continue
        label="AVAILABLE" if re.search(r"available|will\s+play|ruled\s+in",status.group(),re.I) else "OUT"
        key=(str(p["player_id"]),event["start"])
        alert={"player":p["player"],"player_id":str(p["player_id"]),
          "team":team,"game_id":str(event["id"]),"game":event["game"],
          "game_date":event["date_eastern"],"start":event["start"],"status":label,
          "source":"UNDERDOGNBA_X_VERIFIED_AUTHOR",
          "source_url":"https://x.com/"+HANDLE+"/status/"+str(post["id"]),
          "post_id":str(post["id"]),"posted_at":published.isoformat(),
          "official_nba_confirmed":False,
          "requires_lineup_reprojection":label=="OUT"}
        previous=candidates.get(key)
        if previous is None or alert["posted_at"]>previous["posted_at"]:
            candidates[key]=alert
    return sorted(candidates.values(),key=lambda x:(x["start"],x["team"],x["player"]))

def main():
    now=dt.datetime.now(UTC)
    base={"status":"UNDERDOGNBA_X_MONITOR_NOT_CONFIGURED",
          "generated_at":now.isoformat(),"account":"@"+HANDLE,
          "alerts":[],"verified_x_posts":False,"official_status_verified":False,
          "notice":"X bearer API token required; no tweet monitoring was performed."}
    token=os.environ.get("UNDERDOG_X_BEARER_TOKEN","").strip()
    if token:
        try:
            roster=json.loads((ROOT/"docs/current_form.json").read_text())["players"]
            schedule=json.loads((ROOT/"docs/nba_schedule.json").read_text())["games"]
            posts,user_id=retrieve(token)
            base.update(status="UNDERDOGNBA_X_AUTHENTICATED_POLL",
              verified_x_posts=True,
              alerts=player_alerts(posts,roster,schedule,now,verified_author_id=user_id),
              post_count=len(posts),notice="Third-party reports, not official NBA confirmations.")
        except (ValueError,TypeError,KeyError,OSError,urllib.error.HTTPError,urllib.error.URLError) as e:
            base.update(status="UNDERDOGNBA_X_POLL_FAILED",notice="No new verified tweets could be accepted.",
                        failure_code=type(e).__name__)
    OUTPUT.write_text(json.dumps(base,indent=2)+"\n")
    print("INJURY_X_MONITOR",json.dumps({"status":base["status"],
       "verified_alerts":len(base["alerts"]),"failure_code":base.get("failure_code")}),flush=True)

if __name__=="__main__":main()
