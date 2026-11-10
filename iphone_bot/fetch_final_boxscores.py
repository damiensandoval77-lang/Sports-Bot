"""Read finalized NBA player box scores for early grading; never infer final stats.

Priority: NBA public CDN final scoreboard + final boxscore.
Fallback: ESPN NBA scoreboard (completed event) + game summary.
All records use exact player name, team, opponent and Eastern game date;
the historical CSV remains the independent fallback. This module NEVER makes
live projections and NEVER writes grades itself.

Provider network failures are nonfatal but explicitly diagnosed.
"""
import datetime as dt
import json
import math
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
LEDGER=ROOT/"docs/paper_pick_ledger.json"
OUT=ROOT/"data/nba/current/final_boxscores.json"
STATUS=ROOT/"docs/final_boxscores_status.json"
ET=ZoneInfo("America/New_York")
NBA_SCOREBOARD="https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json"
NBA_BOX="https://cdn.nba.com/static/json/liveData/boxscore/boxscore_{}.json"
NBA_SCHEDULE="https://cdn.nba.com/static/json/staticData/scheduleLeagueV2.json"
NBA_SCHEDULE_ALT="https://cdn.nba.com/static/json/staticData/scheduleLeagueV2_1.json"
ESPN_SCORE="https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
ESPN_BOX="https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary"

ALIASES={"GS":"GSW","GSW":"GSW","NY":"NYK","NYK":"NYK",
         "NO":"NOP","NOR":"NOP","NOP":"NOP","SA":"SAS","SAS":"SAS",
         "UTAH":"UTA","UTA":"UTA","PHO":"PHX","PHX":"PHX",
         "BKN":"BKN","BRK":"BKN","CHA":"CHA","CHO":"CHA"}
ABBREV={"ATL","BOS","BKN","CHA","CHI","CLE","DAL","DEN","DET",
        "GSW","HOU","IND","LAC","LAL","MEM","MIA","MIL","MIN",
        "NOP","NYK","OKC","ORL","PHI","PHX","POR","SAC","SAS",
        "TOR","UTA","WAS"}


def team(value):
    code=str(value or "").strip().upper()
    code=ALIASES.get(code,code)
    return code if code in ABBREV else None


def local_date(value):
    date=dt.datetime.fromisoformat(str(value).replace("Z","+00:00"))
    if date.tzinfo is None:raise ValueError("naive game time")
    return date.astimezone(ET).date().isoformat()


def request_json(url,timeout=12):
    headers={"User-Agent":"Mozilla/5.0 (compatible; SportsBotBoxscoreAudit/1.0)",
             "Accept":"application/json","Referer":"https://www.nba.com/"}
    req=urllib.request.Request(url,headers=headers)
    with urllib.request.urlopen(req,timeout=timeout) as resp:
        data=json.load(resp)
    if not isinstance(data,dict):raise ValueError("response not object")
    return data


def number(value):
    if value is None or isinstance(value,bool):return None
    try:
        n=float(value)
        return n if math.isfinite(n) and n>=0 else None
    except (ValueError,TypeError):
        return None


def minutes(value):
    if value is None:return None
    text=str(value).strip()
    m=re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?",text)
    if m and any(x is not None for x in m.groups()):
        h,mins,sec=m.groups()
        return (int(h or 0)*60+int(mins or 0)+float(sec or 0)/60)
    m=re.fullmatch(r"(\d+):(\d{2})",text)
    if m:return int(m.group(1))+int(m.group(2))/60
    return number(text)


