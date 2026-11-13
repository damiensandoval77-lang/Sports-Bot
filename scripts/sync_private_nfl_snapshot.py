"""Safely mirror frozen NFL pregame snapshots from the owner's private repo.

Requires a fine-grained GitHub token with ONLY Contents:read access to
damiensandoval77-lang/Nfl-Bot. Token is GitHub Actions secret, NEVER written
to logs, files, Pages, or browser code. No token: fail visibly, keep old board.
"""
import base64
import csv
import io
import json
import os
import re
import tempfile
import urllib.request
from datetime import datetime,timezone
from pathlib import Path

SOURCE_REPO="damiensandoval77-lang/Nfl-Bot"
YEAR=2026
DEST=Path("docs/nfl/data")
REQUIRED={"captured_at","game_id","player_id","target","line",
          "projection_id","pick","model_pct"}
SAFE=re.compile(r"^latest_2026_\d{2}\.csv$")

def request_bytes(relative, token):
    url=f"https://api.github.com/repos/{SOURCE_REPO}/contents/docs/data/{relative}?ref=main"
    req=urllib.request.Request(url,headers={
        "Authorization":"Bearer "+token,
        "Accept":"application/vnd.github+json",
        "User-Agent":"DamesPicks-NFL-Private-Snapshot-Relay",
        "X-GitHub-Api-Version":"2022-11-28"})
    with urllib.request.urlopen(req,timeout=35) as response:
        data=json.load(response)
    encoded=data.get("content")
    if not encoded and data.get("sha"):
        # Fallback for GitHub contents API large-file encoding omissions.
        url=f"https://api.github.com/repos/{SOURCE_REPO}/git/blobs/{data['sha']}"
        req=urllib.request.Request(url,headers={
            "Authorization":"Bearer "+token,
            "Accept":"application/vnd.github+json",
            "User-Agent":"DamesPicks-NFL-Private-Snapshot-Relay"})
        with urllib.request.urlopen(req,timeout=35) as response:
            data=json.load(response)
        encoded=data.get("content")
    if not encoded or data.get("encoding")!="base64":
        raise ValueError(f"No readable file bytes from private NFL snapshot: {relative}")
    return base64.b64decode(encoded)

def timestamp(value):
    try:
        date=datetime.fromisoformat(value.replace("Z","+00:00"))
        return date.astimezone(timezone.utc) if date.tzinfo else None
    except (ValueError,TypeError,AttributeError):return None

def validate_payload(manifest,content):
    if manifest.get("season")!=YEAR:
        raise ValueError("Private NFL manifest has wrong season")
    files=manifest.get("files")
    if not isinstance(files,list) or not files or len(files)>40 or len(set(files))!=len(files):
        raise ValueError("Incomplete/duplicated NFL chunk manifest")
    if any(not SAFE.fullmatch(name) for name in files):
        raise ValueError("Unsafe file name in private manifest")
    capture=timestamp(manifest.get("captured_at"))
    if not capture:raise ValueError("Invalid private NFL snapshot capture timestamp")
    if set(files)!=set(content):raise ValueError("NFL snapshot chunk set incomplete")
    total=0
    game_ids=set()
    for name in files:
        try:
            text=content[name].decode("utf-8-sig")
        except (UnicodeError,AttributeError):
            raise ValueError("Non-UTF8 NFL line chunk")
        reader=csv.DictReader(io.StringIO(text))
        if not reader.fieldnames or not REQUIRED.issubset(reader.fieldnames):
            raise ValueError(f"Missing NFL frozen prop fields in {name}")
        rows=list(reader)
        if not rows:raise ValueError("Zero-row NFL chunk")
        if len(rows)>250:raise ValueError("NFL chunk exceeds 250-line limit")
        for row in rows:
            if row["captured_at"]!=manifest["captured_at"]:
                raise ValueError("Mixed timestamps in frozen NFL capture")
            if not all(row.get(k) for k in ("game_id","player_id","target","projection_id")):
                raise ValueError("Blank NFL frozen prediction identity")
            if row["pick"] not in ("More","Less"):
                raise ValueError("Invalid frozen betting side")
            try:
                line=float(row["line"]);model=float(row["model_pct"])
                if not (-1e9<line<1e9 and 0<=model<=100):
                    raise ValueError()
            except (ValueError,TypeError):
                raise ValueError("Invalid frozen line or confidence")
            game_ids.add(row["game_id"])
        total+=len(rows)
    if total!=manifest.get("rows") or total<5:
        raise ValueError(f"Incomplete private NFL capture: {total} vs {manifest.get('rows')}")
    if not game_ids:raise ValueError("No games represented by private odds snapshot")
    return total

