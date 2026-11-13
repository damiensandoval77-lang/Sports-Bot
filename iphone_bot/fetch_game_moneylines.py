"""Publicly publish real NBA sportsbook h2h moneyline quotes from The Odds API.

Only exact, two-sided, pregame sportsbook quotes. No model probabilities, no
synthetic lines, no PrizePicks claims. No API key is exposed to the browser.
"""
import datetime as dt
import json
import math
import os
import pathlib
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=ROOT/"docs/game_moneylines.json"
STATUS=ROOT/"docs/game_moneylines_status.json"
URL="https://api.the-odds-api.com/v4/sports/basketball_nba/odds/"
ET=ZoneInfo("America/New_York")


def american(price):
    if isinstance(price,bool):return None
    try:
        n=float(price)
        if not math.isfinite(n) or not n.is_integer():return None
        val=int(n)
        return val if val<=-100 or val>=100 else None
    except (TypeError,ValueError):return None


def parse_event(event,now=None):
    now=now or dt.datetime.now(dt.timezone.utc)
    try:
        start=dt.datetime.fromisoformat(str(event["commence_time"]).replace("Z","+00:00"))
        if start.tzinfo is None or start<=now:return None
        away=str(event["away_team"]).strip()
        home=str(event["home_team"]).strip()
        if not away or not home or away==home:return None
        offers=[]
        for book in event.get("bookmakers",[]):
            bookmaker=str(book.get("title") or book.get("key") or "").strip()
            if not bookmaker:continue
            for market in book.get("markets",[]):
                if market.get("key")!="h2h":continue
                quotes={}
                for selection in market.get("outcomes",[]):
                    name=str(selection.get("name","")).strip()
                    odds=american(selection.get("price"))
                    if name in (away,home) and odds is not None:quotes[name]=odds
                if len(quotes)!=2:continue
                updated=market.get("last_update") or book.get("last_update")
                if not updated:continue
                timestamp=dt.datetime.fromisoformat(str(updated).replace("Z","+00:00"))
                if timestamp.tzinfo is None or timestamp>now+dt.timedelta(minutes=2):continue
                if (now-timestamp).total_seconds()>6*3600:continue
                offers.append({"sportsbook":bookmaker,"away_ml":quotes[away],
                               "home_ml":quotes[home],"updated_at":timestamp.isoformat()})
        if not offers:return None
        offers.sort(key=lambda x:(x["sportsbook"].casefold(),x["updated_at"]))
        return {"game":away+" @ "+home,"away":away,"home":home,
                "start":start.isoformat(),
                "date_eastern":start.astimezone(ET).date().isoformat(),
                "books":offers}
    except (KeyError,TypeError,ValueError,AttributeError):
        return None


def build(events,now=None):
    now=now or dt.datetime.now(dt.timezone.utc)
    if not isinstance(events,list):raise ValueError("Odds provider returned invalid event collection")
    games=[r for item in events if (r:=parse_event(item,now)) is not None]
    games.sort(key=lambda g:(g["start"],g["game"]))
    return {"status":"VERIFIED_PREGAME_NBA_MONEYLINES","updated_at":now.isoformat(),
            "source":"The Odds API h2h sportsbook market",
            "is_live":True,"markets":["h2h"],"games":games,
            "note":"Real pregame sportsbook quotes only; may be unavailable or stale after tipoff. Moneyline is not a modeled hit percentage."}


def request(key):
    query=urllib.parse.urlencode({"apiKey":key,"regions":"us",
        "markets":"h2h","oddsFormat":"american","dateFormat":"iso"})
    req=urllib.request.Request(URL+"?"+query,headers={"User-Agent":"Sports-Bot/2.0"})
    with urllib.request.urlopen(req,timeout=20) as response:
        return json.load(response),response.headers.get("x-requests-remaining")


def status(value,**details):
    STATUS.write_text(json.dumps({"updated_at":dt.datetime.now(dt.timezone.utc).isoformat(),
                   "status":value,**details},indent=2)+"\n")


def main():
    if os.environ.get("SPORTS_BOT_ENABLE_PAID_ODDS") != "1":
        status("PAID_ODDS_POLLING_DISABLED", old_lines_may_be_stale=True)
        print("Paid moneyline polling disabled; preserving prior observations.",flush=True)
        return
    key=os.getenv("ODDS_API_KEY","").strip()
    if not key:
        status("MISSING_ODDS_API_KEY")
        print("Moneyline refresh skipped: no key",flush=True)
        return
    try:
        events,remaining=request(key)
        report=build(events)
        OUT.write_text(json.dumps(report,indent=2)+"\n")
        status("MONEYLINES_FETCHED",games=len(report["games"]),
               books=sum(len(g["books"]) for g in report["games"]),
               remaining_provider_credits=remaining)
        print("NBA moneylines:",len(report["games"]),"games; remaining:",remaining,flush=True)
    except (OSError,ValueError,TypeError,KeyError) as e:
        status("MONEYLINE_PROVIDER_UNAVAILABLE",error_type=type(e).__name__)
        print("Moneylines unavailable; existing quotes will expire in browser:",type(e).__name__,flush=True)


if __name__=="__main__":main()
