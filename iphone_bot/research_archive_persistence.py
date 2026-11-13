"""Lossless, date-scoped research snapshots of authentic historical AI archives.

These archives preserve what WAS originally published; they must NEVER be
mistaken for genuinely prospective paper picks or used to backfill them.
"""
import gzip
import hashlib
import json
from datetime import datetime,timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"docs/ai_pregame_archive.json"
HISTORY=ROOT/"docs/research_history"

def parse_time(s):
    d=datetime.fromisoformat(str(s).replace("Z","+00:00"))
    if d.tzinfo is None:raise ValueError("Missing original timezone")
    return d.astimezone(timezone.utc)

def preserve(archive,root):
    if archive.get("status")!="FROZEN_PREGAME_HISTORICAL_ARCHIVE_NOT_LIVE":
        raise ValueError("Not a validated original pregame archive")
    source=parse_time(archive["original_board_generated_at"])
    day=archive["date_eastern"]
    if source.astimezone(ZoneInfo("America/New_York")).date().isoformat()!=day:
        # Board may legitimately have been generated the prior local day for
        # next day's game, so do NOT require source day = event day.
        pass
    items=archive["comparisons"]
    if not isinstance(items,list) or not items:raise ValueError("Empty archival comparisons")
    for r in items:
        tip=parse_time(r["start"])
        if source>=tip or tip.astimezone(ZoneInfo("America/New_York")).date().isoformat()!=day:
            raise ValueError("Post-tip or wrong-day archival comparison")
        if not r.get("player_id") or not r.get("game") or not r.get("stat") or not r.get("book_quotes"):
            raise ValueError("Unverified archival prediction")
    # Preserve all original research fields and real sportsbook offers exactly.
    raw=json.dumps(archive,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")
    digest=hashlib.sha256(raw).hexdigest()
    filename=source.strftime("%H%M%SZ")+"-"+digest[:12]+".json.gz"
    path=Path(root)/day/filename
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():
        content=gzip.decompress(path.read_bytes())
        if content!=raw:raise RuntimeError("Archived record changed after freezing")
        return path,False
    with path.open("wb") as f:
        f.write(gzip.compress(raw,compresslevel=9,mtime=0))
    return path,True

def main():
    archive=json.loads(SOURCE.read_text())
    path,created=preserve(archive,HISTORY)
    print("PERMANENT RESEARCH ARCHIVE",str(path.relative_to(ROOT)),
          "new",created,"originals",len(archive["comparisons"]),
          "games",len({r["game"] for r in archive["comparisons"]}),
          "source",archive["original_board_generated_at"])

if __name__=="__main__":main()