def box_player(name,team_code,opponent,date,pts,reb,ast,mins,source,game_id):
    if not (isinstance(name,str) and name.strip() and
            team_code in ABBREV and opponent in ABBREV and team_code!=opponent):
        return None
    vals=[number(x) for x in (pts,reb,ast)]
    played=minutes(mins)
    if any(x is None for x in vals) or played is None or not (0<played<=60):
        return None
    # Final box scores must be plausible NBA player lines, not half-empty feed rows.
    if any(x>150 for x in vals):return None
    return {"player":name.strip(),"team":team_code,"opponent":opponent,
            "date":date,"PTS":vals[0],"REB":vals[1],"AST":vals[2],
            "PRA":sum(vals),"MIN":round(played,4),
            "source":source,"final_confirmed":True,"source_game_id":str(game_id)}


def verified_dnp_player(name,team_code,opponent,date,reason,source,game_id):
    """Explicit no-play from confirmed final box, never inferred from missing CSV."""
    if not (name and team_code in ABBREV and opponent in ABBREV
            and team_code!=opponent and isinstance(reason,str) and reason.strip()):
        return None
    return {"player":str(name).strip(),"team":team_code,"opponent":opponent,
            "date":date,"source":source,"final_confirmed":True,
            "source_game_id":str(game_id),"dnp_final_verified":True,
            "dnp_reason":reason.strip()[:160]}


def nba_scoreboard_games(payload):
    games=payload.get("scoreboard",{}).get("games",[])
    if not isinstance(games,list):raise ValueError("bad NBA scoreboard")
    return [g for g in games if g.get("gameStatus")==3 and
            re.fullmatch(r"\d{10}",str(g.get("gameId","")))]


def nba_boxscore_rows(score_event,box):
    if score_event.get("gameStatus")!=3:raise ValueError("scoreboard not final")
    game=box.get("game")
    if not isinstance(game,dict) or game.get("gameStatus")!=3:raise ValueError("boxscore not final")
    game_id=str(score_event.get("gameId"))
    if game_id!=str(game.get("gameId")):raise ValueError("mismatched game id")
    a,h=game.get("awayTeam",{}),game.get("homeTeam",{})
    away,home=team(a.get("teamTricode")),team(h.get("teamTricode"))
    if not away or not home or away==home:raise ValueError("unknown teams")
    if (team(score_event.get("awayTeam",{}).get("teamTricode"))!=away or
        team(score_event.get("homeTeam",{}).get("teamTricode"))!=home):
        raise ValueError("scoreboard/boxscore team mismatch")
    day=local_date(score_event["gameTimeUTC"])
    rows=[]
    for side,tcode,opp in ((a,away,home),(h,home,away)):
        for player in side.get("players",[]):
            stats=player.get("statistics",{})
            if not isinstance(stats,dict):continue
            row=box_player(player.get("name") or
                  " ".join(str(player.get(v) or "").strip()
                    for v in ("firstName","familyName")).strip(),
                  tcode,opp,day,stats.get("points"),stats.get("reboundsTotal"),
                  stats.get("assists"),stats.get("minutes") or stats.get("minutesCalculated"),
                  "NBA_CDN_FINAL",game_id)
            if row:
                rows.append(row)
            elif player.get("played") is False and (
                    player.get("notPlayingReason") or
                    str(player.get("status","")).upper() in ("INACTIVE","DNP","NOT_PLAYING")):
                dnp=verified_dnp_player(
                    player.get("name") or
                    " ".join(str(player.get(v) or "").strip()
                             for v in ("firstName","familyName")).strip(),
                    tcode,opp,day,str(player.get("notPlayingReason") or
                                      player.get("status")),
                    "NBA_CDN_FINAL",game_id)
                if dnp:rows.append(dnp)
    return rows


def espn_final_events(payload):
    events=payload.get("events")
    if not isinstance(events,list):raise ValueError("bad ESPN scoreboard")
    result=[]
    for event in events:
        comps=event.get("competitions") or []
        if not comps:continue
        status=event.get("status",{}).get("type",{})
        if status.get("completed") is not True:continue
        by_side={x.get("homeAway"):x for x in comps[0].get("competitors",[])}
        a,h=by_side.get("away",{}),by_side.get("home",{})
        if not team(a.get("team",{}).get("abbreviation")) or not team(h.get("team",{}).get("abbreviation")):
            continue
        result.append(event)
    return result


