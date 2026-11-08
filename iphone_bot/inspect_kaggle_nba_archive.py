"""Inspect actual Kaggle dataset archive schema, without enabling model features.

Download bounded archive in GitHub Actions (not from the dashboard). Extract
ONLY CSV headers and a few sample rows to inspect feature eligibility.
No training datasets, bets, or live projections modified.
"""
import csv,io,json,os,re,tempfile,urllib.error,urllib.request,zipfile
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/"docs/kaggle_nba_stats_schema_audit.json"
URL="https://www.kaggle.com/api/v1/datasets/download/chevronronson/nba-stats-dataset"
MAX_COMPRESSED=300*1024*1024
MAX_PREVIEW_FILES=75
MARKET_NAMES=("odds","moneyline","spread","total","opening","closing","movement","price","vegas")
TRACKING_NAMES=("potential_ast","potential_assist","rebound_chance","reb_chance","tracking","touches","passes_made")
DATE_NAMES=("date","time","observed","created","updated","recorded","gameid","game_id")
SPORTSBOOK_MARKET=("odds","moneyline","spread","price","open","close")
def classify(name,headers):
    search=" ".join((name,*headers)).lower()
    return {
        "has_moneyline_or_odds_headers":any(x in " ".join(headers).lower() for x in SPORTSBOOK_MARKET),
        "has_tracking_headers":any(x in " ".join(headers).lower() for x in TRACKING_NAMES),
        "has_time_or_date_header":any(x in xcol.lower() for xcol in headers for x in DATE_NAMES),
        "may_be_historical_market_file":any(x in name.lower() for x in MARKET_NAMES)
    }
def inspect_zip(path):
    result=[]
    with zipfile.ZipFile(path) as zip:
        members=zip.infolist()
        files=[m for m in members if not m.is_dir()]
        for entry in files[:400]:
            record={"name":entry.filename,"compressed_bytes":entry.compress_size,
                    "uncompressed_bytes":entry.file_size}
            if (entry.filename.lower().endswith((".csv",".tsv")) and
                len(result)<MAX_PREVIEW_FILES):
                # Read at most 256KB per entry to avoid importing bulk data.
                with zip.open(entry) as src:
                    sample=src.read(262144).decode("utf-8-sig",errors="replace")
                sep="\t" if entry.filename.endswith(".tsv") else ","
                reader=csv.reader(io.StringIO(sample),delimiter=sep)
                try:columns=next(reader)
                except (StopIteration,csv.Error):columns=[]
                if len(columns)>250:columns=columns[:250]
                record["columns"]=columns
                record.update(classify(entry.filename,columns))
                try:
                    rows=[]
                    for row in reader:
                        if len(row)!=len(columns):continue
                        rows.append(dict(zip(columns,row)))
                        if len(rows)>=2:break
                    # only show field names and whether values exist; actual
                    # rows may include athlete identifiers and are not needed.
                    record["valid_preview_rows"]=len(rows)
                    record["nonempty_columns"]=[c for c in columns if any(r.get(c) not in (None,"") for r in rows)]
                except csv.Error:
                    record["valid_preview_rows"]=0
            result.append(record)
    return {"total_members":len(members),"total_files":len(files),
            "files":result,"files_truncated":len(files)>len(result),
            "moneyline_candidate_files":[x["name"] for x in result if x.get("has_moneyline_or_odds_headers")],
            "tracking_candidate_files":[x["name"] for x in result if x.get("has_tracking_headers")]}
def main():
    status={"status":"UNAVAILABLE","checked_at":datetime.now(timezone.utc).isoformat(),
            "source":"chevronronson/nba-stats-dataset","production_model_changed":False,
            "training_data_imported":False,"license_review_required":True}
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    try:
        req=urllib.request.Request(URL,headers={"User-Agent":"Sports-Bot-Kaggle-Schema-Audit/1.0"})
        with urllib.request.urlopen(req,timeout=45) as resp:
            declared=resp.headers.get("Content-Length")
            if declared and int(declared)>MAX_COMPRESSED:
                status.update(status="DOWNLOAD_TOO_LARGE",
                              declared_compressed_bytes=int(declared))
            else:
                with tempfile.TemporaryFile() as out:
                    received=0
                    while True:
                        chunk=resp.read(1024*1024)
                        if not chunk:break
                        received+=len(chunk)
                        if received>MAX_COMPRESSED:
                            status.update(status="DOWNLOAD_TOO_LARGE",
                                          bounded_limit_bytes=MAX_COMPRESSED)
                            break
                        out.write(chunk)
                    if status["status"]!="DOWNLOAD_TOO_LARGE":
                        out.seek(0)
                        report=inspect_zip(out)
                        status.update(report)
                        status["compressed_bytes"]=received
                        status["status"]="ARCHIVE_SCHEMAS_INSPECTED"
    except (urllib.error.URLError,ValueError,zipfile.BadZipFile,OSError,TimeoutError) as error:
        status.update(status="DOWNLOAD_OR_SCHEMA_FAILED",error_type=type(error).__name__)
    OUTPUT.write_text(json.dumps(status,indent=2,ensure_ascii=False)+"\n")
    print("Kaggle schema audit:",status["status"],"files:",status.get("total_files",0),
          "moneyline_candidates:",len(status.get("moneyline_candidate_files",[])),
          "tracking_candidates:",len(status.get("tracking_candidate_files",[])))
if __name__=="__main__":main()
