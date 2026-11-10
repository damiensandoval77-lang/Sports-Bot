"""Recover verified zero receiving markets from participated offensive snaps.

An offensive snap count is not a bet settlement by itself. Require a complete
final game boxscore, exact game/team/name join, and a unique PFR snap record.
Never use this recovery for touchdowns or fantasy scoring.
"""
import csv, io, json, urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path("docs/nfl/data")
SOURCE="https://github.com/nflverse/nflverse-data/releases/download/snap_counts/snap_counts_2026.parquet"
OUT=ROOT/"verified_zero_snap_stats_2026.json"
ELIGIBLE={"REC","REC_YDS","TGT"}

def normalize(name):
    return " ".join(str(name).casefold().replace(".","").replace("'","").split())

def build(pending, games, snap_records):
    by_game={}
    for entry in snap_records:
        if int(entry.get("season",0))!=2026 or str(entry.get("game_type",""))!="REG":continue
        if not entry.get("game_id"):continue
        by_game.setdefault(entry["game_id"],[]).append(entry)
    results=[]
    for r in pending:
        if r["target"] not in ELIGIBLE or r["grade_status"]!="player_not_in_verified_boxscore":
            continue
        gid=r["game_id"]
        g=games.get(gid)
        if not g or g.get("status")!="final" or g.get("home_score") is None or g.get("away_score") is None:
            continue
        peers=by_game.get(gid,[])
        # Refuse incomplete snap snapshots for the game; names are PFR IDs.
        if len(peers)<25 or len({p.get("pfr_player_id") for p in peers if p.get("pfr_player_id")})<25:
            continue
        match=[p for p in peers if p.get("team")==r["team"] and
               normalize(p.get("player"))==normalize(r["player"]) and
               float(p.get("offense_snaps") or 0)>0]
        if len(match)!=1 or not match[0].get("pfr_player_id"):continue
        results.append({"game_id":gid,"player_id":r["player_id"],"player":r["player"],
            "team":r["team"],"pfr_player_id":str(match[0]["pfr_player_id"]),
            "offense_snaps":int(float(match[0]["offense_snaps"])),
            "verified_zero_targets":True,
            "source_url":SOURCE})
    unique={(r["game_id"],r["player_id"]):r for r in results}
    return sorted(unique.values(),key=lambda r:(r["game_id"],r["player_id"]))

def run(root=ROOT):
    import pandas as pd
    import sys
    sys.path.insert(0,"scripts")
    from reconcile_nfl_picks import read_csv,verified_boxscores
    root=Path(root)
    schedule=json.loads((root/"schedule_2026.json").read_text())
    games={g["game_id"]:g for g in schedule["games"]}
    boxes,problems=verified_boxscores(games,root/"boxscores")
    req=urllib.request.Request(SOURCE,headers={"User-Agent":"SportsBot-NFLGradeVerifier"})
    with urllib.request.urlopen(req,timeout=75) as resp: data=resp.read()
    snaps=pd.read_parquet(io.BytesIO(data))
    candidates=build(read_csv(root/"pp_grading_pending_2026.csv"),games,
                     snaps.to_dict("records"))
    verified=[]
    for r in candidates:
        gid=r["game_id"]
        if gid in problems or gid not in boxes or r["player_id"] in boxes[gid]:continue
        # The primary stats feed must be present and independently validated.
        verified.append(r)
    payload={"season":2026,"source":SOURCE,
             "updated_at":datetime.now(timezone.utc).isoformat(),
             "zero_receiving_players":verified}
    if OUT.exists():
        previous=json.loads(OUT.read_text())
        old={(x["game_id"],x["player_id"]) for x in previous.get("zero_receiving_players",[])}
        new={(x["game_id"],x["player_id"]) for x in verified}
        if not old.issubset(new):
            raise ValueError("Verified NFL zero-stat snap coverage regressed; refusing overwrite")
        stable=dict(previous);stable.pop("updated_at",None)
        comparable=dict(payload);comparable.pop("updated_at",None)
        if stable==comparable:return payload
    OUT.write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n")
    print("Verified participated zero-target NFL players:",len(verified))
    return payload

if __name__=="__main__":run()
