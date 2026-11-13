"""Audit exactly what NBA research evidence was durably saved.

No retroactive pick creation or AI model edits. Historical GitHub archive rows
and genuinely captured pre-tip paper records are counted SEPARATELY.
"""
import json
import gzip
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
from zoneinfo import ZoneInfo

try:
    from .paper_pick_pipeline import utc,identity
except ImportError:
    from paper_pick_pipeline import utc,identity

ROOT=Path(__file__).resolve().parents[1]
ET=ZoneInfo("America/New_York")

def read(path):
    try:return json.loads(Path(path).read_text())
    except (FileNotFoundError,ValueError):return {}

def eastern(s):
    return utc(s).astimezone(ET).date().isoformat()

def offer_key(row,book):
    try:
        return (str(row.get("player_id","")),str(row.get("team","")).upper(),
            str(row.get("game","")).casefold(),str(row.get("stat") or row.get("market")),
            str(book.get("name") or book.get("bookmaker") or "").casefold(),
            float(book.get("line",row.get("line"))))
    except (TypeError,ValueError,OverflowError):return None

def audit(paper,archive,slate,research,now=None,live_checkpoints=None,history_artifacts=None,source_inputs=None):
    now=now or datetime.now(timezone.utc)
    records=paper.get("records",[])
    report={"status":"RESEARCH_STORAGE_INTEGRITY_AUDIT",
            "generated_at":now.isoformat(),
            "date_eastern":now.astimezone(ET).date().isoformat(),
            "saved_paper_quotes":len(records),
            "paper_statuses":dict(Counter(str(r.get("status")) for r in records)),
            "paper_games":len({(str(r.get("game")),str(r.get("event_start")))
                               for r in records}),
            "paper_game_dates":{},
            "paper_invariant_errors":[],
            "archive":{},"slate":{},"research_diagnostics":{},
            "intermediate_live_player_stats_persisted":bool(live_checkpoints),
            "live_checkpoints":{
              "persisted_snapshot_files":len(live_checkpoints or []),
              "latest_capture_at":max((x.get("captured_at","") for x in (live_checkpoints or [])),default=None),
              "total_game_observations":sum(len(x.get("games",[])) for x in (live_checkpoints or [])),
              "today_snapshot_files":sum(x.get("date_eastern")==now.astimezone(ET).date().isoformat() for x in (live_checkpoints or []))},
            "permanent_archive_snapshots":len(history_artifacts or []),
            "original_source_input_snapshots":{
              "odds":sum(x.get("status")=="ORIGINAL_PAID_PROVIDER_SOURCE_DATA_ARCHIVE_NOT_LIVE" for x in (source_inputs or [])),
              "schedule":sum(x.get("status")=="ORIGINAL_REPORTED_NBA_FIXTURES_ARCHIVE" for x in (source_inputs or []))},
            "claims_every_game_has_props":False,
            "claims_missing_models_were_pregame_captured":False,
            "no_changes_to_saved_picks_or_live_probabilities":True}
    seen=set()
    date_counts=Counter()
    for r in records:
        try:
            key=identity(r)
            if key in seen:report["paper_invariant_errors"].append("DUPLICATE_QUOTE_IDENTITY")
            seen.add(key)
            if utc(r["captured_at"])>=utc(r["event_start"]):
                report["paper_invariant_errors"].append("LATE_CAPTURE")
            date_counts[eastern(r["event_start"])]+=1
        except (KeyError,TypeError,ValueError,OverflowError):
            report["paper_invariant_errors"].append("INVALID_PAPER_RECORD")
    report["paper_game_dates"]=dict(date_counts)
    archive_rows=archive.get("comparisons",[]) if archive.get("status")=="FROZEN_PREGAME_HISTORICAL_ARCHIVE_NOT_LIVE" else []
    archived_offers=set()
    archive_unique=set()
    rejected=Counter()
    try: generated=utc(archive.get("original_board_generated_at"))
    except (ValueError,TypeError): generated=None
    for row in archive_rows:
        try:
            if generated is None or generated>=utc(row["start"]):
                rejected["NO_ORIGINAL_PRETIP_EVIDENCE"]+=1
                continue
            if eastern(row["start"])!=archive.get("date_eastern"):
                rejected["OUTSIDE_ARCHIVE_GAME_DAY"]+=1
                continue
            archive_unique.add((str(row["player_id"]),str(row["game"]),
                                str(row["stat"]),float(row["line"])))
            for b in row.get("book_quotes",[]):
                key=offer_key(row,b)
                if key:archived_offers.add(key)
                else:rejected["INVALID_BOOK_OFFER"]+=1
        except (TypeError,ValueError,KeyError,OverflowError):rejected["INVALID_ARCHIVE_ROW"]+=1
    saved_offers=set()
    for row in records:
        try:
            if eastern(row["event_start"])==archive.get("date_eastern"):
                key=offer_key(row,row)
                if key:saved_offers.add(key)
        except (ValueError,TypeError,KeyError):continue
    # A quote in the original archive is not necessarily an eligible paper
    # selection. Group mismatches without inventing capture time or a bet.
    # The exact quote ledger remains the only prospective grading source.
    market_key=lambda key:(key[0],key[1],key[2],key[3])
    matching_markets={market_key(k) for k in saved_offers}
    matching_book_markets={(market_key(k),k[4]) for k in saved_offers}
    unmatched_reasons=Counter()
    for k in archived_offers-saved_offers:
        if (market_key(k),k[4]) in matching_book_markets:
            unmatched_reasons["PLAYER_MARKET_AND_BOOK_SAVED_DIFFERENT_LINE"]+=1
        elif market_key(k) in matching_markets:
            unmatched_reasons["PLAYER_MARKET_SAVED_DIFFERENT_BOOK"]+=1
        else:
            unmatched_reasons["NO_SAME_PLAYER_GAME_MARKET_IN_PAPER"]+=1
    report["archive"]={
        "date_eastern":archive.get("date_eastern"),
        "source_generated_at":archive.get("original_board_generated_at"),
        "archived_comparison_rows":len(archive_rows),
        "valid_independent_archived_player_market_lines":len(archive_unique),
        "archived_bookmaker_quotes":len(archived_offers),
        "matched_existing_paper_quote_keys":len(archived_offers&saved_offers),
        "archived_offers_not_found_in_paper":len(archived_offers-saved_offers),
        "archived_offer_mismatch_categories":dict(unmatched_reasons),
        "archive_only_offers_eligible_for_retroactive_grading":False,
        "paper_offers_not_in_current_archived_revision":len(saved_offers-archived_offers),
        "rejected_archive_evidence":dict(rejected),
        "historical_archive_is_not_a_new_paper_capture":True,
        "source_pretip_evidence_preserved":generated is not None}
    games=[g for g in slate.get("games",[])
           if isinstance(g,dict) and g.get("date_eastern")==report["date_eastern"]]
    # The provider schedule is explicitly not guaranteed full slate. Do not
    # count absent games as proof no prediction was captured.
    known={str(g.get("game")) for g in games}
    frozen_games={str(row.get("game")) for row in archive_rows}
    paper_today={str(row.get("game")) for row in records if
          row.get("event_start") and eastern(row["event_start"])==report["date_eastern"]}
    report["slate"]={
        "published_scheduled_games_today":len(known),
        "schedule_coverage_complete":slate.get("coverage_complete") is True,
        "scheduled_games_with_any_saved_paper_offer":len(known&paper_today),
        "scheduled_games_with_archived_predictions":len(known&frozen_games),
        "scheduled_games_without_any_paper_offer":sorted(known-paper_today),
        "scheduled_games_without_archived_predictions":sorted(known-frozen_games),
        "no_line_is_not_equivalent_to_no_game":True}
    unified=research.get("unified_reliability_v1") or {}
    statuses=unified.get("data_availability") or {}
    report["research_diagnostics"]={
        "research_ledger_markets":research.get("locked_samples"),
        "independent_research_markets":unified.get("independent_research_markets"),
        "frozen_sanity":statuses.get("sanity_shadow_v1_present",0),
        "frozen_20k_stress":statuses.get("stress_test_20k_v1_present",0),
        "frozen_model_disagreement":statuses.get("model_disagreement_v1_present",0),
        "missing_sanity":statuses.get("sanity_shadow_v1_missing",0),
        "missing_20k_stress":statuses.get("stress_test_20k_v1_missing",0),
        "missing_model_disagreement":statuses.get("model_disagreement_v1_missing",0),
        "missing_is_not_retrospectively_backfilled":True}
    return report

