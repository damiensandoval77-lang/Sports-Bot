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
import subprocess
import re
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path("docs/nfl/data")
ARCHIVE=ROOT/"frozen_pick_history_2026.csv"
GRADES=ROOT/"pp_graded_2026.csv"
PENDING=ROOT/"pp_grading_pending_2026.csv"
HEALTH=ROOT/"grading_health_2026.json"
INACTIVES=ROOT/"verified_inactives_2026.json"
ZERO_SNAPS=ROOT/"verified_zero_snap_stats_2026.json"
FULL_SCORING=ROOT/"verified_full_scoring_2026_09_BUF_MIN.json"
SUPPLEMENTAL_SNAPS=ROOT/"verified_supplemental_snaps_2026.json"
FIELDS=["captured_at","season","week","game_id","player_id","player",
        "position","team","opponent","stat","target","line","odds_type",
        "proj","pick","model_pct"]
EVIDENCE_FIELDS=["p_more","p_less","p_push","matchup_evidence"]
FIELDS+=EVIDENCE_FIELDS
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
        key=tuple(r[k] for k in KEY)
        prior=rows.get(key)
        if prior:
            # Evidence can be restored only from the exact same original
            # snapshot identity AND unchanged frozen model values.
            if any(prior[k]!=r[k] for k in FIELDS if k not in EVIDENCE_FIELDS):
                raise ValueError("NFL_FROZEN_FORECAST_CONFLICT")
            for field in EVIDENCE_FIELDS:
                if prior[field] and r[field] and prior[field]!=r[field]:
                    raise ValueError("NFL_FROZEN_EVIDENCE_CONFLICT")
                r[field]=prior[field] or r[field]
        rows[key]=r
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

def verified_inactives(root=ROOT):
    """Only explicit, source-attributed inactive rows may void a frozen prop.

    Missing from a box score is NOT proof that a player did not play.
    """
    path=Path(root)/INACTIVES.name
    if not path.exists():return set()
    data=json.loads(path.read_text(encoding="utf-8"))
    if data.get("season")!=2026:raise ValueError("Wrong verified inactive season")
    result=set()
    for r in data.get("inactives",[]):
        if not all(str(r.get(key) or "").strip() for key in ("game_id","player_id","player","source_url","published_at")):
            raise ValueError("Unattributed NFL inactive; refusing void")
        pair=(r["game_id"],r["player_id"])
        if pair in result:raise ValueError("Duplicate verified inactive")
        result.add(pair)
    return result

def verified_zero_snaps(root=ROOT):
    path=Path(root)/ZERO_SNAPS.name
    if not path.exists():return set()
    data=json.loads(path.read_text(encoding="utf-8"))
    if data.get("season")!=2026:raise ValueError("Wrong zero-snap season")
    seen=set()
    for r in data.get("zero_receiving_players",[]):
        if not all(str(r.get(k) or "").strip() for k in
                   ("game_id","player_id","player","team","pfr_player_id","source_url")):
            raise ValueError("Unverified zero receiving evidence")
        if not r.get("verified_zero_targets") or int(r.get("offense_snaps") or 0)<1:
            raise ValueError("Zero receiving evidence without offense participation")
        key=(r["game_id"],r["player_id"])
        if key in seen:raise ValueError("Duplicate zero receiving evidence")
        seen.add(key)
    supplemental=Path(root)/SUPPLEMENTAL_SNAPS.name
    if supplemental.exists():
        extra=json.loads(supplemental.read_text(encoding="utf-8"))
        if extra.get("season")!=2026:raise ValueError("Wrong supplemental snap season")
        allowed={("2026_09_BUF_MIN","00-0040215","Gavin Bartholomew","MIN","BUF",6)}
        for r in extra.get("records",[]):
            identity=(r.get("game_id"),r.get("player_id"),r.get("player"),
                      r.get("team"),r.get("opponent"),r.get("offense_snaps"))
            if identity not in allowed or not str(r.get("source_url","")).startswith(
                    "https://nfl-depth-charts.com/games/"):
                raise ValueError("Unverified supplemental participation evidence")
            key=(r["game_id"],r["player_id"])
            if key in seen:raise ValueError("Duplicate supplemental snap record")
            seen.add(key)
    return seen

