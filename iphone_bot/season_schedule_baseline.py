"""Validate and preserve the 2026-27 NBA regular-season fixture baseline.

A full-season *calendar* is not a live scoreboard, a player-prop feed, or
proof of NBA Cup TBD matchups. A cached verified season can safely restore
missing future games when the daily provider is down.
"""
import datetime as dt
from collections import Counter
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
SEASON = "2026-27"
START = dt.date(2026, 10, 20)
END = dt.date(2027, 4, 11)
STATUS = "VERIFIED_PUBLISHED_NBA_2026_27_SEASON_BASELINE"
TEAMS = {"ATL","BOS","BKN","CHA","CHI","CLE","DAL","DEN","DET",
         "GSW","HOU","IND","LAC","LAL","MEM","MIA","MIL","MIN",
         "NOP","NYK","OKC","ORL","PHI","PHX","POR","SAC","SAS",
         "TOR","UTA","WAS"}
MIN_FIXED_GAMES = 900

def instant(raw):
    try:
        t = dt.datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        return t.astimezone(dt.timezone.utc) if t.tzinfo else None
    except (TypeError, ValueError, OverflowError):
        return None

def valid_game(row):
    if not isinstance(row, dict): return False
    start = instant(row.get("start"))
    if not start or not START <= start.astimezone(ET).date() <= END:
        return False
    if row.get("date_eastern") != start.astimezone(ET).date().isoformat():
        return False
    h, a = row.get("home_abbreviation"), row.get("away_abbreviation")
    if h not in TEAMS or a not in TEAMS or h == a: return False
    if not row.get("id") or row.get("game") != str(row.get("away")) + " @ " + str(row.get("home")):
        return False
    return row.get("game_state") in {"pre", "in", "post"}

def build(games, *, now, source, source_url, minimum=MIN_FIXED_GAMES):
    if not source or not source_url:
        raise ValueError("Full season must have an identifiable published source")
    if not isinstance(games, list) or len(games) < minimum:
        raise ValueError("Full season fixture count too small")
    if not all(valid_game(g) for g in games):
        raise ValueError("Invalid regular-season game identity or Eastern date")
    ids = [str(g["id"]) for g in games]
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate published season game IDs")
    teams = {g[k] for g in games for k in ("away_abbreviation", "home_abbreviation")}
    if minimum == MIN_FIXED_GAMES and teams != TEAMS:
        raise ValueError("Not all 30 NBA teams present")
    # Keep only the published identity and original UTC tip time. Real-time
    # scores and game state belong to the independent daily/live feeds.
    frozen = [{k:g.get(k) for k in
             ("id","game","home","away","home_abbreviation","away_abbreviation",
              "start","date_eastern")} for g in games]
    counts = dict(sorted(Counter(g["date_eastern"] for g in frozen).items()))
    return {"status":STATUS,"season":SEASON,"generated_at":now.isoformat(),
            "source":source,"source_url":source_url,
            "coverage":"PUBLISHED_FIXED_REGULAR_SEASON_GAMES_ONLY",
            "total_games":len(frozen),"teams":len(teams),
            "first_day":START.isoformat(),"last_day":END.isoformat(),
            "daily_counts":counts,
            "games":sorted(frozen,key=lambda g:(g["start"],g["id"])),
            "caveat":"NBA Cup TBD games are not fabricated; postponed dates must be refreshed from verified daily fixtures."}

def validate(archive):
    if archive.get("status") != STATUS or archive.get("season") != SEASON:
        raise ValueError("Missing verified 2026-27 full season archive")
    rows = archive.get("games")
    if not isinstance(rows,list) or len(rows)<MIN_FIXED_GAMES or archive.get("total_games")!=len(rows):
        raise ValueError("Cached season incomplete or count inconsistent")
    if len({str(g.get("id")) for g in rows}) != len(rows):
        raise ValueError("Duplicate archived NBA game IDs")
    if not all(valid_game({**g,"game_state":"pre"}) for g in rows):
        raise ValueError("Corrupt archived NBA fixture identity")
    counted = dict(sorted(Counter(x["date_eastern"] for x in rows).items()))
    if archive.get("daily_counts") != counted or archive.get("teams") != 30:
        raise ValueError("Archived season dates or team coverage invalid")
    return archive

def reconcile_window(archive, days, observed=None):
    """Fill missing scheduled fixtures; preserve fresh scores from observed."""
    validate(archive)
    days = {d.isoformat() if isinstance(d,dt.date) else str(d) for d in days}
    expected = [g for g in archive["games"] if g["date_eastern"] in days]
    rows = {str(g["id"]): {**g,"game_state":"pre","home_score":None,"away_score":None,
                             "clock":None,"period":None,"status_detail":None}
            for g in expected}
    recovered = 0
    observed = observed or []
    for g in observed:
        if not valid_game(g) or g["date_eastern"] not in days: continue
        # A time correction or newly released NBA Cup game can come from a
        # fresh daily source, never from old sportsbook lines.
        for gid,old in list(rows.items()):
            if old["date_eastern"]==g["date_eastern"] and (
                gid==str(g["id"]) or (
                old["away_abbreviation"]==g["away_abbreviation"] and
                old["home_abbreviation"]==g["home_abbreviation"]
            )):
                del rows[gid]
                break
        rows[str(g["id"])]=g
    observed_ids={str(g["id"]) for g in observed}
    recovered=sum(1 for g in expected if str(g["id"]) in rows and str(g["id"]) not in observed_ids)
    games=sorted(rows.values(),key=lambda x:(x["start"],str(x["id"])))
    return {"games":games,"total_games":len(games),
            "dates_eastern":sorted(days),"coverage_complete":True,
            "baseline_recovered":recovered,"season_baseline_total":archive["total_games"]}
