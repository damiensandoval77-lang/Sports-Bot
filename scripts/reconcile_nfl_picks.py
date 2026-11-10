"""Independent public NFL frozen-pick archive and verified final grading.

Use only snapshots published before each game's scheduled kickoff. Keep
append-only pregame history, grade only verified final player game statistics,
and make unsupported markets/pending stat rows explicit rather than losses.
No connection to private GitHub credentials or live PrizePicks is required.
"""
import csv
import io
import json
import math
import os
import tempfile
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path("docs/nfl/data")
ARCHIVE=ROOT/"frozen_pick_history_2026.csv"
GRADES=ROOT/"pp_graded_2026.csv"
PENDING=ROOT/"pp_grading_pending_2026.csv"
HEALTH=ROOT/"grading_health_2026.json"
FIELDS=["captured_at","season","week","game_id","player_id","player",
        "position","team","opponent","stat","target","line","odds_type",
        "proj","pick","model_pct"]
KEY=["captured_at","game_id","player_id","target","odds_type","line"]
MARKET={
 "PASS_YDS":"passing_yards","PASS_ATT":"attempts","PASS_CMP":"completions",
 "PASS_TD":"passing_tds","PASS_INT":"passing_interceptions",
 "RUSH_YDS":"rushing_yards","RUSH_ATT":"carries",
 "REC_YDS":"receiving_yards","REC":"receptions","TGT":"targets"
}
OUTPUT_FIELDS=FIELDS+["actual","result","won","grade_status"]

def read_csv(path):
    path=Path(path)
    if not path.exists():return []
    with path.open(newline="",encoding="utf-8") as file:
        return list(csv.DictReader(file))

def utc(value):
    try:
        t=datetime.fromisoformat(str(value).replace("Z","+00:00"))
        return t.astimezone(timezone.utc) if t.tzinfo else None
    except (TypeError,ValueError):return None

def number(value):
    try:
        n=float(value)
        return n if math.isfinite(n) else None
    except (ValueError,TypeError):return None

def read_published_snapshot(root=ROOT):
    manifest=Path(root)/"latest_2026.json"
    if not manifest.exists():return [],"snapshot_missing"
    m=json.loads(manifest.read_text(encoding="utf-8"))
    files=m.get("files",[])
    if m.get("season")!=2026 or not files or len(files)>100:
        return [],"snapshot_manifest_invalid"
    rows=[]
    for filename in files:
        if Path(filename).name!=filename or not filename.startswith("latest_2026_") or not filename.endswith(".csv"):
            return [],"invalid_chunk_name"
        if not (Path(root)/filename).exists():return [],"snapshot_chunk_missing"
        rows.extend(read_csv(Path(root)/filename))
    if len(rows)!=m.get("rows"):
        return [],"snapshot_chunk_count_mismatch"
    if any(x.get("captured_at")!=m.get("captured_at") for x in rows):
        return [],"snapshot_timestamp_mismatch"
    return rows,None

def valid_frozen(row,schedule):
    game=schedule.get(str(row.get("game_id") or ""))
    if not game:return False
    captured=utc(row.get("captured_at"))
    kickoff=utc(game.get("kickoff_utc"))
    if not captured or not kickoff or captured>=kickoff:
        return False
    if not row.get("player_id") or not row.get("target") or not row.get("player"):
        return False
    if row.get("pick") not in ("More","Less") or number(row.get("line")) is None:
        return False
    if row.get("odds_type") not in ("standard","goblin","demon",""):
        return False
    return True

def normalize(row):
    out={field:str(row.get(field,"") if row.get(field) is not None else "") for field in FIELDS}
    if not out["odds_type"]:out["odds_type"]="standard"
    return out

def collect_history(existing,snapshot,schedule):
    rows={}
    rejected=0
    for row in list(existing)+list(snapshot):
        if not valid_frozen(row,schedule):
            rejected+=1
            continue
        r=normalize(row)
        rows[tuple(r[k] for k in KEY)]=r
    ordered=sorted(rows.values(),key=lambda r:(r["captured_at"],r["game_id"],r["player_id"],r["target"],r["odds_type"],float(r["line"])))
    return ordered,rejected

