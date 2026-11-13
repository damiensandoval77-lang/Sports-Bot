"""Bounded official NBA final-box backfill for opponent research, NOT betting grades.

Uses a saved full-season fixture solely as ID/date/team discovery, the official
NBA league schedule to recover NBA IDs, and the final CDN box itself to prove
status, date and matchup. Does not trust a fixture as proof of a final game.
Research artifact only: no pushes, no original-ledger edits, no odds API calls.
"""
import argparse
import json
from urllib.parse import urlencode
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from iphone_bot.fetch_final_boxscores import (
    NBA_SCHEDULE, NBA_SCHEDULE_ALT, NBA_BOX, ESPN_BOX, request_json, verified_schedule_ids,
    final_schedule_boxscore, verified_direct_espn_summary, team, local_date
)
from iphone_bot.verified_final_cache import merge_rows
from research.verified_team_defense_context import final_games

MAX_GAMES = 90
MAX_LOOKBACK_DAYS = 25

def planned_games(schedule, now, limit=MAX_GAMES, lookback_days=MAX_LOOKBACK_DAYS):
    if (schedule.get("status") != "VERIFIED_PUBLISHED_NBA_2026_27_SEASON_BASELINE"
        or schedule.get("season") != "2026-27"
        or not schedule.get("source_url")):
        raise ValueError("no verified season schedule")
    if not 1 <= limit <= MAX_GAMES or not 1 <= lookback_days <= MAX_LOOKBACK_DAYS:
        raise ValueError("invalid query budget")
    if datetime.fromisoformat(schedule["generated_at"].replace("Z","+00:00")) > now:
        raise ValueError("schedule published after capture")
    cutoff = now - timedelta(days=lookback_days)
    matched=[]
    seen=set()
    for g in schedule.get("games",[]):
        try:
            tip = datetime.fromisoformat(g["start"].replace("Z","+00:00"))
            away,home=team(g["away_abbreviation"]),team(g["home_abbreviation"])
            day = local_date(g["start"])
            key=(day,away,home)
            if not away or not home or away==home or g["date_eastern"]!=day:
                continue
            if not cutoff <= tip < now-timedelta(hours=2):
                continue
            if key in seen:
                raise ValueError("ambiguous fixture")
            seen.add(key)
            matched.append((tip,key))
        except (TypeError, KeyError, ValueError) as err:
            if str(err)=="ambiguous fixture":
                raise
            continue
    return [key for _,key in sorted(matched,reverse=True)[:limit]]

def cached_schedule_ids(snapshot, targets, now):
    """Discovery hints only; every box must independently attest its identity."""
    if not isinstance(snapshot, dict) or snapshot.get("source_url") not in (NBA_SCHEDULE, NBA_SCHEDULE_ALT):
        return {}
    try:
        captured=datetime.fromisoformat(snapshot["captured_at"].replace("Z","+00:00"))
        if captured.tzinfo is None or captured > now:
            return {}
        return verified_schedule_ids(snapshot, set(targets))
    except (ValueError,TypeError,KeyError):
        return {}