def compressed_records(folder):
    records=[]
    invalid=[]
    for path in sorted(folder.glob("*/*.json.gz")):
        try:records.append(json.loads(gzip.decompress(path.read_bytes())))
        except (OSError,ValueError,TypeError):invalid.append(str(path.relative_to(ROOT)))
    return records,invalid

def main():
    live,invalid_live=compressed_records(ROOT/"docs/research_live")
    saved,invalid_archives=compressed_records(ROOT/"docs/research_history")
    source_archives=[]
    invalid_sources=[]
    for path in sorted((ROOT/"docs/research_inputs").glob("*/*/*.json.gz")):
        try:source_archives.append(json.loads(gzip.decompress(path.read_bytes())))
        except (OSError,ValueError,TypeError):
            invalid_sources.append(str(path.relative_to(ROOT)))
    paper=read(ROOT/"docs/paper_pick_ledger.json")
    archive=read(ROOT/"docs/ai_pregame_archive.json")
    slate=read(ROOT/"docs/nba_schedule.json")
    research=read(ROOT/"docs/projection_upgrade_status.json")
    result=audit(paper,archive,slate,research,live_checkpoints=live,history_artifacts=saved,source_inputs=source_archives)
    result["corrupted_live_snapshots"]=invalid_live
    result["corrupted_historical_snapshots"]=invalid_archives
    result["corrupted_source_snapshots"]=invalid_sources
    out=ROOT/"docs/research_storage_integrity.json"
    out.write_text(json.dumps(result,indent=2)+"\n")
    print("RESEARCH STORAGE AUDIT",
          json.dumps({"quotes":result["saved_paper_quotes"],
            "statuses":result["paper_statuses"],
            "games_today":result["slate"]["published_scheduled_games_today"],
            "paper_games_today":result["slate"]["scheduled_games_with_any_saved_paper_offer"],
            "archived":result["archive"]["archived_comparison_rows"],
            "unpaired_archived_book_offers":result["archive"]["archived_offers_not_found_in_paper"],
            "missing_shadow":result["research_diagnostics"]["missing_sanity"],
            "issues":result["paper_invariant_errors"]},sort_keys=True))
    if result["paper_invariant_errors"] or invalid_live or invalid_archives or invalid_sources:
        raise SystemExit("RESEARCH_STORAGE_INTEGRITY_VIOLATION")

if __name__=="__main__":main()