def closing(history,final_games):
    # Keep the last pre-kickoff standard line per game/player/market.
    # Goblin/demon lines have different payouts; each distinct quoted line is
    # frozen separately and excluded from standard-only hit-rate claims.
    standard={}
    alternatives={}
    for row in sorted(history,key=lambda r:r["captured_at"]):
        if row["game_id"] not in final_games:continue
        if row["odds_type"]=="standard":
            standard[(row["game_id"],row["player_id"],row["target"])]=row
        else:
            alternatives[(row["game_id"],row["player_id"],row["target"],row["odds_type"],row["line"])]=row
    return sorted(list(standard.values())+list(alternatives.values()),
        key=lambda r:(r["game_id"],r["player_id"],r["target"],r["odds_type"],float(r["line"])))

def verified_boxscores(schedule,boxroot=ROOT/"boxscores"):
    manifest=Path(boxroot)/"manifest.json"
    if not manifest.exists():return {},set()
    m=json.loads(manifest.read_text(encoding="utf-8"))
    if m.get("season")!=2026:return {},set()
    boxes={}
    problems=set()
    for week in range(1,19):
        file=Path(boxroot)/f"week_{week:02d}.json"
        if not file.exists():continue
        data=json.loads(file.read_text(encoding="utf-8"))
        if data.get("season")!=2026 or data.get("week")!=week:
            raise ValueError(f"Invalid NFL boxscore week {week}")
        for game in data.get("games",[]):
            gid=game.get("game_id")
            scheduled=schedule.get(gid)
            if gid in boxes or not scheduled or int(scheduled["week"])!=week:
                problems.add(gid)
                continue
            if scheduled.get("status")!="final" or any(game.get(x)!=scheduled.get(x)
                 for x in ("away","home","away_score","home_score")):
                problems.add(gid)
                continue
            players=game.get("players",[])
            if not players or len({p.get("player_id") for p in players})!=len(players):
                problems.add(gid)
                continue
            if any(not p.get("player_id") or not str(p.get("player","")).strip() or
                   p.get("team") not in (scheduled["home"],scheduled["away"])
                   for p in players):
                problems.add(gid)
                continue
            boxes[gid]={p["player_id"]:p for p in players}
    # An invalid source never counts as a verified outcome.
    for gid in problems:boxes.pop(gid,None)
    return boxes,problems

def actual_for(target,player):
    if target in MARKET:
        return number(player.get(MARKET[target]))
    if target=="RUSH_REC_YDS":
        values=[number(player.get("rushing_yards")),number(player.get("receiving_yards"))]
        return sum(values) if None not in values else None
    if target=="PASS_RUSH_YDS":
        values=[number(player.get("passing_yards")),number(player.get("rushing_yards"))]
        return sum(values) if None not in values else None
    if target=="ANY_TD":
        values=[number(player.get("rushing_tds")),number(player.get("receiving_tds"))]
        return sum(values) if None not in values else None
    # This feed does NOT include every two-point conversion and fumble
    # component necessary for an exact Fantasy Score. Refuse to guess.
    return None

def grade_finals(history,schedule,boxes,box_problems):
    finals={g for g,s in schedule.items() if s.get("status")=="final" and
            s.get("home_score") is not None and s.get("away_score") is not None}
    expected=closing(history,finals)
    grades=[]
    pending=[]
    for r in expected:
        out=dict(r)
        gid=r["game_id"]
        p=boxes.get(gid,{}).get(r["player_id"])
        reason=None
        if gid in box_problems:reason="boxscore_unverified"
        elif gid not in boxes:reason="boxscore_not_yet_published"
        elif not p:reason="player_not_in_verified_boxscore"
        elif r["target"]=="FPTS":reason="unsupported_exact_fantasy_scoring"
        elif r["target"] not in MARKET and r["target"] not in ("RUSH_REC_YDS","PASS_RUSH_YDS","ANY_TD"):
            reason="unsupported_market"
        else:
            actual=actual_for(r["target"],p)
            if actual is None:reason="missing_required_player_stat"
        if reason:
            out.update(actual="",result="",won="",grade_status=reason)
            pending.append(out)
            continue
        line=number(r["line"])
        side="More" if actual>line else "Less" if actual<line else "Push"
        win="" if side=="Push" else "1" if side==r["pick"] else "0"
        out.update(actual=str(int(actual) if actual.is_integer() else actual),
                   result=side,won=win,grade_status="graded")
        grades.append(out)
    return grades,pending,len(expected)

def write_csv_if_changed(path,rows,fields):
    file=Path(path)
    buf=io.StringIO(newline="")
    w=csv.DictWriter(buf,fieldnames=fields,extrasaction="ignore")
    w.writeheader()
    w.writerows(rows)
    content=buf.getvalue()
    if file.exists() and file.read_text(encoding="utf-8")==content:return False
    file.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile("w",dir=str(file.parent),delete=False,encoding="utf-8",newline="") as tmp:
        tmp.write(content)
        name=tmp.name
    os.replace(name,file)
    return True

