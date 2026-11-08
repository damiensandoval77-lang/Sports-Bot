"""Immutable lossless research input snapshots for real odds and NBA schedules.

Do not reconstruct an absent sportsbook quote, pretend a stale line is live,
or modify saved paper grades. Snapshots are source data only.
"""
import gzip
import hashlib
import json
import sys
from datetime import datetime,timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
HISTORY=ROOT/"docs/research_inputs"
ET=ZoneInfo("America/New_York")

def stamp(value):
    result=datetime.fromisoformat(str(value).replace("Z","+00:00"))
    if result.tzinfo is None:raise ValueError("Missing timezone")
    return result.astimezone(timezone.utc)

def source_payload(kind,docs):
    docs=Path(docs)
    if kind=="odds":
        odds=json.loads((docs/"data.json").read_text())
        compact=json.loads((docs/"odds_compact.json").read_text())
        provider=json.loads((docs/"odds_fetch_status.json").read_text())
        if not odds.get("picks") or not compact.get("picks") or provider.get("status") not in ("FETCHED","FETCHED_PARTIAL"):
            return None
        if not odds.get("updated_at") or odds.get("updated_at")!=compact.get("updated_at"):
            raise ValueError("Unmatched sportsbook quote timestamps")
        source=odds["updated_at"]
        return {"status":"ORIGINAL_PAID_PROVIDER_SOURCE_DATA_ARCHIVE_NOT_LIVE",
                "captured_source_at":source,"provider_health":provider,
                "full_odds_feed":odds,"compact_odds_feed":compact,
                "not_a_pregame_paper_pick":True}
    if kind=="prizepicks":
        feed=json.loads((docs/"prizepicks.json").read_text())
        if feed.get("status")!="LIVE_THIRD_PARTY_PRIZEPICKS_LINES" or not feed.get("board_offers"):
            return None
        source=feed["generated_at"]
        return {"status":"ORIGINAL_AUTHENTICATED_THIRD_PARTY_PRIZEPICKS_CAPTURE",
                "captured_source_at":source,"feed":feed,
                "is_pickem_not_sportsbook_american_odds":True,
                "not_a_retroactive_pregame_paper_pick":True}
    if kind=="schedule":
        slate=json.loads((docs/"nba_schedule.json").read_text())
        if not slate.get("games"):return None
        source=slate["generated_at"]
        return {"status":"ORIGINAL_REPORTED_NBA_FIXTURES_ARCHIVE",
                "captured_source_at":source,
                "schedule":slate,
                "not_proof_of_complete_slate":slate.get("coverage_complete") is not True,
                "not_sportsbook_lines":True}
    raise ValueError("Only odds, prizepicks or schedule source archives supported")

def preserve(kind,docs,root):
    report=source_payload(kind,docs)
    if report is None:return None,False
    at=stamp(report["captured_source_at"])
    date=at.astimezone(ET).date().isoformat()
    raw=json.dumps(report,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
    digest=hashlib.sha256(raw).hexdigest()[:12]
    path=Path(root)/kind/date/(at.strftime("%H%M%SZ")+"-"+digest+".json.gz")
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():
        if gzip.decompress(path.read_bytes())!=raw:
            raise RuntimeError("Frozen source record collision")
        return path,False
    path.write_bytes(gzip.compress(raw,compresslevel=9,mtime=0))
    return path,True

def main():
    if len(sys.argv)!=2:raise SystemExit("Usage: preserve_research_inputs.py odds|schedule|prizepicks")
    kind=sys.argv[1]
    path,created=preserve(kind,ROOT/"docs",HISTORY)
    print("RESEARCH SOURCE INPUT",kind,
          str(path.relative_to(ROOT)) if path else "NO_VALID_SOURCE",
          "new",created)

if __name__=="__main__":main()