def espn_boxscore_rows(event,summary):
    if not event.get("status",{}).get("type",{}).get("completed"):
        raise ValueError("ESPN scoreboard not final")
    event_id=str(event.get("id"))
    comps=event.get("competitions") or []
    if not comps:raise ValueError("missing game")
    by_side={x.get("homeAway"):x for x in comps[0].get("competitors",[])}
    away=team(by_side.get("away",{}).get("team",{}).get("abbreviation"))
    home=team(by_side.get("home",{}).get("team",{}).get("abbreviation"))
    if not away or not home or away==home:raise ValueError("unknown matchup")
    header_events=summary.get("header",{}).get("competitions",[])
    if header_events and str(summary.get("header",{}).get("id",event_id))!=event_id:
        raise ValueError("summary identity mismatch")
    day=local_date(event["date"])
    rows=[]
    for group in summary.get("boxscore",{}).get("players",[]):
        code=team(group.get("team",{}).get("abbreviation"))
        if code not in (away,home):continue
        opp=home if code==away else away
        for table in group.get("statistics",[]):
            labels=table.get("names",[])
            if not isinstance(labels,list):continue
            keys={str(label).upper():i for i,label in enumerate(labels)}
            for entry in table.get("athletes",[]):
                if not isinstance(entry,dict):continue
                player=entry.get("athlete") or {}
                if not isinstance(player,dict):continue
                values=entry.get("stats") or []
                # Explicit finalized ESPN DNP only: never treat missing numeric
                # stats, empty arrays, or a roster omission as proof of absence.
                reason=entry.get("reason") or entry.get("notPlayingReason")
                played_minutes=(minutes(values[keys["MIN"]])
                                if isinstance(values,list) and "MIN" in keys and keys["MIN"]<len(values) else None)
                if (entry.get("didNotPlay") is True and isinstance(reason,str) and
                    reason.strip() and not (played_minutes is not None and played_minutes>0)):
                    row=verified_dnp_player(player.get("displayName"),code,opp,day,
                                            reason,"ESPN_FINAL",event_id)
                    if row:rows.append(row)
                    continue
                if not isinstance(values,list) or not {"PTS","REB","AST","MIN"}.issubset(keys) or not all(keys[k]<len(values) for k in ("PTS","REB","AST","MIN")):
                    continue
                row=box_player(player.get("displayName"),code,opp,day,
                               values[keys["PTS"]],values[keys["REB"]],
                               values[keys["AST"]],values[keys["MIN"]],
                               "ESPN_FINAL",event_id)
                if row:rows.append(row)
    return rows


def verified_schedule_ids(payload,pending):
    """Find official NBA game IDs for exact scheduled date + opponents only.

    The NBA schedule is a discovery source, never proof of a final score.
    Each resolved boxscore must separately confirm gameStatus=3.
    """
    league=payload.get("leagueSchedule")
    if not isinstance(league,dict):
        raise ValueError("Invalid NBA season schedule")
    season=str(league.get("seasonYear") or "")
    if not season.startswith("2026"):
        raise ValueError("NBA schedule is not for 2026-27")
    matches={}
    for block in league.get("gameDates",[]):
        raw_day=str(block.get("gameDate") or "").strip()
        try:
            if raw_day[:4].isdigit() and "-" in raw_day:
                day=raw_day[:10]
            else:
                day=dt.datetime.strptime(raw_day[:10],"%m/%d/%Y").date().isoformat()
        except ValueError:
            continue
        for game in block.get("games",[]):
            gid=str(game.get("gameId") or "")
            if not re.fullmatch(r"00226\d{5}",gid):continue
            away=team(game.get("awayTeam",{}).get("teamTricode"))
            home=team(game.get("homeTeam",{}).get("teamTricode"))
            key=(day,away,home)
            if key not in pending:continue
            if key in matches and matches[key]!=gid:
                raise ValueError("Ambiguous NBA game ID for matchup")
            matches[key]=gid
    return matches