def write_json_if_changed(path,object):
    content=json.dumps(object,sort_keys=True,indent=2)+"\n"
    file=Path(path)
    if file.exists() and file.read_text(encoding="utf-8")==content:return False
    file.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile("w",dir=str(file.parent),delete=False,encoding="utf-8") as tmp:
        tmp.write(content)
        name=tmp.name
    os.replace(name,file)
    return True

def run(root=ROOT):
    schedule_data=json.loads((Path(root)/"schedule_2026.json").read_text(encoding="utf-8"))
    if schedule_data.get("game_count")!=272:
        raise ValueError("Incomplete season schedule; refusing grade update")
    schedule={g["game_id"]:g for g in schedule_data["games"]}
    if len(schedule)!=272:raise ValueError("Duplicated scheduled games")
    snapshot,source_issue=read_published_snapshot(root)
    archive_path=Path(root)/ARCHIVE.name
    prior_history=read_csv(archive_path)
    prior_health_path=Path(root)/HEALTH.name
    prior_health=json.loads(prior_health_path.read_text(encoding="utf-8")) if prior_health_path.exists() else {}
    history,rejected=collect_history(prior_history,snapshot,schedule)
    # An API outage, corrupted archive or invalid snapshot may not silently
    # reduce the number of durable valid frozen pregame observations.
    prior_reported=prior_health.get("archived_pregame_lines",0)
    if not isinstance(prior_reported,int) or prior_reported<0:
        raise ValueError("Invalid previous NFL grading coverage")
    if len(history)<max(len(prior_history),prior_reported):
        raise ValueError(
            "NFL_FROZEN_ARCHIVE_REGRESSION: prior history or published "
            "coverage exceeds recoverable source records; no grades overwritten")
    boxscores,invalid=verified_boxscores(schedule,Path(root)/"boxscores")
    final_ids={gid for gid,game in schedule.items()
               if game.get("status")=="final" and game.get("home_score") is not None
               and game.get("away_score") is not None}
    frozen_final_ids={r["game_id"] for r in history if r["game_id"] in final_ids}
    expected_independent=len(closing(history,final_ids))
    graded,pending,expected=grade_finals(history,schedule,boxscores,invalid)
    if expected!=expected_independent or expected!=len(graded)+len(pending):
        raise ValueError("NFL_FINAL_GRADE_COVERAGE_MISMATCH: no records written")
    standard=[g for g in graded if g["odds_type"]=="standard" and g["won"] in ("0","1")]
    metrics={"season":2026,"archived_pregame_lines":len(history),
             "rejected_non_pregame_or_invalid_lines":rejected,
             "final_games_with_frozen_picks":len(frozen_final_ids),
             "frozen_final_pick_candidates":expected_independent,
             "expected_final_picks":expected,"graded_picks":len(graded),
             "pending_picks":len(pending),
             "pushes":sum(x["result"]=="Push" for x in graded),
             "standard_settled":len(standard),
             "standard_wins":sum(g["won"]=="1" for g in standard),
             "standard_hit_rate":round(100*sum(g["won"]=="1" for g in standard)/len(standard),2) if standard else None,
             "pending_reasons":dict(sorted({reason:sum(p["grade_status"]==reason for p in pending)
                                   for reason in {p["grade_status"] for p in pending}}.items())),
             "invalid_boxscore_games":sorted(str(x) for x in invalid),
             "source_snapshot_status":source_issue or "verified"}
    if metrics["final_games_with_frozen_picks"] and not metrics["expected_final_picks"]:
        raise ValueError("NFL_FINAL_GAME_WITH_FROZEN_PICKS_NOT_RECONCILED")
    # Fail closed on a bad new snapshot while still grading already archived
    # predictions; never destroy previous frozen history.
    write_csv_if_changed(archive_path,history,FIELDS)
    write_csv_if_changed(Path(root)/GRADES.name,graded,OUTPUT_FIELDS)
    write_csv_if_changed(Path(root)/PENDING.name,pending,OUTPUT_FIELDS)
    write_json_if_changed(Path(root)/HEALTH.name,metrics)
    print("NFL public grading:",json.dumps(metrics,sort_keys=True))
    return metrics

if __name__=="__main__":
    run()
