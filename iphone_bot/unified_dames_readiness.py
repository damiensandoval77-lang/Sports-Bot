"""Read-only unified Dame's Picks artifact integrity gate.

Checks merged NBA+NFL frontend and all essential input artifacts. Does not spend
provider credits, generate picks, rewrite frozen lines, or claim browser proof.
"""
import csv
import datetime as dt
import io
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DOCS=ROOT/"docs"

CORE_NBA={
    "frozen_models":"lagged_matchup_all_market_ledger.json",
    "schedule":"nba_schedule.json",
    "quote_archive":"prizepicks_pregame_line_archive.json",
    "capture_audit":"tonight_capture_gradeability.json",
}
CORE_NFL={
    "prop_manifest":"nfl/data/latest_2026.json",
    "schedule":"nfl/data/schedule_2026.json",
    "grading_health":"nfl/data/grading_health_2026.json",
    "graded_standard":"nfl/data/pp_graded_2026.csv",
    "pending_standard":"nfl/data/pp_grading_pending_2026.csv",
}
FRONTEND=("dames-picks/index.html","dames-picks/feeds.js","dames-picks/dames_take.js")

def _read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))

def capture_issue_codes(report):
    """Separate missing game capture from model/archived quote coverage.

    Unknown or legacy incomplete reports remain fail-closed. Coverage reasons
    never convert an incomplete capture report into a healthy one.
    """
    if report.get("status") == "CAPTURE_VERIFIED":
        return []
    summary = report.get("summary", {})
    if not isinstance(summary, dict):
        summary = {}
    games = report.get("games", [])
    total = summary.get("schedule_games")
    game_capture_verified = (
        isinstance(total, int) and total > 0
        and isinstance(games, list) and len(games) == total
        and all(summary.get(key) == total for key in (
            "games_with_saved_source_quotes", "games_with_frozen_ai",
            "games_with_line_backed_models"))
        and all(isinstance(game, dict)
                and all(isinstance(game.get(key), (int, float)) and game[key] > 0
                        for key in ("source_quotes", "frozen_ai_only", "frozen_line_backed"))
                and isinstance(game.get("issues"), list)
                and set(game["issues"]) <= {"STANDARD_MARKETS_WITHOUT_FROZEN_MODEL"}
                for game in games)
    )
    codes = []
    if not game_capture_verified:
        codes.append("PRETIP_CAPTURE_NOT_VERIFIED")
    historical = summary.get("total_standard_markets_without_frozen_model")
    if isinstance(historical, (int, float)) and historical > 0:
        codes.append("ARCHIVED_STANDARD_THRESHOLDS_WITHOUT_PRIMARY_MODEL")
    current = report.get("current_upcoming_coverage", {})
    if isinstance(current, dict) and current.get("status") == "INCOMPLETE":
        codes.append("CURRENT_STANDARD_OFFERS_WITHOUT_PRIMARY_MODEL")
    # An unexplained incomplete status must never silently pass.
    return codes or ["PRETIP_CAPTURE_NOT_VERIFIED"]

def evaluate(root=DOCS, now=None):
    now=now or dt.datetime.now(dt.timezone.utc)
    sections={"app":[],"NBA":[],"NFL":[]}
    def fail(area,code):
        if code not in sections[area]:
            sections[area].append(code)
    for entry in FRONTEND:
        if not (root/entry).is_file():
            fail("app","UNIFIED_FRONTEND_MISSING:"+entry)
    home=root/"dames-picks/index.html"
    if home.exists():
        html=home.read_text(encoding="utf-8")
        if "feeds.js" not in html or "dames_take.js" not in html:
            fail("app","FRONTEND_ADAPTER_MISSING")
        if not ('getJSON("nfl/data/latest_2026.json")' in html and
                'getJSON("lagged_matchup_all_market_ledger.json")' in html):
            fail("app","NBA_OR_NFL_HANDOFF_MISSING")
        if '../index.html' in html or '../nfl/index.html' in html:
            fail("app","RETIRED_DASHBOARD_LINK_REINTRODUCED")
    for path in ("index.html","nfl/index.html"):
        file=root/path
        if not file.is_file() or "location.replace(" not in file.read_text(encoding="utf-8"):
            fail("app","LEGACY_URL_NOT_REDIRECTING:"+path)
    for key,path in CORE_NBA.items():
        file=root/path
        if not file.is_file():
            fail("NBA","MISSING_"+key.upper())
            continue
        try:
            obj=_read_json(file)
            if not isinstance(obj,dict):raise ValueError("not object")
            if key=="frozen_models" and not isinstance(obj.get("records"),list):
                fail("NBA","FROZEN_MODEL_RECORDS_INVALID")
            if key=="schedule" and not isinstance(obj.get("games"),list):
                fail("NBA","NBA_GAME_SCHEDULE_INVALID")
            if key=="capture_audit":
                for code in capture_issue_codes(obj):
                    fail("NBA",code)
        except (ValueError,UnicodeError,OSError):
            fail("NBA","CORRUPT_"+key.upper())
    for key,path in CORE_NFL.items():
        file=root/path
        if not file.is_file():
            fail("NFL","MISSING_"+key.upper())
            continue
        try:
            if path.endswith(".csv"):
                with file.open(encoding="utf-8",newline="") as stream:
                    if not csv.DictReader(stream).fieldnames:
                        fail("NFL","CSV_HEADER_INVALID:"+key)
            else:
                obj=_read_json(file)
                if not isinstance(obj,dict):raise ValueError("not object")
                if key=="prop_manifest":
                    files=obj.get("files")
                    if not isinstance(files,list) or not files:
                        fail("NFL","MANIFEST_EMPTY")
                    else:
                        for shard in files:
                            if not isinstance(shard,str) or Path(shard).name!=shard or not (root/"nfl/data"/shard).is_file():
                                fail("NFL","MISSING_PROP_SHARD")
                if key=="schedule" and (not isinstance(obj.get("games"),list) or not obj["games"]):
                    fail("NFL","NFL_SCHEDULE_INVALID")
        except (ValueError,UnicodeError,OSError):
            fail("NFL","CORRUPT_"+key.upper())
    app_ready=not sections["app"]
    sports={sport:{"state":"READY" if not issues else "DEGRADED","issues":issues}
            for sport,issues in (("NBA",sections["NBA"]),("NFL",sections["NFL"]))}
    return {"checked_at":now.isoformat(),
            "status":"READY" if app_ready and all(x["state"]=="READY" for x in sports.values()) else "DEGRADED",
            "app":{"state":"READY" if app_ready else "DEGRADED","issues":sections["app"]},
            "sports":sports,
            "scope":"UNIFIED_ARTIFACT_INTEGRITY_ONLY",
            "live_browser_verified":False,
            "provider_refresh_verified":False,
            "note":"Artifact integrity is not proof of live browser rendering, current provider line availability, calibrated pick accuracy, or successful final grading."}

def main():
    report=evaluate()
    target=DOCS/"dames-picks/unified_readiness.json"
    target.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":report["status"],"app":report["app"],"sports":report["sports"]}))
    if report["status"]!="READY":
        raise SystemExit(2)

if __name__=="__main__":
    main()