def final_schedule_boxscore(game_id,pending_key,request):
    """Check identity and final status from the boxscore itself."""
    box=request(NBA_BOX.format(game_id))
    g=box.get("game") or {}
    if str(g.get("gameId"))!=str(game_id) or g.get("gameStatus")!=3:
        return []
    day,away,home=pending_key
    if (team(g.get("awayTeam",{}).get("teamTricode"))!=away or
        team(g.get("homeTeam",{}).get("teamTricode"))!=home or
        local_date(g.get("gameTimeUTC"))!=day):
        raise ValueError("Official NBA boxscore identity mismatched schedule")
    # Pass final headers from independently matched official boxscore.
    event={"gameId":game_id,"gameStatus":3,
           "gameTimeUTC":g["gameTimeUTC"],
           "awayTeam":{"teamTricode":away},
           "homeTeam":{"teamTricode":home}}
    return nba_boxscore_rows(event,box)


def pending_games(records,now=None):
    current=now or dt.datetime.now(dt.timezone.utc)
    games=set()
    for r in records:
        if r.get("status")!="PENDING":continue
        try:
            start=dt.datetime.fromisoformat(r["event_start"].replace("Z","+00:00"))
            if start.tzinfo is None:continue
            age=(current-start).total_seconds()
            # Retry every historical pending game, not just the last four days.
            # Settlement still requires an independently verified final box score.
            if age<2*3600:continue
            day=local_date(r["event_start"])
            pair=r["game"].split(" @ ")
            if len(pair)!=2:continue
            try:
                from .paper_pick_pipeline import TEAM_ABBREVIATIONS
            except ImportError:
                from paper_pick_pipeline import TEAM_ABBREVIATIONS
            away=TEAM_ABBREVIATIONS.get(pair[0].strip())
            home=TEAM_ABBREVIATIONS.get(pair[1].strip())
            if away and home and away!=home:
                games.add((day,away,home))
        except (ValueError,KeyError,TypeError):continue
    return games


