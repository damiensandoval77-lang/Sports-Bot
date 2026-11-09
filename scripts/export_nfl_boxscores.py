"""Independent, final-only NFL player box scores from nflverse weekly parquet."""
import io,json,math,os,tempfile,time,urllib.request
from pathlib import Path
from datetime import datetime,timezone

YEAR=2026
SOURCE="https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_week_2026.parquet"
SCHEDULE=Path("docs/nfl/data/schedule_2026.json")
OUT=Path("docs/nfl/data/boxscores")
MARKETS={"passing":("attempts","completions","passing_yards","passing_tds","passing_interceptions"),
         "rushing":("carries","rushing_yards","rushing_tds"),
         "receiving":("targets","receptions","receiving_yards","receiving_tds")}
NUMERIC=set(("fumbles_lost",)).union(*MARKETS.values())
REQUIRED={"game_id","player_id","player_display_name","team","season","week","season_type"}

def fetch_stats():
    import pandas as pd
    problem=None
    for attempt in range(3):
        try:
            req=urllib.request.Request(SOURCE,headers={"User-Agent":"DamesPicks-NFLBoxscores"})
            with urllib.request.urlopen(req,timeout=75) as r:raw=r.read()
            if len(raw)<100:raise ValueError("Empty nflverse stats response")
            return pd.read_parquet(io.BytesIO(raw))
        except (OSError,ValueError) as error:
            problem=error
            if attempt<2:time.sleep(2*(attempt+1))
    raise RuntimeError(f"nflverse weekly stats unavailable: {problem}")

def numeric(value):
    try:
        v=float(value)
        return int(v) if math.isfinite(v) and v.is_integer() else round(v,2) if math.isfinite(v) else None
    except (ValueError,TypeError):return None

def build(schedule,frame):
    if schedule.get("game_count")!=272 or len(schedule.get("games",[]))!=272:
        raise ValueError("Incomplete NFL schedule")
    missing=REQUIRED-set(frame.columns)
    if missing:raise ValueError("Missing NFL stats fields: "+str(sorted(missing)))
    if not NUMERIC.intersection(frame.columns):raise ValueError("No football stats columns")
    finals={g["game_id"]:g for g in schedule["games"] if g["status"]=="final" and
            g["home_score"] is not None and g["away_score"] is not None}
    f=frame[frame.season.eq(YEAR)&frame.season_type.eq("REG")&
            frame.game_id.isin(finals)].copy()
    if f.empty:raise ValueError("No verified-final player games")
    # nflverse can include a few unattributed plays/rows. A player with no
    # GSIS ID must not be guessed from name or attached to the wrong team.
    unknown=f[["game_id","player_id"]].isna().any(axis=1)
    missing_count=int(unknown.sum())
    if missing_count:
        if missing_count>max(30,int(len(f)*.01)):
            raise ValueError(f"Too many unidentified player-game rows: {missing_count}/{len(f)}")
        print(f"Skipping {missing_count} stats rows without verified player/game IDs")
        f=f.loc[~unknown].copy()
    if f.duplicated(["game_id","player_id"]).any():
        raise ValueError("Duplicate player-game records")
    games={}
    for row in f.to_dict("records"):
        game=finals[str(row["game_id"])]
        if str(row["team"]) not in (game["home"],game["away"]):
            raise ValueError("Player team does not match scheduled matchup")
        record=games.setdefault(game["game_id"],{"game_id":game["game_id"],
            "week":int(game["week"]),"home":game["home"],"away":game["away"],
            "home_score":game["home_score"],"away_score":game["away_score"],
            "players":[]})
        # Export only players with recorded offensive box-score activity.
        # Defenders with no pass/rush/receiving events need not bloat the
        # iPhone view, but a real 0-yard game with attempts remains included.
        activity=("attempts","carries","targets","receptions",
                  "passing_yards","rushing_yards","receiving_yards",
                  "passing_tds","rushing_tds","receiving_tds")
        if not any((numeric(row.get(col)) or 0)>0 for col in activity):
            continue
        name=str(row.get("player_display_name") or "").strip()
        # Never publish an anonymous offensive player row. The GSIS ID is
        # authoritative for joins, and the human-readable name is mandatory
        # for a usable final boxscore.
        if not name or name.lower() in {"nan","none","null","<na>"}:
            raise ValueError(f"Missing verified display name for {row['player_id']} in {game['game_id']}")
        player={"player_id":str(row["player_id"]),
                "player":name,
                "team":str(row["team"]),"position":str(row.get("position") or "")}
        for col in sorted(NUMERIC):player[col]=numeric(row.get(col))
        record["players"].append(player)
    weeks={}
    for game in games.values():
        game["players"].sort(key=lambda p:(p["team"],p["player"]))
        weeks.setdefault(game["week"],[]).append(game)
    for records in weeks.values():records.sort(key=lambda g:g["game_id"])
    # A game with no verified offensive player names is not a valid boxscore.
    # Keep it explicitly pending instead of advertising a blank final table.
    for week,records in list(weeks.items()):
        weeks[week]=[g for g in records if g["players"]]
        if not weeks[week]:
            del weeks[week]
    return weeks,len(finals)

