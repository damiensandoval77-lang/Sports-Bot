"""Point-in-time NBA OUT status and conservative teammate minutes scenarios.

Official NBA PDF is preferred at its actual publication time. A later,
authentic UnderdogNBA report may provisionally override an earlier report;
an older or unverified post cannot. No unsupported projections are silently
retained after a meaningful OUT announcement.
"""
from collections import defaultdict
from datetime import datetime,timezone,timedelta
from statistics import mean
import math

def utc(value):
    t=datetime.fromisoformat(str(value).replace("Z","+00:00"))
    if t.tzinfo is None:raise ValueError("Need UTC timestamp")
    return t.astimezone(timezone.utc)

def live_out(injuries,news,game_day,game_start,now):
    """Return keyed player OUT data for one fixture date, with source metadata."""
    tip=utc(game_start);now=utc(now)
    statuses={}
    if injuries.get("status")=="OFFICIAL_NBA_REPORT_VERIFIED" and injuries.get("injury_data_verified") is True:
        try:issued=utc(injuries["report_issued_at"])
        except (KeyError,ValueError,TypeError):issued=None
        if issued and now>=issued and now-issued<=timedelta(hours=18):
            for p in injuries.get("players",[]):
                if p.get("game_date")!=game_day or not p.get("player_id") or not p.get("team"):continue
                statuses[(str(p["player_id"]),p["team"])]={
                  "player_id":str(p["player_id"]),"player":p.get("player"),
                  "team":p["team"],"status":str(p.get("status","")).upper(),
                  "source":"OFFICIAL_NBA_REPORT","reported_at":issued.isoformat(),
                  "official":True}
    if news.get("status")=="UNDERDOGNBA_X_AUTHENTICATED_POLL" and news.get("verified_x_posts") is True:
        for p in news.get("alerts",[]):
            if (p.get("game_date")!=game_day or p.get("start")!=game_start or
                p.get("source")!="UNDERDOGNBA_X_VERIFIED_AUTHOR" or
                p.get("status") not in ("OUT","AVAILABLE") or
                p.get("official_nba_confirmed") is not False):continue
            try:posted=utc(p["posted_at"])
            except (KeyError,ValueError,TypeError):continue
            if posted>now or posted>=tip or now-posted>timedelta(hours=8):continue
            k=(str(p["player_id"]),p["team"])
            old=statuses.get(k)
            if old and utc(old["reported_at"])>=posted:continue
            statuses[k]={"player_id":str(p["player_id"]),"player":p["player"],
                "team":p["team"],"status":p["status"],
                "source":"UNDERDOGNBA_X_PROVISIONAL","reported_at":posted.isoformat(),
                "source_url":p.get("source_url"),"official":False}
    return {k:v for k,v in statuses.items() if v["status"]=="OUT"}

def minutes_shift(player_id,out_id,team,day,games):
    """Require >=3 earlier, complete with/without teammate games.

    Both reciprocal team/opponent player boxes must have >=7 unique players
    on the completed date; cannot infer missing player from partial logs.
    """
    if str(player_id)==str(out_id):return None
    # Current form CSV supplies date, player, team and actual opponent,
    # but does NOT contain a game_id. Verify the reciprocal pair instead.
    # A missing teammate is treated as a completed observed nonappearance
    # only when both teams have at least 7 recorded active players.
    pairs=defaultdict(list)
    for g in games:
        d=str(g.get("date",""))
        t=str(g.get("team") or "")
        opp=str(g.get("opponent") or "")
        if not d or d>=day or not t or not opp or t==opp:continue
        pairs[(d,t,opp)].append(g)
    with_m,without_m=[],[]
    for (date,side,opp),own in pairs.items():
        if side!=team or len(own)<7:continue
        reverse=pairs.get((date,opp,side),[])
        if len(reverse)<7:continue
        if len({str(g.get("id")) for g in own})!=len(own) or len({str(g.get("id")) for g in reverse})!=len(reverse):
            continue
        me=[g for g in own if str(g.get("id"))==str(player_id)]
        if len(me)!=1:continue
        try:m=float(me[0]["MIN"])
        except (KeyError,TypeError,ValueError):continue
        if not math.isfinite(m) or m<1 or m>48:continue
        present=False
        for g in own:
            if str(g.get("id"))!=str(out_id):continue
            try:played=float(g.get("MIN") or 0)
            except (ValueError,TypeError):played=0
            present=math.isfinite(played) and played>0
        (with_m if present else without_m).append(m)
    if min(len(with_m),len(without_m))<3:return None
    # Shrink strongly because teammate absence alone is not causal.
    rate=(mean(without_m[-8:])/mean(with_m[-8:]))**0.5
    return round(max(.90,min(1.10,rate)),5)

