"""Reconcile every finalized NFL game against verified public player boxscores.

This is an independent, read-only audit of the schedule and published
boxscores. It never fabricates statistics or alters a last-known-good week.
"""
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("docs/nfl/data")
SCHEDULE = ROOT / "schedule_2026.json"
BOXES = ROOT / "boxscores"
REPORT = BOXES / "health.json"
BAD_NAMES = {"", "nan", "none", "null", "<na>", "unknown"}
REQUIRED_STATS = {"attempts","passing_yards","carries","rushing_yards",
                  "targets","receptions","receiving_yards"}


def is_final(game):
    return game.get("status") == "final" and game.get("home_score") is not None and game.get("away_score") is not None


def check_game(schedule_game, box):
    if box.get("game_id") != schedule_game["game_id"]:
        return "game_id_mismatch"
    if int(box.get("week",-1)) != int(schedule_game["week"]):
        return "week_mismatch"
    if box.get("home") != schedule_game["home"] or box.get("away") != schedule_game["away"]:
        return "team_mismatch"
    if box.get("home_score") != schedule_game["home_score"] or box.get("away_score") != schedule_game["away_score"]:
        return "score_mismatch"
    players = box.get("players")
    if not isinstance(players,list) or not players:
        return "no_named_players"
    ids=set()
    teams=set()
    counts={schedule_game["home"]:0,schedule_game["away"]:0}
    for p in players:
        if not isinstance(p,dict):
            return "invalid_player"
        pid = str(p.get("player_id") or "").strip()
        name = str(p.get("player") or "").strip()
        if not pid or pid.lower() in BAD_NAMES or pid in ids:
            return "invalid_or_duplicate_player_id"
        if name.lower() in BAD_NAMES:
            return "missing_player_name"
        team=p.get("team")
        if team not in counts:
            return "wrong_player_team"
        if not REQUIRED_STATS.issubset(p):
            return "missing_stats_fields"
        counts[team]+=1
        teams.add(team)
        ids.add(pid)
    # A final NFL boxscore with players for only one club is incomplete;
    # avoid a rigid roster threshold that would reject short legitimate games.
    if len(teams)!=2:
        return "missing_team_players"
    return None


def reconcile(schedule, manifest, week_data, now=None):
    now = now or datetime.now(timezone.utc)
    games=schedule.get("games",[])
    if schedule.get("season")!=2026 or len(games)!=272 or len({g.get("game_id") for g in games})!=272:
        raise ValueError("Invalid 272-game 2026 NFL schedule")
    finals=[g for g in games if is_final(g)]
    ids=set()
    dup=set()
    published={}
    for week, payload in week_data.items():
        if payload.get("season")!=2026 or int(payload.get("week",-1))!=int(week):
            raise ValueError(f"Week {week} boxscore payload has wrong season/week")
        for game in payload.get("games",[]):
            gid=game.get("game_id")
            if gid in ids:
                dup.add(gid)
            ids.add(gid)
            published[gid]=game
    if dup:
        raise ValueError("Duplicate game across boxscore weeks: "+",".join(sorted(dup)[:5]))
    results=[]
    for game in sorted(finals,key=lambda g:(int(g["week"]),g["game_id"])):
        gid=game["game_id"]
        box=published.get(gid)
        reason="missing_boxscore" if box is None else check_game(game,box)
        status="verified" if reason is None else "needs_retry"
        overdue=False
        if reason:
            kickoff=game.get("kickoff_utc")
            try:
                moment=datetime.fromisoformat(kickoff.replace("Z","+00:00"))
                if moment.tzinfo is not None:
                    overdue=(now-moment).total_seconds()>12*3600
            except (ValueError,AttributeError):
                pass
        results.append({"game_id":gid,"week":int(game["week"]),"status":status,
                        "reason":reason,"overdue":overdue})
    known_ids=set(manifest.get("game_ids",[]))
    if published and known_ids!=set(published):
        raise ValueError("Manifest game IDs disagree with week boxscore files")
    retry=[g for g in results if g["status"]=="needs_retry"]
    overdue=[g for g in retry if g["overdue"]]
    return {"season":2026,"scheduled_games":272,"final_games":len(finals),
            "verified_games":len(results)-len(retry),"pending_games":len(retry),
            "overdue_games":len(overdue),"status":"healthy" if not retry else
                      "attention" if overdue else "awaiting_stats",
            "games_to_retry":retry,
            "last_boxscore_capture":manifest.get("updated_at"),
            "source":"validated NFL season schedule + published nflverse weekly player stats"}


def read_and_audit(schedule_path=SCHEDULE, boxes=BOXES, report_path=REPORT, now=None):
    schedule=json.loads(Path(schedule_path).read_text(encoding="utf-8"))
    manifest_path=Path(boxes)/"manifest.json"
    manifest=json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    weeks={}
    for week in range(1,19):
        path=Path(boxes)/f"week_{week:02d}.json"
        if path.exists():
            weeks[week]=json.loads(path.read_text(encoding="utf-8"))
    result=reconcile(schedule,manifest,weeks,now)
    path=Path(report_path)
    path.parent.mkdir(parents=True,exist_ok=True)
    text=json.dumps(result,sort_keys=True,indent=2)+"\n"
    if path.exists() and path.read_text(encoding="utf-8")==text:
        print("NFL reconciliation unchanged; no new commit needed")
    else:
        with tempfile.NamedTemporaryFile("w",delete=False,dir=str(path.parent),encoding="utf-8") as file:
            file.write(text)
            temp=Path(file.name)
        os.replace(temp,path)
    print("NFL postgame reconciliation:",result["verified_games"],"/",result["final_games"],
          "final games verified;",result["pending_games"],"pending;",
          result["overdue_games"],"overdue")
    for game in result["games_to_retry"][:20]:
        print(f"  RETRY week {game['week']} {game['game_id']}: {game['reason']}"
              +(" (overdue)" if game["overdue"] else ""))
    return result

if __name__=="__main__":
    read_and_audit()
