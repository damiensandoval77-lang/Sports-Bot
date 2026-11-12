"""One authoritative, date-scoped NBA grading reconciliation from ORIGINAL ledgers.

A green workflow is NOT a green grading night. Report exact unresolved keys,
provider provenance, duplicate/conflicting records, grade arithmetic and
published-report drift. Never infer a DNP, manufacture a final or count a
source-unverified row as graded. No network or paid sportsbook APIs.
"""
import argparse
import json
import math
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
import unicodedata
from iphone_bot.verified_final_cache import verified_row
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
VALID_MARKETS = frozenset(("PTS", "REB", "AST", "PRA"))
FINAL_SOURCES = frozenset(("NBA_CDN_FINAL", "ESPN_FINAL"))
DNP_SOURCES = frozenset(("NBA_OFFICIAL_INACTIVE_CROSSCHECKED",
                         "VERIFIED_FINAL_BOXSCORE_DNP_CROSSCHECKED",
                         "ESPN_FINAL_BOX_ABSENT_INJURY_LISTED")) | FINAL_SOURCES
EXCLUSION_SOURCES = DNP_SOURCES | frozenset(("NBA_OFFICIAL_PRETIP_TRADE_CROSSCHECKED",))
NO_LINE_FINAL_STATES = frozenset(("GRADED", "EXCLUDED_VERIFIED_DNP",
                                  "EXCLUDED_VERIFIED_NONPARTICIPANT"))
STANDARD_FINAL_STATES = frozenset(("GRADED", "EXCLUDED_VERIFIED_DNP"))
ROOT = Path(__file__).resolve().parents[1]

def timestamp(raw):
    if not isinstance(raw, str):
        return None
    try:
        value = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except (ValueError, OverflowError):
        return None
    if value.tzinfo is None:
        return None
    return value.astimezone(timezone.utc)

def eastern_date(raw):
    t = timestamp(raw)
    return t.astimezone(ET).date().isoformat() if t else None

def identity(row):
    return tuple(str(row.get(k) or "") for k in
                 ("player_id", "team", "game", "start", "stat"))

def original_market_key(row):
    try:
        line = float(row["line"])
    except (ValueError, TypeError, KeyError):
        return None
    if not math.isfinite(line):
        return None
    return (*identity(row), line)

def is_number(v):
    return type(v) in (int, float) and math.isfinite(v)

def observed_final(row):
    status = row.get("status")
    source = row.get("final_source")
    if status == "GRADED":
        return (source in FINAL_SOURCES and bool(row.get("source_game_id"))
                and is_number(row.get("actual")))
    if status == "EXCLUDED_VERIFIED_DNP":
        return (source in DNP_SOURCES and bool(row.get("source_game_id"))
                and bool(row.get("verified_dnp_reason")) and row.get("actual") is None)
    if status == "EXCLUDED_VERIFIED_NONPARTICIPANT":
        return (source in EXCLUSION_SOURCES and bool(row.get("source_game_id"))
                and bool(row.get("verified_dnp_reason") or row.get("verified_transfer_reason") or
                         row.get("verified_nonparticipant_reason")))
    return False

def name_key(raw):
    return "".join(c for c in unicodedata.normalize("NFKD",str(raw or "").casefold())
                   if c.isalnum() and not unicodedata.combining(c))

def independently_verified_team_games(cache, date):
    """Report complete reciprocal NBA/ESPN finals; NEVER infer DNP from absence."""
    rows=cache.get("rows",[]) if isinstance(cache,dict) and cache.get("version")==1 else []
    if not isinstance(rows,list):
        return {}
    by_game={}
    for r in rows:
        if not isinstance(r,dict) or r.get("date")!=date or not verified_row(r):
            continue
        k=(str(r["source_game_id"]),r["team"],r["opponent"])
        by_game.setdefault(k,[]).append(r)
    found={}
    for (game_id,team,opponent),entries in by_game.items():
        reciprocal=by_game.get((game_id,opponent,team),[])
        played=[x for x in entries if x.get("dnp_final_verified") is not True]
        other=[x for x in reciprocal if x.get("dnp_final_verified") is not True]
        if len(played)<7 or len(other)<7:
            continue
        if (len({name_key(x["player"]) for x in played})!=len(played) or
            len({name_key(x["player"]) for x in other})!=len(other)):
            continue
        found.setdefault(team,[]).append({
            "source_game_id":game_id,
            "opponent":opponent,
            "played_names":{name_key(x["player"]) for x in played},
            "explicit_dnps":{name_key(x["player"]) for x in entries
                             if x.get("dnp_final_verified") is True},
            "observed_players":len(played)})
    # A team playing twice in the same date, or conflicting ID sources, cannot
    # be associated to a forecast without independent exact game evidence.
    return {team:games[0] for team,games in found.items() if len(games)==1}

