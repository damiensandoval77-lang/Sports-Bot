"""Fetch the official NBA's published injury-report PDF (not scraping private APIs).

Every status is anchored to an actual published PDF and team/player identity.
No status for an unlisted player is ever inferred: absence != available.
"""
import datetime as dt
import io
import json
import re
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"docs/injury_context.json"
PAGE="https://official.nba.com/nba-injury-report-2026-27-season/"
HOST="ak-static.cms.nba.com"
PDF_PATTERN=re.compile(r"Injury-Report_(\d{4}-\d{2}-\d{2})_(\d{1,2})_(\d{2})(AM|PM)\.pdf")
STATUS=re.compile(r"\b(Out|Doubtful|Questionable|Probable|Available)\b")
SKIP=("not yet submitted","report has not been submitted")
UTC=dt.timezone.utc

def key(value):
    s=unicodedata.normalize("NFKD",str(value or ""))
    return "".join(ch for ch in s.casefold() if ch.isalnum() and not unicodedata.combining(ch))

def report_links(html,now):
    """Only allow official PDF hostname and dated, current-season filenames."""
    candidates=[]
    for found in re.finditer(r"""(?:https?:)?(?://ak-static\.cms\.nba\.com)?/referee/injury/Injury-Report_\d{4}-\d{2}-\d{2}_\d{1,2}_\d{2}(?:AM|PM)\.pdf""",html,re.I):
        path=found.group(0)
        if path.startswith("//"):url="https:"+path
        elif path.startswith("http"):url=path
        else:url="https://"+HOST+path
        parsed=urllib.parse.urlparse(url)
        if parsed.hostname!=HOST or not parsed.path.startswith("/referee/injury/"):continue
        m=PDF_PATTERN.search(parsed.path)
        if not m:continue
        date=dt.date.fromisoformat(m.group(1))
        hour=int(m.group(2))%12+(12 if m.group(4).upper()=="PM" else 0)
        minute=int(m.group(3))
        try:issued=dt.datetime.combine(date,dt.time(hour,minute),ZoneInfo("America/New_York")).astimezone(UTC)
        except ValueError:continue
        if issued<=now and (now-issued).total_seconds()<48*3600:candidates.append((issued,url))
    return sorted(set(candidates),reverse=True)

def parse_rows(text,roster):
    """Match comma-formatted official names to roster with no guessed healthy statuses."""
    known={key(p["player"]):p for p in roster}
    result={}
    for line in text.splitlines():
        if any(token in line.lower() for token in SKIP):continue
        # The official table puts Last, First immediately before the designation;
        # extra leading game/team columns are allowed.
        pattern=r"([\w.'’\-]+(?:\s+[\w.'’\-]+){0,2}),\s*([\w.'’\-]+(?:\s+[\w.'’\-]+){0,2})\s+(Out|Doubtful|Questionable|Probable|Available)\b"
        for m in re.finditer(pattern,line,re.I):
            last,first,status=m.groups()
            p=known.get(key(first+" "+last))
            if not p:continue
            # Reject ambiguous contradictory statuses, never pick whichever
            # happened to appear first/last in a malformed extract.
            ident=str(p["player_id"])
            observation={"player":p["player"],"player_id":ident,
                         "team":p["team"],"status":status.title()}
            if ident in result and result[ident]["status"]!=observation["status"]:
                result[ident]["status"]="CONFLICTING_EXTRACT"
            else:result[ident]=observation
    return list(result.values())

def read(url):
    req=urllib.request.Request(url,headers={"User-Agent":"Sports-Bot/1.0 (+official public injury report)"})
    with urllib.request.urlopen(req,timeout=25) as response:
        return response.read()

def main():
    now=dt.datetime.now(UTC)
    base={"generated_at":now.isoformat(),"status":"UNAVAILABLE","injury_data_verified":False,
          "players":[],"source_page":PAGE,
          "notice":"No NBA status is inferred for an unlisted player; manual lineup verification is still required."}
    try:
        html=read(PAGE).decode("utf-8","replace")
        links=report_links(html,now)
        if not links:raise ValueError("No recent official PDF linked from NBA report page")
        issued,url=links[0]
        from pypdf import PdfReader
        reader=PdfReader(io.BytesIO(read(url)))
        text="\n".join(page.extract_text(extraction_mode="layout") or "" for page in reader.pages)
        if not text or "Injury Report:" not in text:raise ValueError("Official injury PDF could not be extracted")
        roster=json.loads((ROOT/"docs/current_form.json").read_text()).get("players",[])
        players=parse_rows(text,roster)
        if not players:raise ValueError("No roster status reliably identified in official PDF")
        base.update(status="OFFICIAL_NBA_REPORT_VERIFIED",injury_data_verified=True,
                    source_pdf=url,report_issued_at=issued.isoformat(),
                    extracted_statuses=len(players),players=players)
        print("Official NBA injury report:",url,"matched player statuses:",len(players),flush=True)
    except (OSError,ValueError,KeyError,ImportError,RuntimeError) as error:
        base["failure_type"]=type(error).__name__
        print("Official NBA injury report unavailable:",type(error).__name__,flush=True)
    OUT.write_text(json.dumps(base,indent=2)+"\n")

if __name__=="__main__":main()