def verified_full_game_scoring(root=ROOT):
    """Only a source-attributed complete game scoring record is accepted.

    Conflicting boxscore TDs/team scores or mismatched fumble attributions
    stop grading instead of making up a zero.
    """
    path=Path(root)/FULL_SCORING.name
    if not path.exists():return {}
    data=json.loads(path.read_text(encoding="utf-8"))
    if (data.get("season")!=2026 or data.get("week")!=9 or
        data.get("game_id")!="2026_09_BUF_MIN" or
        data.get("away")!="BUF" or data.get("home")!="MIN" or
        (data.get("away_score"),data.get("home_score"))!=(23,6) or
        data.get("verified_final") is not True):
        raise ValueError("Unverified full NFL game scoring evidence")
    if len(data.get("source_urls",[]))<2 or not data.get("prizepicks_scoring_reference"):
        raise ValueError("Full NFL scoring source references missing")
    scoring=data["verified_game_scoring"]
    tds=scoring.get("touchdowns",[])
    if {(r.get("player_id"),r.get("type")) for r in tds}!={
        ("00-0040363","receiving"),("00-0037248","rushing")}:
        raise ValueError("Unexpected verified NFL touchdown ledger")
    for k in ("two_point_conversions","return_touchdowns","offensive_fumble_recovery_touchdowns"):
        if scoring.get(k)!=[]:raise ValueError("Unresolved extra NFL scoring event")
    fumbles=data["verified_fumbles_lost"]
    if (fumbles.get("BUF",{}).get("team_lost")!=0 or
        fumbles.get("BUF",{}).get("player_lost")!=[] or
        fumbles.get("MIN",{}).get("team_lost")!=1 or
        fumbles.get("MIN",{}).get("player_lost")!=[
         {"player_id":"00-0032950","player":"Carson Wentz","lost":1}]):
        raise ValueError("Unverified team fumble attribution")
    return {data["game_id"]:data}

def exact_fantasy_score(player,game_scoring):
    """PrizePicks offensive full-PPR, only when all components are proven."""
    if not game_scoring or player.get("team") not in ("BUF","MIN"):
        return None
    game_id=str(player.get("player_id") or "")
    # Confirm the boxscore matches the only two final-game touchdown scorers.
    tds=game_scoring["verified_game_scoring"]["touchdowns"]
    rush=sum(r["player_id"]==game_id and r["type"]=="rushing" for r in tds)
    rec=sum(r["player_id"]==game_id and r["type"]=="receiving" for r in tds)
    if (number(player.get("rushing_tds"))!=rush or
        number(player.get("receiving_tds"))!=rec):
        return None
    fields=("passing_yards","passing_tds","passing_interceptions",
            "rushing_yards","rushing_tds","receptions",
            "receiving_yards","receiving_tds")
    values={k:number(player.get(k)) for k in fields}
    if any(v is None for v in values.values()):return None
    # Source attributes the game's only lost fumble to Carson Wentz, who is
    # not an eligible fantasy pick in this frozen game; all others lost zero.
    lost=1 if game_id=="00-0032950" else 0
    return (0.04*values["passing_yards"]+4*values["passing_tds"]
            -values["passing_interceptions"]+0.1*values["rushing_yards"]
            +6*values["rushing_tds"]+values["receptions"]
            +0.1*values["receiving_yards"]+6*values["receiving_tds"]-lost)

def verified_zero_anytime_td(row,scoring,zero_snaps):
    """Zero TD requires complete game scoring AND independently verified snap."""
    key=(row["game_id"],row["player_id"])
    game=scoring.get(row["game_id"])
    if not game or key not in zero_snaps:return None
    all_td_ids={x["player_id"] for x in game["verified_game_scoring"]["touchdowns"]}
    return 0.0 if row["player_id"] not in all_td_ids else None

def grade_finals(history,schedule,boxes,box_problems,inactives=None,zero_snaps=None,full_scoring=None):
    finals={g for g,s in schedule.items() if s.get("status")=="final" and
            s.get("home_score") is not None and s.get("away_score") is not None}
    expected=closing(history,finals)
    grades=[]
    pending=[]
    inactives=inactives or set()
    zero_snaps=zero_snaps or set()
    full_scoring=full_scoring or {}
    for r in expected:
        out=dict(r)
        gid=r["game_id"]
        p=boxes.get(gid,{}).get(r["player_id"])
        reason=None
        if (gid,r["player_id"]) in inactives and gid in boxes and gid not in box_problems:
            # Exact player ID and game must match the published inactive report;
            # void is not counted in hit rate, even for More/Less lines.
            if p:raise ValueError("Verified inactive has offensive boxscore stats: "+gid)
            out.update(actual="",result="Void",won="",grade_status="void_verified_inactive")
            grades.append(out)
            continue
        if (gid,r["player_id"]) in zero_snaps and r["target"] in ("REC","REC_YDS","TGT") and gid in boxes and gid not in box_problems:
            if p:raise ValueError("Zero-receiving evidence conflicts with boxscore: "+gid)
            actual=0.0
            line=number(r["line"])
            side="More" if actual>line else "Less" if actual<line else "Push"
            out.update(actual="0",result=side,
                       won="" if side=="Push" else "1" if side==r["pick"] else "0",
                       grade_status="graded")
            grades.append(out)
            continue
        if gid in box_problems:reason="boxscore_unverified"
        elif gid not in boxes:reason="boxscore_not_yet_published"
        elif not p:
            if r["target"]=="ANY_TD":
                actual=verified_zero_anytime_td(r,full_scoring,zero_snaps)
                if actual is None:reason="player_not_in_verified_boxscore"
            else:reason="player_not_in_verified_boxscore"
        elif r["target"]=="FPTS":
            actual=exact_fantasy_score(p,full_scoring.get(gid))
            if actual is None:reason="unsupported_exact_fantasy_scoring"
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