def gather(records,now=None,request=request_json,known_game_ids=None):
    pending=pending_games(records,now)
    days={key[0] for key in pending}
    # By team abbreviation and event day, never by a similar player's name.
    from_nba=[]
    from_espn=[]
    report={"pending_matchups":len(pending),"final_nba_games":0,
            "final_schedule_discovered_nba_games":0,
            "final_espn_games":0,"retrieved_player_lines":0,"errors":[],
            "source":"NBA live CDN; ESPN completed boxscore fallback"}
    def needed(date,a,h):
        return (date,a,h) in pending
    if not pending:
        report["status"]="NO_ELIGIBLE_PENDING_MATCHUPS"
        return [],report
    nba_complete=set()
    try:
        board=request(NBA_SCOREBOARD)
        for event in nba_scoreboard_games(board):
            try:
                day=local_date(event["gameTimeUTC"])
                a=team(event.get("awayTeam",{}).get("teamTricode"))
                h=team(event.get("homeTeam",{}).get("teamTricode"))
                if not needed(day,a,h):continue
                rows=nba_boxscore_rows(event,request(NBA_BOX.format(event["gameId"])))
                if not rows:continue
                from_nba.extend(rows)
                nba_complete.add((day,a,h))
                report["final_nba_games"]+=1
            except (ValueError,KeyError,TypeError,OSError) as exc:
                report["errors"].append("NBA boxscore unavailable: "+str(exc)[:140])
    except (ValueError,KeyError,TypeError,OSError) as exc:
        report["errors"].append("NBA scoreboard unavailable: "+str(exc)[:140])
    # Use previously observed official liveData NBA IDs before expensive
    # season schedule rediscovery. These IDs are only lookup hints: the
    # returned official box must STILL attest FINAL, date, teams, and game ID.
    if known_game_ids:
        from iphone_bot.official_game_id_index import matching_ids
        pending_ids=matching_ids(known_game_ids,pending-nba_complete)
        report["cached_official_id_candidates"]=len(pending_ids)
        for key,gid in pending_ids.items():
            if key in nba_complete:continue
            try:
                rows=final_schedule_boxscore(gid,key,request)
                if not rows:continue
                from_nba.extend(rows)
                nba_complete.add(key)
                report["final_nba_games"]+=1
                report["final_cached_id_nba_games"]=report.get("final_cached_id_nba_games",0)+1
            except (OSError,ValueError,KeyError,TypeError) as exc:
                report["errors"].append("Cached official ID boxscore unavailable: "+str(exc)[:130])
    # The live NBA scoreboard can time out on hosted runners or roll over to
    # the next day. Discover historical IDs from the official season schedule,
    # then read each actual final (gameStatus=3) NBA player boxscore.
    remaining={k for k in pending if k not in nba_complete}
    if remaining:
        for endpoint in (NBA_SCHEDULE,NBA_SCHEDULE_ALT):
            try:
                candidates=verified_schedule_ids(request(endpoint),remaining)
                for key,gid in candidates.items():
                    if key in nba_complete:continue
                    try:
                        rows=final_schedule_boxscore(gid,key,request)
                        if not rows:continue
                        from_nba.extend(rows)
                        nba_complete.add(key)
                        report["final_nba_games"]+=1
                        report["final_schedule_discovered_nba_games"]+=1
                    except (OSError,ValueError,KeyError,TypeError) as exc:
                        report["errors"].append("NBA schedule-boxscore unavailable: "+str(exc)[:130])
                break
            except (OSError,ValueError,KeyError,TypeError) as exc:
                report["errors"].append("NBA schedule unavailable: "+str(exc)[:130])
    # ESPN is a fallback for missed games (e.g. NBA daily scoreboard has rolled).
    for date in sorted(days):
        if all(key in nba_complete for key in pending if key[0]==date):continue
        try:
            board=request(ESPN_SCORE+"?"+urllib.parse.urlencode({"dates":date.replace("-",""),"limit":100}))
            for event in espn_final_events(board):
                try:
                    teams={c["homeAway"]:team(c.get("team",{}).get("abbreviation"))
                           for c in event["competitions"][0]["competitors"]}
                    ateam,hteam=teams.get("away"),teams.get("home")
                    key=(local_date(event["date"]),ateam,hteam)
                    if key in nba_complete or key not in pending:continue
                    rows=espn_boxscore_rows(event,request(ESPN_BOX+"?"+urllib.parse.urlencode({"event":str(event["id"])})))
                    if not rows:continue
                    from_espn.extend(rows)
                    report["final_espn_games"]+=1
                except (ValueError,KeyError,TypeError,OSError) as exc:
                    report["errors"].append("ESPN game unavailable: "+str(exc)[:140])
        except (ValueError,KeyError,TypeError,OSError) as exc:
            report["errors"].append("ESPN scoreboard unavailable: "+str(exc)[:140])
    # Never overwrite an NBA result with a second provider's same game.
    found=from_nba+from_espn
    report["retrieved_player_lines"]=len(found)
    report["status"]="FINAL_BOXSCORES_FOUND" if found else "NO_FINAL_BOXSCORES_AVAILABLE"
    return found,report


def main():
    entries=json.loads(LEDGER.read_text()).get("records",[]) if LEDGER.exists() else []
    observed,report=gather(entries)
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(observed,indent=2)+"\n")
    report.update(updated_at=dt.datetime.now(dt.timezone.utc).isoformat())
    STATUS.write_text(json.dumps(report,indent=2)+"\n")
    print("FINAL NBA BOXSCORES:",json.dumps(report,sort_keys=True),flush=True)


if __name__=="__main__":main()
