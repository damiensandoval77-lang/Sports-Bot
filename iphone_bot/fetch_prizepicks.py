"""Optional independent PrizePicks board feed alongside existing sportsbook odds.

Never reads PrizePicks private endpoints, never calls demo data for live display,
and never treats pick'em payout multipliers as sportsbook American odds.
Set PRIZEPICKS_API_KEY in GitHub Actions secrets. Server-side only.
"""
import datetime as dt
import json
import math
import os
from pathlib import Path
import unicodedata
import urllib.error
import urllib.parse
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/"docs/prizepicks.json"
BASE="https://prizepicksapi.com/api/v1/projections"
STAT={"points":"PTS","rebounds":"REB","assists":"AST",
      "pts+rebs+asts":"PRA","pts+reb+ast":"PRA","points rebounds assists":"PRA",
      "points+rebounds+assists":"PRA","pts reb ast":"PRA"}
MAX_PAGES=3  # Limit free-plan API requests; a partial result is clearly labeled.

def timeparse(value):
    try:
        d=dt.datetime.fromisoformat(str(value).replace("Z","+00:00"))
        return d.astimezone(dt.timezone.utc) if d.tzinfo else None
    except (TypeError,ValueError):return None

def norm(value):
    s=unicodedata.normalize("NFKD",str(value or ""))
    return "".join(c for c in s.lower() if c.isalnum() and not unicodedata.combining(c))

def numeric(value):
    try:
        n=float(value)
        return n if math.isfinite(n) and n>=0 else None
    except (ValueError,TypeError):return None

def team_abbrev(s):
    if isinstance(s,dict):
        return str(s.get("abbreviation") or s.get("team") or "").strip().upper()
    return str(s or "").strip().upper()

def clean(row,now,verified_live=False):
    if not isinstance(row,dict) or row.get("is_demo") is True or row.get("status")!="active":return None
    # Compact production rows may omit is_demo. Only accept that case after
    # confirming the authenticated production endpoint meta.mode is live.
    if row.get("is_demo") is None and not verified_live:return None
    if str(row.get("league","")).upper()!="NBA":return None
    player=row.get("player",{})
    event=row.get("event",{})
    market=row.get("market",{})
    if isinstance(player,str):player={"name":player,"team":row.get("team")}
    if not isinstance(player,dict):return None
    if not isinstance(event,dict):event={}
    if not isinstance(market,dict):market={"stat":row.get("stat"),"period":row.get("period")}
    stat=STAT.get(str(market.get("stat") or row.get("stat") or "").lower().strip())
    period=str(market.get("period") or row.get("period") or "").strip().lower()
    if period not in ("full game","full_game","fullgame"):return None
    raw_starts=event.get("starts_at") or row.get("event_starts_at")
    starts=timeparse(raw_starts)
    observed=timeparse(row.get("observed_at"))
    if not observed or observed>now+dt.timedelta(minutes=10):return None
    if starts and starts<=now:return None
    # Vendor records may be old even if a cached endpoint says active.
    if now-observed>dt.timedelta(hours=6):return None
    if row.get("is_live") is True or row.get("in_game") is True:return None
    fields=row.get("source_fields") or {}
    if not isinstance(fields,dict):fields={}
    if fields.get("is_promo") is True or row.get("is_promo") is True:return None
    line=numeric(row.get("line"))
    if line is None:return None
    selections=row.get("selections")
    if not isinstance(selections,list):
        selections=[]
        for side in ("more","less"):
            if row.get(side+"_available") is True:
                selections.append({"side":side,"available":True,"tier":row.get(side+"_tier")})
    picks={}
    for sel in selections:
        if not isinstance(sel,dict) or sel.get("available") is not True:continue
        side=str(sel.get("side","")).lower()
        tier=str(sel.get("tier","")).lower()
        if side in ("more","less") and tier in ("standard","goblin","demon"):
            picks[side]=tier
    if not picks:return None
    name=str(player.get("name") or "").strip()
    team=team_abbrev(player.get("team"))
    opponent=team_abbrev(event.get("opponent") or row.get("opponent"))
    if not name or len(team)!=3 or (opponent and team==opponent):return None
    return {"id":str(row.get("id","")),"player":name,"team":team,
            "opponent":opponent,"stat":stat,"line":line,
            "starts_at":starts.isoformat() if starts else None,"observed_at":observed.isoformat(),
            "more_tier":picks.get("more"),"less_tier":picks.get("less"),
            "source":"independent_prizepicksapi_com","is_demo":False}

