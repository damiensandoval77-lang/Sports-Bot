"""Prospective, verified NBA *team* defensive context from official final player boxes.

This is not defense-versus-position or a defender assignment. Strictly require
reciprocal finalized teams from the same official game ID, no partial boxscores,
and multiple independent prior games. Source cache has no publication timestamp:
the *workflow run* is the first attested as-of capture, never a retroactive
claimed original-pick feature. Never recompute historical picks or live HIT EST.
"""
import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

STATS = ("PTS", "REB", "AST", "PRA")
MIN_TEAMS_PLAYED = 7
MIN_DEFENSE_GAMES = 5

def timestamp(s):
    if not isinstance(s, str):
        raise ValueError("missing timestamp")
    t = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if t.tzinfo is None:
        raise ValueError("timezone required")
    return t.astimezone(timezone.utc)

def number(x):
    if type(x) not in (int, float) or not 0 <= x < float("inf"):
        raise ValueError("invalid stat total")
    return float(x)

def final_games(cache):
    if cache.get("version") != 1 or not isinstance(cache.get("rows"), list):
        raise ValueError("invalid official final cache")
    games = defaultdict(list)
    invalid_game_keys = set()
    for x in cache["rows"]:
        if not isinstance(x, dict) or x.get("source") not in ("NBA_CDN_FINAL","ESPN_FINAL") or x.get("final_confirmed") is not True:
            continue
        if not x.get("source_game_id") or not x.get("team") or not x.get("opponent") or not x.get("player") or not x.get("date"):
            continue
        key = (str(x["source_game_id"]), x["date"])
        if x["team"] == x["opponent"]:
            invalid_game_keys.add(key)
            continue
        # Official DNP records deliberately have no performance totals. They
        # neither invalidate an otherwise complete box nor count as players
        # who played. A contradictory or unexplained DNP remains a bad game.
        if x.get("dnp_final_verified") is True:
            if (not isinstance(x.get("dnp_reason"), str) or not x["dnp_reason"].strip()
                or any(x.get(stat) not in (None, 0) for stat in (*STATS, "MIN"))):
                invalid_game_keys.add(key)
            continue
        # A corrupt row invalidates the complete game: silently dropping it
        # would undercount that team's final score despite >=7 other rows.
        try:
            totals = {k:number(x[k]) for k in ("PTS","REB","AST")}
            if abs(number(x["PRA"]) - sum(totals.values())) > 1e-6:
                invalid_game_keys.add(key)
                continue
        except (KeyError, ValueError):
            invalid_game_keys.add(key)
            continue
        games[key].append(x)
    accepted = []
    rejected = Counter()
    for (gid, day), rows in sorted(games.items()):
        if (gid, day) in invalid_game_keys:
            rejected["invalid_final_player_stat"] += 1
            continue
        teams = sorted({x["team"] for x in rows})
        if len(teams) != 2:
            rejected["missing_reciprocal_team"] += 1
            continue
        a,b = teams
        by_team = {t:[x for x in rows if x["team"] == t] for t in teams}
        if any(len(by_team[t]) < MIN_TEAMS_PLAYED for t in teams):
            rejected["partial_boxscore"] += 1
            continue
        if any(any(x["opponent"] != (b if t == a else a) for x in by_team[t]) for t in teams):
            rejected["conflicting_opponents"] += 1
            continue
        if any(len({x["player"] for x in by_team[t]}) != len(by_team[t]) for t in teams):
            rejected["duplicate_player_identity"] += 1
            continue
        values = {t:{stat:sum(float(x[stat]) for x in by_team[t]) for stat in STATS} for t in teams}
        accepted.append({"id":gid,"date":day,"teams":teams,
                         "totals":values,"players_by_team":{t:len(by_team[t]) for t in teams},
                         "source":"NBA_CDN_FINAL_OR_ESPN_FINAL"})
    return accepted, dict(sorted(rejected.items()))

