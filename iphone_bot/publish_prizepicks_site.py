"""Publish small verified NBA PrizePicks UI board and no-cost slate coverage report.

Reads an already captured authenticated source file; never uses the API key,
re-queries a provider, invents a quote, or rewrites research/graded records.
"""
import json
from collections import Counter
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
FULL=ROOT/"docs/prizepicks.json"
SITE=ROOT/"docs/prizepicks_site.json"
STATUS=ROOT/"docs/prizepicks_status.json"
FIELDS=("id","player","team","game","stat","line","starts_at","observed_at",
        "more_tier","less_tier","source","is_demo","opponent",
        "event_start_source","combined_projection","difference","ai_direction")

def slim(offer):
    return {k:offer[k] for k in FIELDS if k in offer}

def summarize(board,schedule):
    accepted=board.get("status")=="LIVE_THIRD_PARTY_PRIZEPICKS_LINES"
    raw=board.get("board_offers") if accepted and isinstance(board.get("board_offers"),list) else []
    matched=board.get("offers") if accepted and isinstance(board.get("offers"),list) else []
    verified=[o for o in raw if isinstance(o,dict) and o.get("source")=="independent_prizepicksapi_com"
              and o.get("is_demo") is False and o.get("game") and o.get("starts_at")
              and (o.get("more_tier") or o.get("less_tier"))]
    # Event identity must include the actual scheduled tipoff. Identical
    # teams can meet on consecutive nights, so name-only coverage is unsafe.
    known=[g for g in schedule.get("games",[]) if isinstance(g,dict)
           and g.get("game") and g.get("start")]
    def parsed(value):
        try:
            t=datetime.fromisoformat(str(value).replace("Z","+00:00"))
            return t.astimezone(timezone.utc) if t.tzinfo else None
        except (TypeError,ValueError,OverflowError):return None
    def matching_offers(game):
        start=parsed(game.get("start"))
        if start is None:return []
        return [o for o in verified if o["game"]==game["game"]
                and (tip:=parsed(o.get("starts_at"))) is not None
                and abs((tip-start).total_seconds())<=30*60]
    by_game=Counter(o["game"] for o in verified)
    # Exclude already-started games from available line coverage, not from
    # original pregame research archive.
    now=datetime.now(timezone.utc)
    def future(value):
        try:
            t=datetime.fromisoformat(str(value).replace("Z","+00:00"))
            return t.tzinfo is not None and t>now
        except (TypeError,ValueError):return False
    scheduled=[g for g in known if future(g["start"])]
    offered=[g for g in scheduled if matching_offers(g)]
    # A partially paged board cannot prove that later scheduled games have no
    # lines. Separate near-tipoff coverage from future-date coverage without
    # making extra paid vendor requests.
    eastern=ZoneInfo("America/New_York")
    per_game=[]
    per_date={}
    for game in known:
        name=game["game"]
        try:
            start=datetime.fromisoformat(str(game["start"]).replace("Z","+00:00"))
        except (TypeError,ValueError):
            continue
        if start.tzinfo is None or start<=now:continue
        date=start.astimezone(eastern).date().isoformat()
        hours=round((start-now).total_seconds()/3600,2)
        matched_lines=matching_offers(game)
        has_lines=bool(matched_lines)
        reason=("LINES_OBSERVED" if has_lines else
                "NOT_OBSERVED_IN_PARTIAL_FEED" if board.get("partial_board") is True
                else "NOT_OBSERVED_IN_COMPLETE_FEED")
        per_game.append({"game":name,"game_date_eastern":date,
                         "hours_until_tipoff":hours,"line_offer_count":len(matched_lines),
                         "coverage_status":reason})
        day=per_date.setdefault(date,{"scheduled_games":0,"games_with_lines":0,
                                      "games_without_lines":0})
        day["scheduled_games"]+=1
        day["games_with_lines"]+=int(has_lines)
        day["games_without_lines"]+=int(not has_lines)
    health={"status":"INDEPENDENT_PRIZEPICKS_NBA_COVERAGE",
        "generated_at":now.isoformat(),
        "source_status":board.get("status"),"source_generated_at":board.get("generated_at"),
        "source_provider_health":board.get("provider_status"),
        "provider_board_fully_paged":board.get("complete_provider_board") is True,
        "board_coverage_scope":board.get("board_coverage_scope") or "UNVERIFIED_LEGACY_SCOPE",
        "source_partial_board":board.get("partial_board") is True,
        "pages_read":board.get("pages_read"),
        "source_rows_read":board.get("raw_rows_read"),
        "source_valid_upcoming_offers":board.get("eligible_upcoming_offers"),
        "valid_scheduled_market_rows":len(verified),
        "markets_by_game":dict(sorted(by_game.items())),
        "source_eligible_but_unassigned":board.get("unassigned_or_ambiguous_events"),
        "source_unassigned_reason_counts":board.get("unassigned_reason_counts",{}),
        "source_unassigned_reasons_available":isinstance(board.get("unassigned_reason_counts"),dict),
        "known_upcoming_scheduled_games":len(scheduled),
        "known_upcoming_games_with_lines":len(offered),
        "known_upcoming_games_without_lines":[g["game"]+" @ "+g["start"] for g in scheduled if not matching_offers(g)],
        "per_game_coverage":sorted(per_game,key=lambda x:(x["hours_until_tipoff"],x["game"])),
        "coverage_by_eastern_date":dict(sorted(per_date.items())),
        "missing_lines_are_provider_absence_verified":board.get("complete_provider_board") is True,
        "schedule_is_independently_complete":schedule.get("coverage_complete") is True,
        "source_spend_credits_reported":board.get("total_provider_charged_credits"),
        "source_credits_remaining":board.get("remaining_provider_credits"),
        "real_american_odds_provided":False,
        "confidence_is_calibrated":False,
        "missing_games_not_assumed_without_lines":True}
    site={"status":board.get("status"),"generated_at":board.get("generated_at"),
          "matched_count":len(matched),"independent_board_count":len(verified),
          "provider_status":board.get("provider_status"),
          "partial_board":board.get("partial_board"),
          "complete_provider_board":board.get("complete_provider_board"),
          "board_coverage_scope":board.get("board_coverage_scope") or "UNVERIFIED_LEGACY_SCOPE",
          "offers":[slim(x) for x in matched if isinstance(x,dict)],
          "board_offers":[slim(x) for x in verified],
          "source":"independent_prizepicksapi_com",
          "is_actual_sportsbook_american_odds":False}
    return site,health

def main():
    board=json.loads(FULL.read_text())
    schedule=json.loads((ROOT/"docs/nba_schedule.json").read_text())
    site,health=summarize(board,schedule)
    if site["status"]!="LIVE_THIRD_PARTY_PRIZEPICKS_LINES" or not site["board_offers"]:
        print("No verified independent PrizePicks full-slate input: retaining existing site snapshot")
        return
    SITE.write_text(json.dumps(site,separators=(",",":"),ensure_ascii=False)+"\n")
    STATUS.write_text(json.dumps(health,indent=2,ensure_ascii=False)+"\n")
    print("PRIZEPICKS SITE SNAPSHOT:",len(site["board_offers"]),
          "offers",len(health["markets_by_game"]),"games",
          "source complete",health["provider_board_fully_paged"],
          "games lacking lines",health["known_upcoming_games_without_lines"])

if __name__=="__main__":main()