def historic_snapshot(ref):
    if not re.fullmatch(r"[0-9a-f]{40}",ref):
        raise ValueError("NFL recovery requires exact immutable commit")
    def read(name):
        return subprocess.check_output(["git","show",f"{ref}:docs/nfl/data/{name}"])
    manifest=json.loads(read("latest_2026.json"))
    with tempfile.TemporaryDirectory(prefix="nfl-original-recovery-") as folder:
        path=Path(folder)
        (path/"latest_2026.json").write_text(json.dumps(manifest))
        for name in manifest.get("files",[]):
            if not isinstance(name,str) or not re.fullmatch(r"latest_2026_[0-9]{2}\.csv",name):
                raise ValueError("Invalid historical snapshot filename")
            (path/name).write_bytes(read(name))
        rows,issue=read_published_snapshot(path)
        if issue:raise ValueError(issue)
    return rows,manifest

def pending_counts(pending):
    standard=[p for p in pending if p.get("odds_type")=="standard"]
    return {"standard_pending_picks":len(standard),
            "alternative_tier_pending_excluded":sum(p.get("odds_type") in ("demon","goblin") for p in pending),
            "standard_pending_reasons":{reason:sum(p["grade_status"]==reason for p in standard)
                for reason in sorted({p["grade_status"] for p in standard})}}

def run(root=ROOT,recovery_ref=None):
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
    recovery_receipt=None
    receipt_path=Path(root)/"original_evidence_recovery_2026.json"
    if recovery_ref and (not receipt_path.exists() or
          json.loads(receipt_path.read_text()).get("source_commit")!=recovery_ref):
        original,original_manifest=historic_snapshot(recovery_ref)
        prior_history,_=collect_history(prior_history,original,schedule)
        recovery_receipt={"source_commit":recovery_ref,
            "captured_at":original_manifest["captured_at"],
            "source_rows":len(original),
            "source_rows_with_exact_evidence":sum(bool(r.get("matchup_evidence")) for r in original),
            "method":"IDENTICAL_FROZEN_SOURCE_BYTES_NO_RETROACTIVE_MODEL"}
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
    graded,pending,expected=grade_finals(history,schedule,boxscores,invalid,verified_inactives(root),verified_zero_snaps(root),verified_full_game_scoring(root))
    if expected!=expected_independent or expected!=len(graded)+len(pending):
        raise ValueError("NFL_FINAL_GRADE_COVERAGE_MISMATCH: no records written")
    # Only original frozen standard quotes enter official model hit rates.
    # Goblin/demon lines remain gradeable historical research, never votes
    # in the main hit-rate denominator or independent-pick count.
    standard=[g for g in graded if g["odds_type"]=="standard" and g["won"] in ("0","1")]
    official_standard=[g for g in graded if g["odds_type"]=="standard"
                       and g["grade_status"]=="graded"]
    alternative_graded=[g for g in graded if g["odds_type"] in ("goblin","demon")
                        and g["grade_status"]=="graded"]
    genuine_grades=sum(g["grade_status"]=="graded" for g in graded)
    voids=sum(g["grade_status"]=="void_verified_inactive" for g in graded)
    metrics={"season":2026,"archived_pregame_lines":len(history),
             "rejected_non_pregame_or_invalid_lines":rejected,
             "final_games_with_frozen_picks":len(frozen_final_ids),
             "frozen_final_pick_candidates":expected_independent,
             "expected_final_picks":expected,"graded_picks":genuine_grades,
             "void_picks":voids,
             "pending_picks":len(pending),
             **pending_counts(pending),
             "pushes":sum(x["result"]=="Push" for x in graded),
             "official_grading_scope":"FROZEN_STANDARD_LINE_ONLY",
             "standard_graded_picks_including_pushes":len(official_standard),
             "alternative_tier_historical_grades_excluded":len(alternative_graded),
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
    # Small durable active-game feed survives latest-snapshot rotation. Final
    # cards come from grade/pending ledgers with the same evidence columns.
    now=datetime.now(timezone.utc)
    active_ids={gid for gid,g in schedule.items() if g.get("status")!="final"
                and utc(g.get("kickoff_utc")) and utc(g["kickoff_utc"])<=now}
    active=closing(history,active_ids)
    active=[r for r in active if r["odds_type"]=="standard"]
    write_json_if_changed(Path(root)/"active_frozen_2026.json",
                          {"season":2026,"scope":"EXACT_ARCHIVED_PREGAME_ROWS","records":active})
    write_csv_if_changed(Path(root)/GRADES.name,graded,OUTPUT_FIELDS)
    write_csv_if_changed(Path(root)/PENDING.name,pending,OUTPUT_FIELDS)
    write_json_if_changed(Path(root)/HEALTH.name,metrics)
    if recovery_receipt:write_json_if_changed(receipt_path,recovery_receipt)
    print("NFL public grading:",json.dumps(metrics,sort_keys=True))
    return metrics

if __name__=="__main__":
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument("--recover-snapshot-ref")
    args=parser.parse_args()
    run(recovery_ref=args.recover_snapshot_ref)