def injury_adjustment(base,player_id,team,opponent,day,game_start,now,injuries,news,games,*,free_watch=None):
    outs=live_out(injuries,news,day,game_start,now)
    self_out=outs.get((str(player_id),team))
    if self_out:return {"status":"PLAYER_REPORTED_OUT_SUPPRESS_ALL_MARKETS",
        "factor":None,"out":self_out,"affected":[]}
    # A published official report lists persistent long-term absences again
    # every time it refreshes. Do not treat every old OUT as a newly missing
    # teammate and re-adjust the entire league repeatedly. Only a matching,
    # authenticated new Underdog alert enters the teammate-change scenario.
    # Official updates still remove ruled-out players' OWN lines above.
    alerted=set()
    if news.get("status")=="UNDERDOGNBA_X_AUTHENTICATED_POLL" and news.get("verified_x_posts") is True:
        for e in news.get("alerts",[]):
            if (e.get("source")=="UNDERDOGNBA_X_VERIFIED_AUTHOR" and
                e.get("status")=="OUT" and e.get("game_date")==day and
                e.get("start")==game_start):
                try:
                    published=utc(e["posted_at"])
                    if published<=utc(now) and utc(now)-published<=timedelta(hours=8):
                        alerted.add((str(e["player_id"]),e["team"]))
                except (ValueError,KeyError,TypeError):pass
    # A keyless official NBA monitor can detect real status changes even
    # though no X developer account exists. Only carry forward a transition
    # while it remains an OUT in the latest verified official report.
    if (free_watch and free_watch.get("status")=="FREE_OFFICIAL_NBA_INJURY_MONITOR"
            and free_watch.get("official_confirmed") is True):
        for e in free_watch.get("events",[]):
            if (e.get("source")=="OFFICIAL_NBA_REPORT" and e.get("official") is True
                    and e.get("status")=="OUT" and e.get("game_date")==day):
                k=(str(e.get("player_id")),e.get("team"))
                if k not in outs:continue
                try:
                    reported=utc(e["reported_at"])
                    if reported<=utc(now) and utc(now)-reported<=timedelta(hours=12):
                        alerted.add(k)
                except (ValueError,TypeError,KeyError):pass
    affected=[v for k,v in outs.items() if k in alerted and v["team"] in (team,opponent)]
    if not affected:return {"status":"NO_REPORTED_OUT","factor":1.0,"affected":[]}
    same=[v for v in affected if v["team"]==team]
    other=[v for v in affected if v["team"]==opponent]
    if other:
        # Opponent defense changes require independently validated historical
        # matchup splits; do not pretend teammate minutes captures that effect.
        return {"status":"BASELINE_WITH_UNRESOLVED_INJURY","factor":1.0,
                "affected":affected,"reason":"OPPONENT_ABSENCE_NOT_MODELED",
                "injury_adjusted":False,"probability_actionable":False}
    if len(same)!=1:return {"status":"BASELINE_WITH_UNRESOLVED_INJURY",
                           "factor":1.0,"affected":affected,
                           "reason":"MULTIPLE_TEAMMATES_OUT",
                           "injury_adjusted":False,"probability_actionable":False}
    ratio=minutes_shift(player_id,same[0]["player_id"],team,day,games)
    if ratio is None:return {"status":"BASELINE_WITH_UNRESOLVED_INJURY",
                             "factor":1.0,"affected":affected,
                             "reason":"NO_COMPLETE_PRIOR_WITH_WITHOUT_SPLITS",
                             "injury_adjusted":False,"probability_actionable":False}
    return {"status":"CONDITIONAL_INJURY_REPROJECTION",
        "factor":ratio,"affected":affected,
        "provisional":not same[0]["official"],
        "method":"PRIOR_COMPLETE_GAMES_BOUNDED_MINUTES_SPLIT",
        "disclaimer":"Unvalidated teammate minutes sensitivity; not proven change in player usage."}
