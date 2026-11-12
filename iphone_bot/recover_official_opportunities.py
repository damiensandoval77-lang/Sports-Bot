"""Recover missing current-season opportunity rows from completed NBA CDN boxscores.

Only use previously completed *official* games, exact NBA player ID, team,
opponent, Eastern date, and independent CSV stats agreement. No odds requests.
Does not fabricate a current player or teammate role. If unavailable, retain
the previous model history and explicitly report the coverage gap.
"""
from collections import defaultdict
from datetime import datetime,timezone
try:
    from .fetch_final_boxscores import (NBA_SCHEDULE,NBA_SCHEDULE_ALT,NBA_BOX,
        request_json,verified_schedule_ids,team,local_date,minutes,number)
    from .live_lagged_matchup_sidecar import stamp,ET
except ImportError:
    from fetch_final_boxscores import (NBA_SCHEDULE,NBA_SCHEDULE_ALT,NBA_BOX,
        request_json,verified_schedule_ids,team,local_date,minutes,number)
    from live_lagged_matchup_sidecar import stamp,ET

FIELDS={"FGA":"fieldGoalsAttempted","FTA":"freeThrowsAttempted",
        "TOV":"turnovers","OREB":"reboundsOffensive",
        "PTS":"points","REB":"reboundsTotal","AST":"assists"}

def completed_row(local,game_id,box,tip_day):
    """Return a genuine independently confirmed historical player game."""
    game=box.get("game") or {}
    if str(game.get("gameId"))!=str(game_id) or game.get("gameStatus")!=3:
        return None
    date=local.get("date")
    if not date or date>=tip_day or local_date(game.get("gameTimeUTC"))!=date:
        return None
    away=team((game.get("awayTeam") or {}).get("teamTricode"))
    home=team((game.get("homeTeam") or {}).get("teamTricode"))
    own=team(local.get("team"));opp=team(local.get("opponent"))
    if (not own or not opp or own==opp or set((own,opp))!=set((away,home))):
        return None
    side=game["awayTeam"] if own==away else game["homeTeam"]
    matches=[p for p in side.get("players",[])
             if str(p.get("personId") or p.get("playerId") or "")==str(local.get("id"))]
    if len(matches)!=1 or matches[0].get("played") is False:
        return None
    stats=matches[0].get("statistics") or {}
    if not isinstance(stats,dict):return None
    values={key:number(stats.get(src)) for key,src in FIELDS.items()}
    played=minutes(stats.get("minutes") or stats.get("minutesCalculated"))
    if any(v is None for v in values.values()) or played is None or not 0<played<=60:
        return None
    if any(abs(float(local.get(k,-999))-values[k])>0.01 for k in ("PTS","REB","AST")):
        return None
    if abs(float(local.get("MIN",-999))-played)>2.5:
        return None
    if values["FGA"]>60 or values["FTA"]>50 or values["OREB"]>25 or values["TOV"]>25:
        return None
    return {**local,**values,"MIN":played,"season":"2026-27",
            "team":own,"opponent":opp,"id":str(local["id"]),
            "verified_source":"NBA_CDN_FINAL_OPPORTUNITY_HISTORY",
            "verified_game_id":str(game_id)}

def recover(local,checked,feed,*,fetch=request_json,max_games=24):
    """Use official finalized boxes only for historical player-games missing
    from the two-source parquet match. Prioritize players in the live board.
    All dates must precede the exact quoted fixture tip (no post-tip leakage).
    """
    selected=[x for x in feed.get("picks",[]) if x.get("pickem_tier")=="standard"
              and x.get("player") and x.get("team") and x.get("start")]
    tips=defaultdict(list)
    for x in selected:
        try:
            tip=stamp(x["start"])
            day=tip.astimezone(ET).date().isoformat()
            tips[(str(x["player"]).casefold(),str(x["team"]).upper())].append(day)
        except (ValueError,TypeError):continue
    if not tips:
        return checked,{"status":"NO_VERIFIED_TARGETS","recovered":0,"requested_games":0}
    existing={(str(r["id"]),r["team"],r["date"]) for r in checked}
    needed=defaultdict(list)
    for r in local:
        key=(str(r.get("id")),str(r.get("team")),str(r.get("date")))
        dates=tips.get((str(r.get("player","")).casefold(),str(r.get("team","")).upper()))
        if not dates or key in existing or not r.get("opponent"):continue
        tip_day=min(dates)
        if not r.get("date") or r["date"]>=tip_day:continue
        # Only exact season years and player IDs; never trust a sportsbook
        # name alone to recover opponent opportunities.
        if not str(r.get("id","")).isdigit():continue
        own,opp=team(r["team"]),team(r["opponent"])
        if not own or not opp or own==opp:continue
        away,home=tuple(sorted((own,opp)))
        needed[(r["date"],away,home)].append((r,tip_day))
    if not needed:
        return checked,{"status":"NO_MISSING_PRIOR_GAMES","recovered":0,"requested_games":0}
    schedule=None
    for url in (NBA_SCHEDULE_ALT,NBA_SCHEDULE):
        try:
            schedule=fetch(url)
            if isinstance(schedule.get("leagueSchedule"),dict):break
        except Exception:continue
    if not schedule or not isinstance(schedule.get("leagueSchedule"),dict):
        return checked,{"status":"NBA_SCHEDULE_UNAVAILABLE","recovered":0,"requested_games":0}
    # Official schedule uses away/home identity; use game keys in either
    # direction but never accept ambiguous collisions.
    pending=set()
    for day,a,b in needed:
        pending.add((day,a,b));pending.add((day,b,a))
    try:
        ids=verified_schedule_ids(schedule,pending)
    except (ValueError,TypeError,KeyError):
        return checked,{"status":"NBA_SCHEDULE_UNVERIFIED","recovered":0,"requested_games":0}
    candidates=[]
    for (day,a,b),rows in needed.items():
        hits=[(key,gid) for key,gid in ids.items()
              if key[0]==day and set(key[1:])==set((a,b))]
        if len(hits)==1:
            candidates.append((day,hits[0][1],rows))
    # Bounded free reads. Recent games fill the most important history first.
    candidates.sort(key=lambda x:x[0],reverse=True)
    result=list(checked);seen=set(existing);failures=0
    for day,gid,rows in candidates[:max_games]:
        try:box=fetch(NBA_BOX.format(gid))
        except Exception:
            failures+=1;continue
        for raw,tip_day in rows:
            recovered=completed_row(raw,gid,box,tip_day)
            if not recovered:continue
            key=(recovered["id"],recovered["team"],recovered["date"])
            if key not in seen:
                seen.add(key);result.append(recovered)
    return result,{"status":"NBA_CDN_FINAL_CROSSCHECKED",
                   "recovered":len(result)-len(checked),
                   "requested_games":min(len(candidates),max_games),
                   "eligible_games":len(candidates),"fetch_failures":failures,
                   "remaining_missing":max(0,sum(len(v) for v in needed.values())-(len(result)-len(checked)))}