def sync(fetch, dest=DEST):
    manifest=json.loads(fetch(f"latest_{YEAR}.json").decode("utf-8"))
    filenames=manifest.get("files",[])
    if not isinstance(filenames,list) or not filenames or len(filenames)>40:
        raise ValueError("Invalid manifest; not downloading anything")
    if any(not isinstance(x,str) or not SAFE.fullmatch(x) for x in filenames):
        raise ValueError("Unsafe chunk names")
    existing=Path(dest)/f"latest_{YEAR}.json"
    if existing.exists():
        try:
            local=json.loads(existing.read_text(encoding="utf-8"))
            old_time=timestamp(local.get("captured_at"))
            new_time=timestamp(manifest.get("captured_at"))
            if old_time and new_time and old_time>=new_time:
                # Check the actual existing CSVs too: a corrupt/incomplete
                # local transfer at the same timestamp must be repairable.
                local_files=local.get("files",[])
                complete=bool(local_files) and all(
                    isinstance(name,str) and SAFE.fullmatch(name) and
                    (Path(dest)/name).exists() for name in local_files)
                if complete:
                    try:
                        local_data={name:(Path(dest)/name).read_bytes() for name in local_files}
                        validate_payload(local,local_data)
                    except (OSError,ValueError,UnicodeError):
                        complete=False
                if complete:
                    print("Published NFL odds are already as recent as the private snapshot; no overwrite")
                    return {"changed":False,"rows":local.get("rows",0),"reason":"already_current"}
        except (OSError,ValueError,TypeError):
            pass
    blobs={name:fetch(name) for name in filenames}
    total=validate_payload(manifest,blobs)
    dest=Path(dest)
    dest.mkdir(parents=True,exist_ok=True)
    # Archive the currently published snapshot before replacing any chunks.
    # The post-sync reconciliation alone cannot recover a rotated source.
    if existing.exists() and (dest/"schedule_2026.json").exists():
        from reconcile_nfl_picks import run as archive_snapshot
        archive_snapshot(dest)
    with tempfile.TemporaryDirectory(prefix="private-nfl-sync-",dir=str(dest)) as folder:
        stage=Path(folder)
        for name,raw in blobs.items():
            (stage/name).write_bytes(raw)
        (stage/f"latest_{YEAR}.json").write_text(
            json.dumps(manifest,indent=2)+"\n",encoding="utf-8")
        for name in filenames:
            os.replace(stage/name,dest/name)
        # Write manifest last; the last good manifest remains intact on
        # download/validation failure.
        os.replace(stage/f"latest_{YEAR}.json",existing)
    print(f"Synced {total} validated, time-frozen NFL lines in {len(filenames)} chunks")
    return {"changed":True,"rows":total,"reason":"new_verified_snapshot"}

if __name__=="__main__":
    token=os.environ.get("NFL_PRIVATE_READ_TOKEN","")
    if not token:
        raise SystemExit("NFL_PRIVATE_READ_TOKEN secret not configured in Sports-Bot. Private-to-public sync is NOT running. Preserve existing data.")
    sync(lambda name:request_bytes(name,token))