def prepare(schedule,stats,previous=None):
    weeks,finals=build(schedule,stats)
    old=set((previous or {}).get("game_ids",[]))
    current={g["game_id"] for items in weeks.values() for g in items}
    if not old.issubset(current):
        raise ValueError("Regressed game coverage: "+", ".join(sorted(old-current)[:10]))
    manifest={"season":YEAR,"updated_at":datetime.now(timezone.utc).isoformat(),
        "source":"nflverse stats_player_week_2026.parquet",
        "final_games":finals,"games_with_stats":len(current),
        "pending_boxscores":finals-len(current),"game_ids":sorted(current),
        "weeks":{str(w):len(v) for w,v in weeks.items()}}
    return weeks,manifest

def validate_against_published(weeks,out=OUT):
    """Never replace a complete game with a severely truncated player list."""
    previous_counts={}
    for week in weeks:
        path=out/f"week_{week:02d}.json"
        if path.exists():
            old=json.loads(path.read_text(encoding="utf-8"))
            if old.get("season")!=YEAR or int(old.get("week",-1))!=week:
                raise ValueError("Stored NFL boxscore has inconsistent season/week")
            for game in old.get("games",[]):
                previous_counts[game["game_id"]]=len(game.get("players",[]))
    for games in weeks.values():
        for game in games:
            n=len(game["players"])
            if n==0:raise ValueError("Final NFL game has zero named offensive players")
            if any(not str(p.get("player") or "").strip() or
                   str(p["player"]).strip().lower() in {"nan","none","null"}
                   for p in game["players"]):
                raise ValueError("Verified NFL boxscore contains a blank player name")
            before=previous_counts.get(game["game_id"],0)
            if before>=8 and n<before*.6:
                raise ValueError(f"Refusing truncated player boxscore for {game['game_id']}: {n}/{before}")
    return True

def run():
    schedule=json.loads(SCHEDULE.read_text(encoding="utf-8"))
    if schedule.get("season")!=YEAR:raise ValueError("Wrong NFL season")
    manifest_file=OUT/"manifest.json"
    previous=json.loads(manifest_file.read_text()) if manifest_file.exists() else {}
    weeks,manifest=prepare(schedule,fetch_stats(),previous)
    validate_against_published(weeks)
    # Do not commit timestamp-only refreshes; redundant commits repeatedly
    # cancel GitHub Pages deployments when NBA and NFL jobs share the site.
    comparable=dict(manifest)
    comparable.pop("updated_at",None)
    prior_content=dict(previous)
    prior_content.pop("updated_at",None)
    if comparable==prior_content:
        same=True
        for week,games in weeks.items():
            filename=OUT/f"week_{week:02d}.json"
            expected=json.dumps({"season":YEAR,"week":week,"games":games},separators=(",",":"))+"\n"
            if not filename.exists() or filename.read_text(encoding="utf-8")!=expected:
                same=False
                break
        if same:
            print(f"NFL boxscores unchanged: {manifest['games_with_stats']} verified; no new Pages deployment")
            return
    OUT.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="nfl-final-boxscores-") as tmp:
        stage=Path(tmp)
        for week,games in weeks.items():
            (stage/f"week_{week:02d}.json").write_text(
                json.dumps({"season":YEAR,"week":week,"games":games},separators=(",",":"))+"\n")
        (stage/"manifest.json").write_text(json.dumps(manifest,separators=(",",":"))+"\n")
        for week in weeks:
            os.replace(stage/f"week_{week:02d}.json",OUT/f"week_{week:02d}.json")
        os.replace(stage/"manifest.json",manifest_file)
    print(f"Final NFL boxscores: {manifest['games_with_stats']} available; {manifest['pending_boxscores']} pending")
if __name__=="__main__":run()
