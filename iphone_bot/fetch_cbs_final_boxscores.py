"""Optional postgame CBS HTML fallback for blocked NBA/ESPN APIs.

Read-only with respect to immutable pregame picks. No game is settled from a
live score, standings page, or cached projection. Require a final-status page,
exact date/matchup URL, a player box-score table with PTS/REB/AST/MIN,
and unique full-roster player identity derived from the SAVED pregame slate.
If HTML structure changes, produce diagnostics and do not infer any stats.
"""
import json
import re
import unicodedata
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime,timezone
from pathlib import Path

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup=None

try:
    from .fetch_final_boxscores import pending_games,team
    from .paper_pick_pipeline import TEAM_ABBREVIATIONS
except ImportError:
    from fetch_final_boxscores import pending_games,team
    from paper_pick_pipeline import TEAM_ABBREVIATIONS

ROOT=Path(__file__).resolve().parents[1]
LEDGER=ROOT/"docs/paper_pick_ledger.json"
OUTPUT=ROOT/"data/nba/current/cbs_final_boxscores.json"
STATUS=ROOT/"docs/cbs_final_boxscores_status.json"
ROOT_URL="https://www.cbssports.com/nba/gametracker/boxscore/"
# CBS uses shorter game URL codes than standard NBA tricode identifiers.
CBS_URL_TEAMS={"NYK":"NY","GSW":"GS"}

def cbs_boxscore_url(date,away,home,view="boxscore"):
    if view not in ("boxscore","live"):raise ValueError("Unsupported CBS game view")
    a=CBS_URL_TEAMS.get(away,away)
    h=CBS_URL_TEAMS.get(home,home)
    return f"https://www.cbssports.com/nba/gametracker/{view}/NBA_{date.replace('-','')}_{a}%40{h}/"


def keyname(s):
    ascii_name=unicodedata.normalize("NFKD",str(s or "")).casefold()
    return re.sub(r"[^a-z0-9]","", "".join(c for c in ascii_name
            if not unicodedata.combining(c)))

def shortname(s):
    """Conservative first-initial + full surname identity, not substring."""
    parts=str(s or "").replace("."," ").strip().split()
    if len(parts)<2:return None
    return (keyname(parts[0])[:1],keyname("".join(parts[1:])))

def fetch_html(url,timeout=13):
    headers={"User-Agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
             "(KHTML, like Gecko) Chrome/131.0 Safari/537.36",
             "Accept":"text/html,application/xhtml+xml",
             "Accept-Language":"en-US,en;q=0.9"}
    with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=timeout) as response:
        content=response.read(3_000_000)
    return content.decode("utf-8","replace")