def collect(season, existing_cache, *, now, request=request_json, limit=MAX_GAMES,
            schedule_snapshot=None):
    targets=planned_games(season,now,limit)
    # Baseline schedule ESPN IDs are discovery hints ONLY. The summary must
    # independently verify completed status and exact event, teams and date.
    hints={}
    for g in season.get("games",[]):
        gid=str(g.get("id") or "")
        key=(g.get("date_eastern"),team(g.get("away_abbreviation")),
             team(g.get("home_abbreviation")))
        if key not in targets or not gid.isdigit():continue
        if key in hints and hints[key]!=gid:
            hints[key]=None
        elif key not in hints:hints[key]=gid
    official={}
    schedule_error=None
    for url in (NBA_SCHEDULE,NBA_SCHEDULE_ALT):
        try:
            official=verified_schedule_ids(request(url),set(targets))
            if official:break
        except (OSError,ValueError,KeyError,TypeError) as err:
            schedule_error=type(err).__name__
    saved_ids=cached_schedule_ids(schedule_snapshot, targets, now)
    recovered_ids={key:gid for key,gid in saved_ids.items() if key not in official}
    official.update(recovered_ids)
    retrieved=[]
    errors=Counter()
    provider_games=Counter()
    espn_consecutive_http_errors=0
    circuit_open=False
    for key in targets:
        gid=official.get(key)
        rows=None
        scores=None
        if gid:
            try:
                payload=request(NBA_BOX.format(gid))
                candidate=final_schedule_boxscore(gid,key,lambda _url:payload)
                if candidate:
                    scores={side["teamTricode"]:side.get("score")
                            for side in (payload["game"]["awayTeam"],payload["game"]["homeTeam"])}
                    rows=candidate
            except (ValueError,TypeError,KeyError,OSError) as err:
                errors["nba_box_"+type(err).__name__]+=1
        if rows is None:
            espn_id=hints.get(key)
            if espn_id and not circuit_open:
                try:
                    payload=request(ESPN_BOX+"?"+urlencode({"event":espn_id}))
                    espn_consecutive_http_errors=0
                    candidate=verified_direct_espn_summary(espn_id,key,payload)
                    if candidate:
                        competition=payload["header"]["competitions"][0]
                        scores={team((item.get("team") or {}).get("abbreviation")):item.get("score")
                                for item in competition.get("competitors",[])}
                        rows=candidate
                except (ValueError,TypeError,KeyError,OSError) as err:
                    errors["espn_box_"+type(err).__name__]+=1
                    if type(err).__name__=="HTTPError":
                        espn_consecutive_http_errors+=1
                        if espn_consecutive_http_errors>=3:
                            circuit_open=True
                    else:
                        espn_consecutive_http_errors=0
            elif circuit_open:
                errors["espn_skipped_circuit_open"]+=1
            else:
                errors["no_verified_id_hints"]+=1
        if not rows or not scores:
            errors["no_verified_completed_box"]+=1
            continue
        # CDN or ESPN must have two independently attested final team totals.
        teams={key[1],key[2]}
        try:
            numeric_scores={t:float(v) for t,v in scores.items()
                            if type(v) in (str,int,float) and str(v).strip()}
        except (ValueError,TypeError):
            errors["invalid_final_score"]+=1
            continue
        if (set(numeric_scores)!=teams or any(not 0<=v<=250 for v in numeric_scores.values()) or
            {r["team"] for r in rows}!=teams or any(
                sum(r["team"]==t and not r.get("dnp_final_verified") for r in rows)<7
                or abs(sum(r["PTS"] for r in rows if r["team"]==t and
                           not r.get("dnp_final_verified"))-numeric_scores[t])>.01
                for t in teams)):
            errors["partial_or_inconsistent_final_box"]+=1
            continue
        if len({r["source"] for r in rows})!=1 or rows[0]["source"] not in ("NBA_CDN_FINAL","ESPN_FINAL"):
            errors["unverified_provider_type"]+=1
            continue
        provider_games[rows[0]["source"]]+=1
        retrieved.extend(rows)
    prior=existing_cache.get("rows",[]) if existing_cache.get("version")==1 else []
    merged=merge_rows(prior,retrieved)
    # Both NBA CDN and ESPN rows must satisfy the exact same final score gate.
    accepted={r["source_game_id"] for r in retrieved
              if r.get("source") in ("NBA_CDN_FINAL","ESPN_FINAL")}
    confirmed,_=final_games({"version":1,"rows":merged})
    valid={g["id"] for g in confirmed}
    # Whole-game consistency gate: drop any new event that failed final_games().
    valid_new=accepted & valid
    merged=[r for r in merged if r["source_game_id"] not in accepted or
            r["source_game_id"] in valid_new]
    return {"version":1,"status":"RESEARCH_OFFICIAL_NBA_FINAL_BOX_BACKFILL",
            "captured_at":now.isoformat(),"source":"NBA_CDN_FINAL_OR_ESPN_FINAL",
            "season_schedule_source":season["source_url"],
            "requested_games":len(targets),
            "official_ids_found":len(official),
            "official_ids_from_saved_discovery":len(recovered_ids),
            "verified_espn_id_hints":sum(bool(v) for v in hints.values()),
            "espn_http_circuit_open":circuit_open,
            "provider_outage_detected":circuit_open,
            "schedule_lookup_error":schedule_error,
            "verified_games_by_provider":dict(sorted(provider_games.items())),
            "verified_new_games":len(valid_new),
            "verified_combined_games":len(final_games({"version":1,"rows":merged})[0]),
            "failures":dict(sorted(errors.items())),
            "rows":merged,
            "production_approved":False,
            "retroactive_pregame_feature_claims":False,
            "note":"Official final observations captured now. Never claim availability at historical pick capture; does not change grading, sportsbook lines, model outputs or live odds."}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--schedule",default="docs/nba_season_schedule_2026_27.json")
    p.add_argument("--prior",default="docs/verified_final_player_cache.json")
    p.add_argument("--output",default="official-defense-history-research.json")
    p.add_argument("--limit",type=int,default=MAX_GAMES)
    a=p.parse_args()
    now=datetime.now(timezone.utc)
    snapshot_path=Path(__file__).resolve().parent/"data/official_nba_schedule_hints_2026_27.json"
    snapshot=json.loads(snapshot_path.read_text()) if snapshot_path.exists() else None
    result=collect(json.loads(Path(a.schedule).read_text()),
                   json.loads(Path(a.prior).read_text()),now=now,limit=a.limit,
                   schedule_snapshot=snapshot)
    Path(a.output).write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps({k:result.get(k) for k in (
        "status","requested_games","official_ids_found","verified_new_games",
        "verified_combined_games","failures","production_approved")},indent=2))

if __name__=="__main__":main()
