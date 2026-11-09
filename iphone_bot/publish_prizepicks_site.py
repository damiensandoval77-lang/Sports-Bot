"""Publish small verified NBA PrizePicks UI board and no-cost slate coverage report.

Reads an already captured authenticated source file; never uses the API key,
re-queries a provider, invents a quote, or rewrites research/graded records.
"""
import json
from collections import Counter
from datetime import datetime,timezone
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
    by_game=Counter(o["game"] for o in verified)
    known=[g for g in schedule.get("games",[]) if isinstance(g,dict)
           and g.get("game") and g.get("start")]
    # Exclude already-started games from available line coverage, not from
    # original pregame research archive.
    now=datetime.now(timezone.utc)
    def future(value):
        try:
            t=datetime.fromisoformat(str(value).replace("Z","+00:00"))
            return t.tzinfo is not None and t>now
        except (TypeError,ValueError):return False
    scheduled={g["game"] for g in known if future(g["start"])}
    offered={x for x in by_game if x in scheduled}
    health={"status":"INDEPENDENT_PRIZEPICKS_NBA_COVERAGE",
        "generated_at":now.isoformat(),
        "source_status":board.get("status"),"source_generated_at":board.get("generated_at"),
        "source_provider_health":board.get("provider_status"),
        "provider_board_fully_paged":board.get("complete_provider_board") is True,
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
        "known_upcoming_games_without_lines":sorted(scheduled-offered),
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