def parse_final(html,date,away,home,records):
    if BeautifulSoup is None:raise RuntimeError("beautifulsoup4 not installed")
    soup=BeautifulSoup(html,"html.parser")
    for dead in soup(["script","style","noscript"]):dead.decompose()
    # No final claim from page title alone. Require literal terminal game status.
    text=soup.get_text(" ",strip=True)
    # "FINAL" elsewhere on the site (recaps, sidebars) must not cause
    # an in-progress matchup to be graded. It must appear between the
    # away/home scorestrip identities, as CBS formats its game header.
    header_away=CBS_URL_TEAMS.get(away,away)
    header_home=CBS_URL_TEAMS.get(home,home)
    result_pattern=(r"\b"+re.escape(header_away)+r"\b.{0,200}\bFINAL\b.{0,200}\b"+
                    re.escape(header_home)+r"\b")
    if not re.search(result_pattern,text,re.I):return []
    # CBS includes both full team names near game box score and date.
    names={abbr:full for full,abbr in TEAM_ABBREVIATIONS.items()}
    if (away not in names or home not in names or
        names[away].split()[-1].lower() not in text.lower() or
        names[home].split()[-1].lower() not in text.lower()):
        return []
    # Resolve by roster identity of the exact pregame game, not by fuzzy name.
    roster=defaultdict(list)
    for row in records:
        if row.get("status")!="PENDING":continue
        if row.get("team") not in (away,home):continue
        if row.get("game")!=f"{names[away]} @ {names[home]}":continue
        try:
            game_date=datetime.fromisoformat(str(row["event_start"]).replace("Z","+00:00")).astimezone(
                __import__("zoneinfo").ZoneInfo("America/New_York")).date().isoformat()
        except (TypeError,ValueError):continue
        if game_date!=date:continue
        identity=shortname(row.get("player"))
        if identity:
            r=(str(row["player"]),str(row["team"]))
            if r not in roster[identity]:roster[identity].append(r)
    found={}
    for table in soup.select("table"):
        trs=table.select("tr")
        header=None
        for tr in trs:
            cells=tr.find_all(["th","td"],recursive=False)
            if not cells:continue
            vals=[c.get_text(" ",strip=True) for c in cells]
            norms=[re.sub(r"[^A-Z0-9]","",v.upper()) for v in vals]
            if all(n in norms for n in ("PTS","REB","AST","MIN")):
                header={n:norms.index(n) for n in ("PTS","REB","AST","MIN")}
                continue
            if header is None:continue
            try:
                # Match only a unique first initial/full surname from the
                # pregame roster. Ambiguous aliases must be excluded.
                name=vals[0]
                sig=shortname(name)
                candidates=roster.get(sig,[])
                if len(candidates)!=1:continue
                player,tcode=candidates[0]
                from .fetch_final_boxscores import box_player
            except ImportError:
                from fetch_final_boxscores import box_player
            except (ValueError,IndexError,KeyError,TypeError):continue
            try:
                stats={name:vals[i] for name,i in header.items()}
                # DNP/OUT '-' is never interpreted as 0.
                entry=box_player(player,tcode,home if tcode==away else away,
                   date,stats["PTS"],stats["REB"],stats["AST"],stats["MIN"],
                   "CBS_SPORTS_LIVE_FINAL",f"CBS_{date.replace('-','')}_{away}_{home}")
                if not entry:continue
                k=(player,tcode)
                if k in found and found[k]!=entry:
                    found[k]=None # Ambiguous or changing player stats: no grade
                elif k not in found:
                    found[k]=entry
            except (ValueError,IndexError,KeyError,TypeError):continue
    # Require genuinely populated player boxscore tables on BOTH teams.
    valid=[r for r in found.values() if r]
    if (sum(r["team"]==away for r in valid)<3 or
        sum(r["team"]==home for r in valid)<3):
        return []
    return valid

def collect(records,now=None,request=fetch_html):
    pending=pending_games(records,now)
    report={"source":"CBS Sports terminal box-score HTML fallback",
        "eligible_matchups":len(pending),"finished_matchups":0,
        "matched_player_lines":0,"failures":[]}
    results=[]
    for date,away,home in sorted(pending):
        # The CBS /boxscore page sometimes retains an early-quarter snapshot
        # after the separate /live game page has reached FINAL.
        # Both routes must independently pass parse_final's terminal-status
        # and multi-player identity checks; never trust cached live scores.
        for view in ("boxscore","live"):
            url=cbs_boxscore_url(date,away,home,view=view)
            try:
                parsed=parse_final(request(url),date,away,home,records)
                if not parsed:continue
                results.extend(parsed)
                report["finished_matchups"]+=1
                break
            except (ValueError,TypeError,OSError,RuntimeError,TimeoutError) as exc:
                report["failures"].append(f"{date} {away}@{home} {view}: {str(exc)[:150]}")
    report["matched_player_lines"]=len(results)
    report["status"]="VERIFIED_FINAL_CBS_MATCHUPS" if results else "NO_VERIFIED_FINAL_CBS_MATCHUPS"
    return results,report

def main():
    records=json.loads(LEDGER.read_text()).get("records",[]) if LEDGER.exists() else []
    players,report=collect(records)
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    OUTPUT.write_text(json.dumps(players,indent=2)+"\n")
    report["updated_at"]=datetime.now(timezone.utc).isoformat()
    STATUS.write_text(json.dumps(report,indent=2)+"\n")
    print("CBS FINAL BOXSCORES:",json.dumps(report,sort_keys=True),flush=True)

if __name__=="__main__":main()