def build(cache, schedule, *, frozen_at):
    freeze = timestamp(frozen_at)
    schedule_time = timestamp(schedule["generated_at"])
    if schedule_time > freeze or not schedule.get("source_url"):
        raise ValueError("fixture source published after research freeze")
    games, rejected = final_games(cache)
    future = []
    counts = Counter()
    for fixture in schedule.get("games", []):
        tip = timestamp(fixture["start"])
        if tip <= freeze:continue
        date = fixture["date_eastern"]
        home, away = fixture["home_abbreviation"],fixture["away_abbreviation"]
        if home == away or not fixture.get("id") or not home or not away:
            raise ValueError("bad fixture identity")
        if not isinstance(date,str) or date != tip.astimezone(__import__("zoneinfo").ZoneInfo("America/New_York")).date().isoformat():
            raise ValueError("fixture Eastern date mismatch")
        report={"game_id":fixture["id"],"start":fixture["start"],
                "home":home,"away":away,"date_eastern":date,
                "team_defense":{}}
        for team,opp in ((home,away),(away,home)):
            eligible=[g for g in games if g["date"] < date and opp in g["teams"]]
            eligible.sort(key=lambda x:(x["date"],x["id"]))
            last5=eligible[-5:]
            if len({g["id"] for g in last5}) < MIN_DEFENSE_GAMES:
                counts["insufficient_verified_prior_defense_games"] += 1
                report["team_defense"][opp]={"status":"INSUFFICIENT_VERIFIED_PRIOR_GAMES",
                   "observed_games":len(last5),"required_games":MIN_DEFENSE_GAMES,
                   "position_adjustment_verified":False}
                continue
            # Opponent defense's allowed totals = reciprocal opposing offense.
            allowed = {stat:mean(g["totals"][next(t for t in g["teams"] if t!=opp)][stat]
                                 for g in last5) for stat in STATS}
            report["team_defense"][opp]={
                "status":"VERIFIED_PRIOR_TEAM_TOTALS_ONLY",
                "last5_team_totals_allowed":{k:round(v,3) for k,v in allowed.items()},
                "prior_game_ids":[g["id"] for g in last5],
                "prior_dates":[g["date"] for g in last5],
                "source":"NBA_CDN_FINAL_OR_ESPN_FINAL",
                "source_observed_in_research_at":frozen_at,
                "position_adjustment_verified":False,
                "individual_defender_verified":False,
                "not_a_modeled_hit_estimate":True}
        future.append(report)
    return {"status":"RESEARCH_TEAM_DEFENSE_NO_POSITION", "captured_at":frozen_at,
            "source":"NBA_CDN_FINAL_OR_ESPN_FINAL", "source_cache_published_at":None,
            "cache_publication_time_verified":False,
            "retroactive_feature_backfill_allowed":False,
            "production_hit_estimate_eligible":False,
            "min_independent_prior_games":MIN_DEFENSE_GAMES,
            "verified_final_games":len(games),
            "rejected_final_games":rejected,
            "future_games":future,
            "future_game_count":len(future),
            "blockers":dict(sorted(counts.items())),
            "note":"Team totals are not positional defense. Cache has no published_at; this research capture does not prove those games were available to an older pick. No opponent adjustment is promoted."}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--cache",default="docs/verified_final_player_cache.json")
    p.add_argument("--schedule",default="docs/nba_schedule.json")
    p.add_argument("--output",default="defense-evidence-research.json")
    a=p.parse_args()
    data=build(json.loads(Path(a.cache).read_text()),json.loads(Path(a.schedule).read_text()),
               frozen_at=datetime.now(timezone.utc).isoformat())
    Path(a.output).write_text(json.dumps(data,indent=2,sort_keys=True)+"\n")
    print(json.dumps({k:data[k] for k in ("status","captured_at","verified_final_games",
            "future_game_count","blockers","production_hit_estimate_eligible")},indent=2))

if __name__=="__main__":main()