def match(offer,comparison):
    """Require team + complete player name + stat + opponent + close start."""
    if norm(offer["player"])!=norm(comparison.get("player")):return False
    if offer["team"]!=str(comparison.get("team","")).upper():return False
    if offer["stat"]!=comparison.get("stat"):return False
    start=timeparse(comparison.get("start"))
    other=timeparse(offer.get("starts_at"))
    if not start or start<=dt.datetime.now(dt.timezone.utc):return False
    from iphone_bot.paper_pick_pipeline import expected_opponents
    verified=expected_opponents(comparison.get("game"),offer["team"])
    if not verified:return False
    if offer["opponent"] and offer["opponent"] not in verified:return False
    if other:
        if abs((start-other).total_seconds())>3*3600:return False
        return bool(offer["opponent"]) or abs((start-other).total_seconds())<=30*60
    # A third-party offer without a game time can only match a fully named
    # opponent + verified upcoming team game, never player/name alone.
    return bool(offer["opponent"]) and offer["opponent"] in verified

def rejection_hint(row,now,verified_live=False):
    """Count rejection categories without publishing private provider rows."""
    if not isinstance(row,dict):return "non_object"
    if row.get("is_demo") is True or (row.get("is_demo") is None and not verified_live):return "missing_real_provenance"
    if row.get("status")!="active" or str(row.get("league","")).upper()!="NBA":return "inactive_or_not_nba"
    event=row.get("event") if isinstance(row.get("event"),dict) else {}
    start=timeparse(event.get("starts_at") or row.get("event_starts_at"))
    if start and start<=now:return "game_already_started"
    observed=timeparse(row.get("observed_at"))
    if observed is None:return "missing_observed_time"
    if now-observed>dt.timedelta(hours=6):return "observation_older_than_six_hours"
    market=row.get("market") if isinstance(row.get("market"),dict) else {}
    period=str(market.get("period") or row.get("period") or "").strip().lower()
    if period not in ("full game","full_game","fullgame"):return "not_full_game_market"
    stat=str(market.get("stat") or row.get("stat") or "").lower().strip()
    if stat not in STAT:return "unsupported_stat"
    player=row.get("player")
    team=player.get("team") if isinstance(player,dict) else row.get("team")
    if not team or len(team_abbrev(team))!=3:return "missing_team"
    if not start and not (event.get("opponent") or row.get("opponent")):return "missing_game_time_and_opponent"
    return "invalid_or_unavailable_selection"