def missing_player_evidence(player,team,verified_games):
    game=verified_games.get(team)
    if not game:
        return ("VERIFIED_COMPLETED_GAME_PLAYER_COVERAGE_NOT_ESTABLISHED",None)
    label=name_key(player)
    if label in game["played_names"]:
        reason="VERIFIED_PLAYER_PLAYED_BUT_GRADE_IDENTITY_NOT_MATCHED"
    elif label in game["explicit_dnps"]:
        reason="SOURCE_EXPLICIT_DNP_NOT_YET_APPLIED_TO_GRADE"
    else:
        reason="VERIFIED_FINAL_GAME_PLAYER_ABSENT_FROM_PLAYED_ROWS_DNP_NOT_PROVEN"
    return (reason,game["source_game_id"])

def reconcile(no_line_archive, actuals, standard, ai_report=None, published_report=None, final_cache=None,
              *, game_date, checked_at, overdue_hours=4):
    now = timestamp(checked_at)
    if now is None:
        raise ValueError("timezone-aware check required")
    try:
        target = datetime.strptime(game_date, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError("invalid Eastern game date") from exc
    if not (1 <= overdue_hours <= 72):
        raise ValueError("overdue threshold out of bounds")
    if (no_line_archive.get("status") != "IMMUTABLE_OBSERVED_PRETIP_NOLINE_AI_ARCHIVE"
        or actuals.get("version") != 1
        or standard.get("status") != "FROZEN_NEW_AI_ALL_MARKET"):
        raise ValueError("untrusted frozen source status")
    if any(not isinstance(x, list) for x in
           (no_line_archive.get("predictions"), actuals.get("records"),
            standard.get("records"))):
        raise ValueError("missing underlying ledger rows")

    defects = Counter()
    final_index = {}
    for result in actuals["records"]:
        if not isinstance(result, dict) or eastern_date(result.get("start")) != game_date:
            continue
        k = identity(result)
        if not all(k) or not observed_final(result):
            defects["INVALID_VERIFIED_FINAL_RECORD"] += 1
            continue
        if k in final_index:
            defects["DUPLICATE_OR_CONFLICTING_FINAL_IDENTITY"] += 1
            # Always quarantine ambiguous identity, even if duplicates agree.
            final_index[k] = None
        else:
            final_index[k] = result

    team_game_evidence=independently_verified_team_games(final_cache,game_date)
    missing_categories=Counter()
    ai_seen = set()
    ai_counts = Counter()
    unresolved_ai = []
    def overdue(row):
        start = timestamp(row.get("start"))
        return start is not None and now - start >= timedelta(hours=overdue_hours)

    for p in no_line_archive["predictions"]:
        if not isinstance(p, dict) or eastern_date(p.get("start")) != game_date:
            continue
        if not (p.get("is_pregame_prediction") is True and
                p.get("line") is None and p.get("stat") in VALID_MARKETS):
            defects["INVALID_PREGAME_AI_FORECAST"] += 1
            continue
        key = identity(p)
        cap, tip = timestamp(p.get("captured_at")), timestamp(p.get("start"))
        if not all(key) or cap is None or tip is None or not cap < tip:
            defects["INVALID_OR_LATE_PREGAME_AI"] += 1
            continue
        if key in ai_seen:
            defects["DUPLICATE_AI_FORECAST_IDENTITY"] += 1
            continue
        ai_seen.add(key)
        grade = final_index.get(key)
        if grade is None:
            ai_counts["unresolved"] += 1
            if overdue(p):
                ai_counts["overdue"] += 1
            reason,verified_id=missing_player_evidence(p.get("player"),key[1],team_game_evidence)
            missing_categories[reason]+=1
            unresolved_ai.append({"player_id":key[0],"player":p.get("player"),
                                  "team":key[1],"game":key[2],"start":key[3],
                                  "stat":key[4],"reason":reason,
                                  "verified_game_id":verified_id,
                                  "overdue":overdue(p)})
            continue
        if grade.get("captured_at") != p.get("captured_at") or not is_number(grade.get("projection")) or abs(
            grade["projection"] - p.get("projection", float("inf"))) > 1e-6:
            defects["AI_FINAL_CHANGED_FROZEN_PROJECTION"] += 1
        if grade.get("status") == "GRADED":
            ai_counts["graded"] += 1
            if not is_number(grade.get("absolute_error")) or abs(
                grade["absolute_error"] - abs(grade["projection"] - grade["actual"])) > .001:
                defects["AI_GRADE_ABSOLUTE_ERROR_MISMATCH"] += 1
        else:
            ai_counts["verified_exclusion"] += 1

    std_seen = set()
    std_counts = Counter()
    unresolved_standard = []
    for p in standard["records"]:
        if not isinstance(p, dict) or eastern_date(p.get("start")) != game_date:
            continue
        k = original_market_key(p)
        cap, tip, quote = (timestamp(p.get(c)) for c in
                           ("captured_at","start","market_updated"))
        if (k is None or not all(k[:5]) or p.get("stat") not in VALID_MARKETS
            or p.get("pickem_tier") != "standard"
            or p.get("standard_line_two_sided_verified") is not True
            or cap is None or tip is None or quote is None or
            not quote <= cap < tip or not is_number(p.get("projection"))):
            defects["INVALID_OR_LATE_STANDARD_PICK"] += 1
            continue
        if k in std_seen:
            defects["DUPLICATE_STANDARD_LINE_IDENTITY"] += 1
            continue
        std_seen.add(k)
        status = p.get("grade")
        if status == "GRADED":
            if (p.get("final_source") not in FINAL_SOURCES
                or not p.get("source_game_id") or not is_number(p.get("actual"))):
                defects["UNVERIFIED_STANDARD_GRADE"] += 1
                continue
            # Independently corroborate the published standard grade when the
            # separate AI final player ledger has the same player/game/stat.
            corroborated=final_index.get(identity(p))
            if corroborated is not None:
                if (corroborated.get("status")=="GRADED" and
                    (corroborated["actual"] != p["actual"] or
                     corroborated.get("source_game_id")!=p.get("source_game_id"))):
                    defects["STANDARD_GRADE_CONFLICTS_WITH_FINAL_LEDGER"] += 1
                elif corroborated.get("status")!="GRADED":
                    defects["STANDARD_GRADE_CONFLICTS_WITH_VERIFIED_EXCLUSION"] += 1
            expected_error = abs(p["projection"] - p["actual"])
            if not is_number(p.get("absolute_error")) or abs(
                expected_error - p["absolute_error"]) > .001:
                defects["STANDARD_ABSOLUTE_ERROR_MISMATCH"] += 1
            direction = (p.get("estimated_hit_chance") or {}).get("modeled_direction")
            # Integer original standard lines may push exactly. Published
            # direction_hit=None represents a verified push (neither win nor
            # loss), NOT a missing grade or incorrect binary prediction.
            if p["actual"] == k[-1] and direction in ("More", "Less"):
                expected_hit = None
                std_counts["push"] += 1
            elif direction == "More":
                expected_hit = p["actual"] > k[-1]
            elif direction == "Less":
                expected_hit = p["actual"] < k[-1]
            else:
                expected_hit = "INVALID_DIRECTION"
            if expected_hit == "INVALID_DIRECTION" or p.get("direction_hit") is not expected_hit:
                defects["STANDARD_DIRECTION_GRADE_MISMATCH"] += 1
            std_counts["graded"] += 1
        elif status == "EXCLUDED_VERIFIED_DNP":
            if (p.get("final_source") not in DNP_SOURCES or
                not p.get("source_game_id") or p.get("actual") is not None or
                p.get("direction_hit") is not None or not p.get("verified_dnp_reason")):
                defects["UNVERIFIED_STANDARD_VOID"] += 1
            std_counts["verified_exclusion"] += 1
        elif status == "PENDING":
            std_counts["unresolved"] += 1
            if overdue(p):
                std_counts["overdue"] += 1
            reason,verified_id=missing_player_evidence(p.get("player"),k[1],team_game_evidence)
            missing_categories[reason]+=1
            unresolved_standard.append({
                "player_id":k[0],"player":p.get("player"),"team":k[1],
                "game":k[2],"start":k[3],"stat":k[4],"line":k[5],
                "reason":reason,"verified_game_id":verified_id,
                "overdue":overdue(p)})
            if final_index.get(identity(p)) is not None:
                defects["STANDARD_VERIFIED_FINAL_NOT_APPLIED"] += 1
        else:
            defects["UNKNOWN_STANDARD_GRADE_STATE"] += 1

    ai_total = len(ai_seen)
    std_total = len(std_seen)
    ai_accounted = ai_counts["graded"] + ai_counts["verified_exclusion"] + ai_counts["unresolved"]
    std_accounted = std_counts["graded"] + std_counts["verified_exclusion"] + std_counts["unresolved"]
    if ai_accounted != ai_total:
        defects["AI_RECONCILIATION_SUM_MISMATCH"] += 1
    if std_accounted != std_total:
        defects["STANDARD_RECONCILIATION_SUM_MISMATCH"] += 1

    reports = {}
    if isinstance(ai_report, dict) and ai_report.get("game_date_eastern") == game_date:
        claims={"recorded_pregame_forecasts":ai_total,"graded":ai_counts["graded"],
                "ungraded":ai_counts["unresolved"]}
        mismatches={f:{"reported":ai_report.get(f),"recomputed":v}
                    for f,v in claims.items() if ai_report.get(f) != v}
        if mismatches:
            defects["AI_STATUS_REPORT_LEDGER_DRIFT"] += 1
        reports["ai_status_mismatch"] = mismatches
    else:
        defects["AI_STATUS_REPORT_MISSING_FOR_DATE"] += 1
        reports["ai_status_mismatch"] = {"game_date_eastern":"report missing or wrong date"}
    # Published pick settlement has no date-scoped claims: compare *only* its
    # all-dates counts to the all-dates frozen ledger, never to one night's rows.
    if isinstance(published_report, dict) and isinstance(published_report.get("counts"),dict):
        all_grade=Counter(str(p.get("grade")) for p in standard["records"])
        claims={"frozen_picks":len(standard["records"]),
                "graded":all_grade["GRADED"],
                "verified_dnp_excluded":all_grade["EXCLUDED_VERIFIED_DNP"],
                "pending":all_grade["PENDING"]}
        mismatches={k:{"reported":published_report["counts"].get(k,0),"recomputed":v}
                    for k,v in claims.items()
                    if published_report["counts"].get(k,0) != v}
        if mismatches:
            defects["STANDARD_PUBLISHED_REPORT_LEDGER_DRIFT"] += 1
        reports["standard_report_mismatch"] = mismatches
    else:
        defects["STANDARD_PUBLISHED_REPORT_MISSING"] += 1
        reports["standard_report_mismatch"] = {"counts":"published settlement report missing"}

    blockers = dict(sorted(defects.items()))
    if ai_counts["overdue"]:
        blockers["AI_OVERDUE_WITHOUT_VERIFIED_FINAL"] = ai_counts["overdue"]
    if std_counts["overdue"]:
        blockers["STANDARD_OVERDUE_WITHOUT_VERIFIED_FINAL"] = std_counts["overdue"]
    return {
        "status":("BLOCKED" if blockers else
                  "AWAITING_VERIFIED_FINALS" if ai_counts["unresolved"] or std_counts["unresolved"]
                  else "READY"),
        "scope":"ONE_EASTERN_GAME_DATE_TWO_INDEPENDENT_FORECAST_LEDGERS",
        "game_date_eastern":game_date,"checked_at":now.isoformat(),
        "ai_only":{"frozen":ai_total,**{k:ai_counts[k] for k in
                    ("graded","verified_exclusion","unresolved","overdue")}},
        "standard_line":{"frozen":std_total,**{k:std_counts[k] for k in
                    ("graded","verified_exclusion","unresolved","overdue","push")}},
        "published_report_reconciliation":reports,
        "blockers":blockers,
        "unresolved_ai_only":unresolved_ai,
        "unresolved_standard":unresolved_standard,
        "missing_final_evidence_categories":dict(sorted(missing_categories.items())),
        "verified_team_final_games":{team:{
            "game_id":x["source_game_id"],"opponent":x["opponent"],
            "observed_players":x["observed_players"]}
            for team,x in sorted(team_game_evidence.items())},
        "uses_real_verified_final_sources_only":True,
        "no_fabricated_dnp_or_final":True,
        "betting_hit_rate_reported":False,
        "notice":"A clean job is not a complete grading night. Missing final player rows remain pending, never losses or inferred DNPs. Each original standard line is a separate quote."
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--date",required=True,help="Eastern game date YYYY-MM-DD")
    p.add_argument("--output",default="docs/production_grading_reconciliation.json")
    p.add_argument("--fail-on-blockers",action="store_true")
    args=p.parse_args()
    def read(path):
        return json.loads((ROOT/path).read_text())
    result=reconcile(read("docs/ai_no_line_pregame_archive.json"),
        read("docs/ai_forecast_actual_ledger.json"),
        read("docs/lagged_matchup_all_market_ledger.json"),
        read("docs/ai_forecast_grade_status.json"),
        read("docs/dames-picks/published_pick_settlement.json"),
        final_cache=read("docs/verified_final_player_cache.json"),
        game_date=args.date,checked_at=datetime.now(timezone.utc).isoformat())
    path=Path(args.output)
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n")
    print("AUTHORITATIVE_GRADING_RECONCILIATION",json.dumps({
        k:result[k] for k in ("status","game_date_eastern","ai_only","standard_line","blockers")}))
    if args.fail_on_blockers and result["status"]!="READY":
        raise SystemExit("PRODUCTION_GRADING_INCOMPLETE: see detailed reconciliation report")

if __name__=="__main__":
    main()
