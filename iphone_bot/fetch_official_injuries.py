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
    """Identify exact roster names in published table rows, never inferred absences."""
    result={}
    for p in roster:
        name=str(p.get("player","")).strip()
        parts=name.split()
        if len(parts)<2:continue
        # NBA PDFs format names "Surname, Given". Check both single and
        # double-token surnames, including e.g. 'Jackson Jr., Jaren'.
        forms=[(parts[-1]," ".join(parts[:-1]))]
        if len(parts)>=3:forms.append((" ".join(parts[-2:])," ".join(parts[:-2])))
        statuses=set()
        for line in text.splitlines():
            if any(token in line.lower() for token in SKIP):continue
            for last,first in forms:
                expression=r"(?<!\w)"+re.escape(last)+r",\s*"+re.escape(first)+r"\s+(Out|Doubtful|Questionable|Probable|Available)\b"
                m=re.search(expression,line,re.I)
                if m:statuses.add(m.group(1).title())
        if statuses:
            ident=str(p["player_id"])
            result[ident]={"player":name,"player_id":ident,"team":p["team"],
                           "status":next(iter(statuses)) if len(statuses)==1 else "CONFLICTING_EXTRACT"}
    return list(result.values())

def read(url,timeout=12):
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 (compatible; Sports-Bot-Research/1.0)"})
    with urllib.request.urlopen(req,timeout=timeout) as response:
        return response.read()

def fallback_links(now):
    """Predict at most four recently published NBA static report filenames."""
    local=now.astimezone(ZoneInfo("America/New_York")).replace(second=0,microsecond=0)
    local=local.replace(minute=(local.minute//15)*15)
    out=[]
    for slot in range(4):
        issued=local-dt.timedelta(minutes=15*slot)
        suffix=issued.strftime("%I_%M%p").lstrip("0")
        filename="Injury-Report_"+issued.strftime("%Y-%m-%d")+"_"+suffix+".pdf"
        out.append((issued.astimezone(UTC),"https://"+HOST+"/referee/injury/"+filename))
    return out

def parse_espn_injuries(payload,roster):
    """Match ESPN league injury records by exact name and matching team."""
    indexed={(key(p.get("player")),str(p.get("team","")).upper()):p for p in roster}
    result={}
    groups=payload.get("injuries",[])
    if not isinstance(groups,list):return []
    for group in groups:
        if not isinstance(group,dict):continue
        team=group.get("team",{})
        abbr=str(team.get("abbreviation","")).upper() if isinstance(team,dict) else ""
        if len(abbr)!=3:continue
        for item in group.get("injuries",[]):
            if not isinstance(item,dict):continue
            athlete=item.get("athlete",{})
            name=athlete.get("displayName") if isinstance(athlete,dict) else ""
            p=indexed.get((key(name),abbr))
            if not p:continue
            status=str(item.get("status","")).upper().replace("-","_").replace(" ","_")
            if status not in ("OUT","DOUBTFUL","QUESTIONABLE","PROBABLE","DAY_TO_DAY"):continue
            ident=str(p["player_id"])
            if ident in result and result[ident]["status"]!=status:result[ident]["status"]="CONFLICTING_EXTRACT"
            else:result[ident]={"player":p["player"],"player_id":ident,
                                "team":abbr,"status":status,"provider":"ESPN_THIRD_PARTY"}
    return list(result.values())

def main():
    now=dt.datetime.now(UTC)
    base={"generated_at":now.isoformat(),"status":"UNAVAILABLE","injury_data_verified":False,
          "players":[],"source_page":PAGE,
          "notice":"No NBA status is inferred for an unlisted player; manual lineup verification is still required."}
    try:
        source="official_index"
        try:
            html=read(PAGE).decode("utf-8","replace")
            links=report_links(html,now)
        except (OSError,TimeoutError,ValueError):
            links=[]
        if not links:
            source="official_static_pdf_fallback"
            links=fallback_links(now)
        from pypdf import PdfReader
        pdf_bytes=None
        issued=None
        url=None
        last_error=None
        for timestamp,link in links[:4]:
            try:
                result=read(link,timeout=10)
                if not result.startswith(b"%PDF"):continue
                pdf_bytes=result
                issued,url=timestamp,link
                break
            except (OSError,TimeoutError,ValueError) as error:
                last_error=type(error).__name__
                continue
        if not pdf_bytes:
            raise RuntimeError("Official static PDF not accessible: "+str(last_error or "not found"))
        reader=PdfReader(io.BytesIO(pdf_bytes))
        raw="\n".join(page.extract_text(extraction_mode="layout") or "" for page in reader.pages)
        if not raw or "Injury Report:" not in raw:raise ValueError("Official injury PDF could not be extracted")
        roster=json.loads((ROOT/"docs/current_form.json").read_text()).get("players",[])
        players=parse_rows(raw,roster)
        if not players:raise ValueError("No roster status reliably identified in official PDF")
        base.update(status="OFFICIAL_NBA_REPORT_VERIFIED",injury_data_verified=True,
                    source_pdf=url,source_method=source,report_issued_at=issued.isoformat(),
                    extracted_statuses=len(players),players=players)
        print("Official NBA injury report:",url,"matched player statuses:",len(players),flush=True)
    except (OSError,ValueError,KeyError,ImportError,RuntimeError) as error:
        base["official_unavailable_reason"]=type(error).__name__
        print("Official NBA injury report unavailable:",type(error).__name__,flush=True)
        try:
            url="https://site.api.espn.com/apis/site/v2/sports/basketball/nba/injuries"
            response=json.loads(read(url,timeout=12))
            if not isinstance(response,dict) or not isinstance(response.get("injuries"),list):
                raise ValueError("Invalid ESPN injury response")
            roster=json.loads((ROOT/"docs/current_form.json").read_text()).get("players",[])
            observed=parse_espn_injuries(response,roster)
            if not observed:raise ValueError("No matching third-party injury data")
            base.update(status="THIRD_PARTY_ESPN_INJURY_CONTEXT",
                        injury_data_verified=False,players=observed,
                        report_issued_at=now.isoformat(),source_url=url,
                        extracted_statuses=len(observed),
                        notice="ESPN injury listing: NOT official NBA game-day confirmation. Recheck official report and starting lineup.")
            print("Third-party ESPN injury context:",len(observed),"players",flush=True)
        except (OSError,TimeoutError,ValueError,KeyError,TypeError) as fallback:
            base["failure_type"]=type(fallback).__name__
            print("Third-party injury backup unavailable:",type(fallback).__name__,flush=True)
    OUT.write_text(json.dumps(base,indent=2)+"\n")

if __name__=="__main__":main()
