"""Grade archived standard-line research only from verified NBA final player rows.

This is a SEPARATE research scorecard, never the official validated model ledger.
No sportsbook calls, no retroactive projection edits, no alt-tier lines.
"""
import datetime as dt
import json
import math
from collections import defaultdict
from pathlib import Path
from iphone_bot.reconcile_grading_production import observed_final

from iphone_bot.archive_standard_quote_ai_research import STATUS, identity, moment

ROOT=Path(__file__).resolve().parents[1]
ARCHIVE=ROOT/"docs/standard_quote_ai_research_archive.json"
FINALS=ROOT/"docs/ai_forecast_actual_ledger.json"
FINAL_SOURCES={"NBA_CDN_FINAL","ESPN_FINAL"}
DNP_SOURCE="NBA_OFFICIAL_INACTIVE_CROSSCHECKED"

def player_key(row):
    return tuple(str(row.get(k) or "") for k in ("player_id","team","game","start","stat"))

def reconcile(archive, finals, now=None):
    now=now or dt.datetime.now(dt.timezone.utc)
    if archive.get("status")!=STATUS or not isinstance(archive.get("records"),list):
        raise ValueError("No verified independent research archive")
    pool=defaultdict(list)
    for row in finals.get("records",[]):
        if not isinstance(row,dict) or not row.get("source_game_id"):
            continue
        status=row.get("status")
        source=row.get("final_source")
        if status not in {"GRADED","EXCLUDED_VERIFIED_DNP"} or not observed_final(row):
            continue
        if status=="GRADED":
            try:
                actual=float(row["actual"])
                if not math.isfinite(actual) or actual<0 or actual>250:
                    continue
            except (ValueError,TypeError,KeyError):
                continue
        pool[player_key(row)].append(row)

    output=[]
    seen=set()
    counts={"HIT":0,"MISS":0,"PUSH":0,"VOID":0,"NO_LEAN":0,"UNSETTLED_RESEARCH":0}
    for old in archive["records"]:
        row=dict(old)
        ident=identity(row)
        if ident in seen:
            raise ValueError("Duplicate immutable quote in archive")
        seen.add(ident)
        if row.get("more_tier")!="standard" or row.get("less_tier")!="standard" or row.get("research_only") is not True:
            raise ValueError("Research archive includes unverified tier")
        recorded=row.get("grade")
        if recorded not in {"UNSETTLED_RESEARCH","HIT","MISS","PUSH","VOID","NO_LEAN"}:
            raise ValueError("Unrecognized historical research status")
        if recorded!="UNSETTLED_RESEARCH":
            counts[recorded]+=1
            output.append(row)
            continue
        started=moment(row.get("start"))
        if not started or now<=started:
            counts["UNSETTLED_RESEARCH"]+=1
            output.append(row)
            continue
        entries=pool.get(player_key(row),[])
        # Different verified sources may agree on the same final. If they
        # conflict, quarantine rather than pick whichever was processed first.
        signature={(x.get("status"),x.get("source_game_id"),
                    str(x.get("actual")) if x.get("status")=="GRADED" else "DNP") for x in entries}
        if len(signature)!=1:
            counts["UNSETTLED_RESEARCH"]+=1
            output.append(row)
            continue
        found=entries[0]
        if found["status"]=="EXCLUDED_VERIFIED_DNP":
            row.update(grade="VOID",actual=None,direction_hit=None,
                       grade_source=found["final_source"],
                       source_game_id=found["source_game_id"])
            counts["VOID"]+=1
        else:
            actual=float(found["actual"])
            line=float(row["line"])
            side=row.get("ai_direction")
            grade=("NO_LEAN" if side not in {"MORE","LESS"}
                   else "PUSH" if actual==line
                   else "HIT" if (actual>line if side=="MORE" else actual<line)
                   else "MISS")
            row.update(grade=grade,actual=actual,
                       direction_hit=True if grade=="HIT" else False if grade=="MISS" else None,
                       grade_source=found["final_source"],
                       source_game_id=found["source_game_id"])
            counts[grade]+=1
        output.append(row)
    eligible=counts["HIT"]+counts["MISS"]
    # Idempotent grading: no new results means no new published timestamp.
    # This avoids a needless Pages rebuild every scheduled postgame check.
    if (output == archive["records"]
            and archive.get("research_results") == counts
            and archive.get("research_directional_sample") == eligible):
        return archive
    return {
        **archive,"records":output,"count":len(output),
        "research_grading_checked_at":now.isoformat(),
        "research_results":counts,
        "research_directional_sample":eligible,
        "research_directional_hit_rate":round(counts["HIT"]/eligible,5) if eligible else None,
        "note":"Separate, uncalibrated standard-line research; not validated model hit rate or betting recommendation."
    }

def main():
    archive=json.loads(ARCHIVE.read_text())
    finals=json.loads(FINALS.read_text())
    updated=reconcile(archive,finals)
    ARCHIVE.write_text(json.dumps(updated,indent=2,ensure_ascii=False)+"\n")
    print("STANDARD LINE RESEARCH VERIFIED FINALS",updated["research_results"])

if __name__=="__main__":
    main()