def publish(raw_pages,comparisons,now=None):
    now=now or dt.datetime.now(dt.timezone.utc)
    offers=[]
    raw_count=0
    from collections import Counter
    rejection_reasons=Counter()
    statuses=[]
    cursors=[]
    for page in raw_pages:
        meta=page.get("meta",{})
        if meta.get("mode")!="live":raise ValueError("Refuse demo or unknown mode")
        if meta.get("source_status") in ("failed","stale","partial"):
            raise ValueError("Provider source is not fresh")
        statuses.append(meta.get("source_status","unknown"))
        cursors.append(meta.get("next_cursor"))
        rows=page.get("data",[])
        if not isinstance(rows,list):raise ValueError("Invalid projection rows")
        raw_count+=len(rows)
        for row in rows:
            cleaned=clean(row,now,verified_live=True)
            if cleaned:offers.append(cleaned)
            else:rejection_reasons[rejection_hint(row,now,verified_live=True)]+=1
    distinct={o["id"]:o for o in offers if o["id"]}
    matched=[]
    unmatched=0
    for comparison in comparisons:
        suitable=[o for o in distinct.values() if match(o,comparison)]
        if not suitable:
            unmatched+=1
            continue
        # The same projection may carry multiple selectable tiers; preserve them.
        for o in suitable:
            projection=numeric(comparison.get("combined_projection"))
            if projection is None:projection=numeric(comparison.get("projection"))
            matched.append(dict(o,starts_at=o["starts_at"] or comparison["start"],
                event_start_source="provider" if o["starts_at"] else "verified_internal_schedule",
                combined_projection=projection,
                difference=round(projection-o["line"],2) if projection is not None else None,
                ai_direction="MORE" if projection is not None and projection>o["line"] else
                             "LESS" if projection is not None and projection<o["line"] else "NO LEAN"))
    return {"status":"LIVE_THIRD_PARTY_PRIZEPICKS_LINES" if matched else "LIVE_NO_MATCHED_PRIZEPICKS_LINES",
        "source":"Independent prizepicksapi.com (not affiliated with PrizePicks)",
        "source_url":"https://prizepicksapi.com/docs",
        "generated_at":now.isoformat(),
        "provider_status":statuses[0] if statuses else "unknown",
        "pages_read":len(raw_pages),"partial_board":bool(cursors and cursors[-1]),
        "raw_rows_read":raw_count,"eligible_upcoming_offers":len(distinct),
        "filtered_out_reasons":dict(sorted(rejection_reasons.items())),
        "match_method":"EXACT_PLAYER_TEAM_STAT_AND_VERIFIED_SCHEDULE_OR_30_MIN_TIPOFF",
        "matched_count":len(matched),"unmatched_ai_comparisons":unmatched,
        "offers":matched,
        "notice":"Read-only third-party observations. May lag the app. FanDuel odds and EV are separate; PrizePicks pick'em lines are NOT American-odds quotes."}

def read_url(url,key):
    req=urllib.request.Request(url,headers={
        "Authorization":"Bearer "+key,
        "Accept":"application/json",
        "X-User-Request":"Read NBA PrizePicks lines for Sports-Bot dashboard comparison"})
    with urllib.request.urlopen(req,timeout=30) as reply:
        return json.load(reply)

def main():
    key=os.environ.get("PRIZEPICKS_API_KEY","").strip()
    if not key:
        out={"status":"NOT_CONFIGURED","generated_at":dt.datetime.now(dt.timezone.utc).isoformat(),
             "offers":[],"matched_count":0,
             "notice":"Add PRIZEPICKS_API_KEY as a GitHub Actions repository secret to enable this independent feed. FanDuel continues unchanged."}
        DEST.write_text(json.dumps(out,indent=2)+"\n")
        print("PrizePicks API key missing; publishing NOT_CONFIGURED status, no vendor request.",flush=True)
        return
    comp=json.loads((ROOT/"docs/ai_comparisons.json").read_text())
    if comp.get("status")!="EXPERIMENTAL_NON_CALIBRATED":
        raise ValueError("AI comparison source invalid")
    # Search only players we can actually compare, rather than consuming
    # monthly credits on 3,000 unrelated rows from the ID-ordered board.
    # The full JSON shape retains event/selection context missing in compact.
    names=[]
    for comparison in comp["comparisons"]:
        name=str(comparison.get("player","")).strip()
        if name and name not in names:names.append(name)
        if len(names)>=3:break
    pages=[]
    requested=[]
    for name in names:
        url=BASE+"?"+urllib.parse.urlencode({
            "league":"NBA","status":"active","search":name,"limit":200})
        page=read_url(url,key)
        if not isinstance(page,dict):raise ValueError("Invalid response")
        pages.append(page)
        requested.append(name)
    out=publish(pages,comp["comparisons"])
    out["searched_player_count"]=len(requested)
    out["searched_players"]=requested
    DEST.write_text(json.dumps(out,indent=2)+"\n")
    print("PrizePicks matched observations:",out["matched_count"],
          "raw rows:",out["raw_rows_read"],"eligible:",out["eligible_upcoming_offers"],
          "pages:",out["pages_read"],"partial board:",out["partial_board"],
          "rejections:",out["filtered_out_reasons"],flush=True)

if __name__=="__main__":main()
