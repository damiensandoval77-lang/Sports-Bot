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
import urllib.error
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

TEAM_NAMES={
    "ATL":"Atlanta Hawks","BOS":"Boston Celtics","BKN":"Brooklyn Nets",
    "CHA":"Charlotte Hornets","CHI":"Chicago Bulls","CLE":"Cleveland Cavaliers",
    "DAL":"Dallas Mavericks","DEN":"Denver Nuggets","DET":"Detroit Pistons",
    "GSW":"Golden State Warriors","HOU":"Houston Rockets","IND":"Indiana Pacers",
    "LAC":"Los Angeles Clippers","LAL":"Los Angeles Lakers","MEM":"Memphis Grizzlies",
    "MIA":"Miami Heat","MIL":"Milwaukee Bucks","MIN":"Minnesota Timberwolves",
    "NOP":"New Orleans Pelicans","NYK":"New York Knicks","OKC":"Oklahoma City Thunder",
    "ORL":"Orlando Magic","PHI":"Philadelphia 76ers","PHX":"Phoenix Suns",
    "POR":"Portland Trail Blazers","SAC":"Sacramento Kings","SAS":"San Antonio Spurs",
    "TOR":"Toronto Raptors","UTA":"Utah Jazz","WAS":"Washington Wizards",
}
GAME_DATE_PATTERN=re.compile(r"\b(\d{2})/(\d{2})/(\d{4})\b")


def parse_rows(text,roster):
    """Parse NBA PDF regardless of pypdf's line/column layout.

    pypdf plain extraction often puts EVERY PDF word on a separate line;
    layout extraction can reverse the table's row order. Normalize whitespace,
    then process explicit game-date, team and player-status tokens IN ORDER.
    """
    normalized=" ".join(str(text).split())
    events=[]
    for match in GAME_DATE_PATTERN.finditer(normalized):
        month,day,year=map(int,match.groups())
        try:date=dt.date(year,month,day).isoformat()
        except ValueError:continue
        events.append((match.start(),0,"DATE",date))
    for abbr,full in TEAM_NAMES.items():
        for match in re.finditer(r"(?<!\w)"+re.escape(full)+r"(?!\w)",normalized,re.I):
            events.append((match.start(),1,"TEAM",abbr))
    for player in roster:
        team=str(player.get("team","")).upper()
        name=str(player.get("player","")).strip()
        if team not in TEAM_NAMES or len(name.split())<2:continue
        parts=name.split()
        forms=[(parts[-1]," ".join(parts[:-1]))]
        if len(parts)>=3:forms.append((" ".join(parts[-2:])," ".join(parts[:-2])))
        for last,first in forms:
            expression=(r"(?<!\w)"+re.escape(last)+r",\s*"+re.escape(first)
                        +r"\s+(Out|Doubtful|Questionable|Probable|Available)\b")
            for match in re.finditer(expression,normalized,re.I):
                events.append((match.start(),2,"PLAYER",(player,match.group(1).title())))
    # The official table repeats dates/teams only at the start of sections.
    # Preserve that context across PDF page headers and continuation rows.
    current_date=None
    current_team=None
    found={}
    for _,__,kind,value in sorted(events,key=lambda item:(item[0],item[1])):
        if kind=="DATE":
            current_date=value
            current_team=None
        elif kind=="TEAM":
            current_team=value
        elif kind=="PLAYER":
            player,status=value
            # A team/player mention without a preceding official game date
            # cannot be represented as a verified game-specific status.
            if current_date is None or current_team is None:continue
            if str(player.get("team","")).upper()!=current_team:continue
            ident=str(player["player_id"])
            k=(ident,current_date)
            previous=found.get(k)
            if previous and previous["status"]!=status:
                status="CONFLICTING_EXTRACT"
            found[k]={"player":player["player"],"player_id":ident,
                      "team":current_team,"game_date":current_date,
                      "status":status}
    return list(found.values())

def read(url,timeout=12):
    """Request public NBA documents with ordinary browser headers.

    Keep requests bounded; upstream 403/429 responses must never be treated as
    valid official injury data or bypassed through undocumented APIs.
    """
    req=urllib.request.Request(url,headers={
        "User-Agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36",
        "Accept":"application/pdf,text/html;q=0.9,*/*;q=0.8",
        "Accept-Language":"en-US,en;q=0.9",
    })
    with urllib.request.urlopen(req,timeout=timeout) as response:
        return response.read()


def failure_label(error):
    if isinstance(error,urllib.error.HTTPError):
        return "HTTP_"+str(error.code)
    if isinstance(error,urllib.error.URLError):
        return "URL_ERROR"
    return type(error).__name__

