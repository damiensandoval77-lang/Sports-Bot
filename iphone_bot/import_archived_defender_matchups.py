"""Import independently archived 2025-26 NBA defender matchup parquet safely.

This is a public, research-only mirror, not live projected defender coverage.
Schemas MUST be explicitly recognized and validated; a missing or ambiguous
column yields a diagnostic, not fabricated data. The 2025-26 regular-season
file must predate 2026-27 evaluation games.
"""
import datetime as dt
import json
import pathlib
import urllib.error
import urllib.request

try:
    from .defender_matchup_v3 import SOURCE, ROOT, clean_matchup
except ImportError:
    from defender_matchup_v3 import SOURCE,ROOT,clean_matchup

STATUS=ROOT/"docs/defender_v3_source_status.json"
PARQUET_URL="https://huggingface.co/datasets/cdechoch/nba-data-archive/resolve/main/per_season/matchups/2025.parquet"
SEASON=2025
# Historical data predates the current 2026-27 season.
SOURCE_THROUGH="2026-07-01T00:00:00Z"
FIELDS={
 "OFF_PLAYER_ID":("OFF_PLAYER_ID","OFFPLAYERID","OFFENSIVE_PLAYER_ID","offPlayerId"),
 "DEF_PLAYER_ID":("DEF_PLAYER_ID","DEFPLAYERID","DEFENSIVE_PLAYER_ID","defPlayerId"),
 "PARTIAL_POSS":("PARTIAL_POSS","PARTIAL_POSS_COUNT","PARTIALPOSSESSIONS","matchupPossessions"),
 "MATCHUP_MIN":("MATCHUP_MIN","MATCHUP_MINUTES","MATCHUPMIN","matchupMinutes"),
 "MATCHUP_FGA":("MATCHUP_FGA","MATCHUPFIELDGOALSATTEMPTED","MATCHUP_FG_ATTEMPTS","matchupFGA"),
 "MATCHUP_FGM":("MATCHUP_FGM","MATCHUPFIELDGOALSMADE","MATCHUP_FG_MADE","matchupFGM"),
}

def normalize_schema(columns):
    columns=list(columns)
    out={}
    used=set()
    for canonical,alternatives in FIELDS.items():
        matched=[c for c in columns if c in alternatives]
        if len(matched)!=1 or matched[0] in used:
            raise ValueError("Unsupported/ambiguous matchup schema for "+canonical)
        out[canonical]=matched[0]
        used.add(matched[0])
    return out

def convert_table(table):
    mapping=normalize_schema(table.column_names)
    if "_season" not in table.column_names or "_season_type" not in table.column_names:
        raise ValueError("Missing archive season provenance")
    import pyarrow.compute as pc
    seasons=pc.unique(table["_season"]).to_pylist()
    types=pc.unique(table["_season_type"]).to_pylist()
    if set(seasons)!={SEASON} or set(types)!={"rg"}:
        raise ValueError("Archive contains other seasons or playoff rows")
    subset=table.select(list(mapping.values())).rename_columns(list(mapping))
    grouped={}
    for raw in subset.to_pylist():
        clean=clean_matchup(raw)
        if clean is None:continue
        key=(clean["off_id"],clean["def_id"])
        agg=grouped.setdefault(key,{"OFF_PLAYER_ID":clean["off_id"],
                "DEF_PLAYER_ID":clean["def_id"],"PARTIAL_POSS":0.,
                "MATCHUP_MIN":0.,"MATCHUP_FGA":0.,"MATCHUP_FGM":0.})
        for source,target in (("poss","PARTIAL_POSS"),("minutes","MATCHUP_MIN"),
                              ("fga","MATCHUP_FGA"),("fgm","MATCHUP_FGM")):
            agg[target]+=clean[source]
    if len(grouped)<100:raise ValueError("Too few valid NBA matchup pairs")
    return list(grouped.values())

def download(url=PARQUET_URL,timeout=22):
    request=urllib.request.Request(url,headers={"User-Agent":"Sports-Bot-NBA-Research/1.0"})
    with urllib.request.urlopen(request,timeout=timeout) as response:
        # Defensive cap; the documented file is ~4.8MB compressed.
        raw=response.read(20_000_001)
        if len(raw)>20_000_000:raise ValueError("Unexpected archive file size")
        if not raw.startswith(b"PAR1") or not raw.endswith(b"PAR1"):
            raise ValueError("Not a valid Parquet download")
        return raw

def import_data(parquet_bytes):
    import io
    import pyarrow.parquet as pq
    table=pq.read_table(io.BytesIO(parquet_bytes))
    return convert_table(table),table.column_names,table.num_rows

def main():
    report={"updated_at":dt.datetime.now(dt.timezone.utc).isoformat(),
        "status":"ARCHIVED_DEFENDER_MATCHUPS_UNAVAILABLE",
        "source":PARQUET_URL,
        "requested_season":"2025-26",
        "source_through":SOURCE_THROUGH,
        "live_model_unchanged":True}
    try:
        parquet_bytes=download()
        import io
        import pyarrow.parquet as pq
        table=pq.read_table(io.BytesIO(parquet_bytes))
        # Expose column names even when validation rejects an unfamiliar schema.
        report["source_columns"]=table.column_names
        report["original_rows"]=table.num_rows
        rows=convert_table(table)
        columns=table.column_names
        raw_count=table.num_rows
        SOURCE.parent.mkdir(parents=True,exist_ok=True)
        SOURCE.write_text(json.dumps({"season":"2025-26",
             "source_through":SOURCE_THROUGH,"source":"HUGGINGFACE_NBA_DATA_ARCHIVE_MATCHUPS",
             "rows":rows})+"\n")
        report.update(status="HISTORICAL_MATCHUPS_DOWNLOADED",
                      original_rows=raw_count,valid_pairs=len(rows),
                      source_columns=columns,source_kind="2025-26 regular-season parquet")
    except (OSError,ValueError,KeyError,TypeError,ImportError,AttributeError) as exc:
        report.update(error_type=type(exc).__name__,
                      error_detail=str(exc)[:260],
                      notice="Source not validated; no live defender projections or probability adjustments.")
    STATUS.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,sort_keys=True),flush=True)
    return report

if __name__=="__main__":main()
