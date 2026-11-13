"""Independent pair on/off game coverage from dated player stint intervals.

Accept independently sourced possession/stint records for EACH player. All
seconds are game-elapsed offsets (not period clock). This verifies target
exposure with teammate ON versus OFF by overlap; no stat totals are invented.
An overlap threshold confirms sample diversity but does not license source use.
"""
from collections import defaultdict
from datetime import date
import math

def _intervals(records,player_id,through):
    if not isinstance(records,list):raise ValueError("Missing game-level distribution")
    out={}
    for game in records:
        if not isinstance(game,dict):raise ValueError("Invalid game-level record")
        if str(game.get("PlayerId"))!=str(player_id):
            raise ValueError("Game-level player identity mismatch")
        try:
            day=date.fromisoformat(game["Date"])
        except (KeyError,ValueError,TypeError):
            raise ValueError("Missing verifiable game date")
        if day>through:raise ValueError("Future game in on/off coverage")
        gid=str(game.get("GameId",""))
        if not gid.isdecimal() or len(gid)!=10:raise ValueError("Invalid canonical GameId")
        if gid in out:raise ValueError("Duplicate GameId in player distribution")
        parts=game.get("Possessions")
        if not isinstance(parts,list):raise ValueError("Missing player stints")
        windows=[]
        for p in parts:
            if not isinstance(p,dict):raise ValueError("Invalid stint")
            a=p.get("StartTime");b=p.get("EndTime")
            if not isinstance(a,(int,float)) or isinstance(a,bool) or not math.isfinite(a):
                raise ValueError("Invalid starting second")
            if not isinstance(b,(int,float)) or isinstance(b,bool) or not math.isfinite(b):
                raise ValueError("Invalid ending second")
            if not (0<=a<=b<=4000):raise ValueError("Out-of-range or negative stint")
            # Provider emits zero-second possession events. These add no
            # actual exposure and must not invalidate an otherwise legal game.
            if a==b:continue
            windows.append((float(a),float(b)))
        # PBP Stats returns individual possession records, not disjoint
        # continuous court stints. They can share clock intervals. Collapse
        # overlapping intervals into their union to avoid counting time twice.
        windows.sort()
        merged=[]
        for start,end in windows:
            if merged and start<=merged[-1][1]:
                merged[-1]=(merged[-1][0],max(merged[-1][1],end))
            else:
                merged.append((start,end))
        out[gid]=(day,merged)
    return out

def audit_pair(target_distribution,teammate_distribution,
               *,player_id,teammate_id,cutoff_date,min_games=5,min_minutes=120):
    """Return actual independent exposure evidence, or reject incomplete files.

    Each game record has PlayerId, GameId, Date, and Possessions containing
    StartTime/EndTime game-elapsed seconds. For teammate OUT, the target's
    full season participation minus overlap provides off-floor exposure.
    """
    if str(player_id)==str(teammate_id):raise ValueError("Target cannot be teammate")
    through=date.fromisoformat(cutoff_date)
    target=_intervals(target_distribution,player_id,through)
    teammate=_intervals(teammate_distribution,teammate_id,through)
    if not target:raise ValueError("No completed target games")
    # Reject ambiguous case where one distribution includes future-day records
    # or a teammate game ID maps to a different date.
    for gid,(day,_) in target.items():
        if gid in teammate and teammate[gid][0]!=day:
            raise ValueError("Conflicting game dates across distributions")
    on=[];off=[]
    for gid,(day,windows) in target.items():
        other=teammate.get(gid,(day,[]))[1]
        on_seconds=0
        for a,b in windows:
            for x,y in other:
                on_seconds+=max(0,min(b,y)-max(a,x))
        total=sum(b-a for a,b in windows)
        off_seconds=total-on_seconds
        if on_seconds>0:on.append((gid,day.isoformat(),on_seconds))
        if off_seconds>0:off.append((gid,day.isoformat(),off_seconds))
    totals={}
    for name,items in (("with",on),("without",off)):
        seconds=sum(z[2] for z in items)
        totals[name]={"game_dates":sorted({x[1] for x in items}),
                      "game_ids":sorted({x[0] for x in items}),
                      "games":len(items),"seconds":round(seconds,3),
                      "minutes":round(seconds/60,4)}
        if len(items)<min_games or seconds/60<min_minutes:
            raise ValueError("Insufficient independent "+name+" teammate sample")
    return {"status":"GAME_LEVEL_ON_OFF_EXPOSURE_VERIFIED",
            "player_id":str(player_id),"teammate_id":str(teammate_id),
            "data_through":cutoff_date,"with":totals["with"],
            "without":totals["without"],
            "source_method":"PLAYER_DISTRIBUTION_POSSESSION_TIME_INTERSECTION",
            "rights_verified":False}