def fallback_links(now):
    """Bounded official static URL candidates when the injury index is blocked.

    The NBA publishes multiple quarter-hour updates. Check recent slots first,
    followed by older hourly slots to survive delayed publication.
    """
    local=now.astimezone(ZoneInfo("America/New_York")).replace(second=0,microsecond=0)
    local=local.replace(minute=(local.minute//15)*15)
    slots=(0,1,2,3,4,6,8,12,16,24,32,48)
    out=[]
    for slot in slots:
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
        diagnostics={"index":"NOT_ATTEMPTED","pdf_attempts":0,"pdf_http_errors":{}}
        try:
            html=read(PAGE).decode("utf-8","replace")
            links=report_links(html,now)
            diagnostics["index"]="OK_"+str(len(links))+"_LINKS"
        except (OSError,TimeoutError,ValueError) as error:
            links=[]
            diagnostics["index"]=failure_label(error)
        if not links:
            source="official_static_pdf_fallback"
        # Use dated URLs explicitly published by the NBA first.
        # Static filenames are merely candidate URLs, never proof of a report.
        links=links[:5]+fallback_links(now)
        links=list(dict((url,(timestamp,url)) for timestamp,url in links).values())
        base["retrieval_diagnostics"]=diagnostics
        from pypdf import PdfReader
        pdf_bytes=None
        issued=None
        url=None
        last_error=None
        for timestamp,link in links[:12]:
            diagnostics["pdf_attempts"]+=1
            try:
                result=read(link,timeout=7)
                if not result.startswith(b"%PDF"):
                    diagnostics["pdf_http_errors"]["NON_PDF_RESPONSE"]=diagnostics["pdf_http_errors"].get("NON_PDF_RESPONSE",0)+1
                    continue
                pdf_bytes=result
                issued,url=timestamp,link
                break
            except (OSError,TimeoutError,ValueError) as error:
                last_error=failure_label(error)
                diagnostics["pdf_http_errors"][last_error]=diagnostics["pdf_http_errors"].get(last_error,0)+1
                # Do not spend the whole CI budget retrying the same forbidden host.
                if last_error in ("HTTP_401","HTTP_403","HTTP_429"):
                    break
                continue
        if not pdf_bytes:
            raise RuntimeError("Official static PDF not accessible: "+str(last_error or "not found"))
        reader=PdfReader(io.BytesIO(pdf_bytes))
        # pypdf layout mode and normal mode arrange PDF table columns
        # differently. Accept only verified team+player matches, but try both.
        roster=json.loads((ROOT/"docs/current_form.json").read_text()).get("players",[])
        players=[]
        parse_diagnostics=[]
        for mode in ("layout","plain"):
            try:
                raw="\n".join(
                    (page.extract_text(extraction_mode="layout") if mode=="layout"
                     else page.extract_text()) or ""
                    for page in reader.pages)
                found=[p for p in parse_rows(raw,roster) if p.get("game_date")]
                parse_diagnostics.append({"mode":mode,"characters":len(raw),
                                          "matches":len(found),
                                          "has_report_header":"Injury Report:" in raw,
                                          "has_game_date":bool(GAME_DATE_PATTERN.search(raw)),
                                          "official_text_sample":raw[:1100].replace("\\r"," ")})
                if len(found)>len(players):players=found
            except (ValueError,TypeError) as extraction_error:
                parse_diagnostics.append({"mode":mode,"failure":type(extraction_error).__name__})
        diagnostics["pdf_parse"]=parse_diagnostics
        if not players:raise ValueError("No team-matched roster statuses extracted from official PDF")
        base.update(status="OFFICIAL_NBA_REPORT_VERIFIED",injury_data_verified=True,
                    source_pdf=url,source_method=source,report_issued_at=issued.isoformat(),
                    extracted_statuses=len(players),players=players)
        print("Official NBA injury report:",url,"matched player statuses:",len(players),flush=True)
    except (OSError,ValueError,KeyError,ImportError,RuntimeError) as error:
        base["official_unavailable_reason"]=type(error).__name__
        print("Official NBA injury report unavailable:",type(error).__name__,
              "details:",json.dumps(base.get("retrieval_diagnostics",{}),sort_keys=True),flush=True)
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
            base["failure_type"]=failure_label(fallback)
            print("Third-party injury backup unavailable:",type(fallback).__name__,flush=True)
    OUT.write_text(json.dumps(base,indent=2)+"\n")

if __name__=="__main__":main()
