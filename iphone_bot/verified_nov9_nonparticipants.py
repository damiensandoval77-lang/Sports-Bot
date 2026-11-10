"""Source-linked Nov 9 nonparticipant evidence against immutable verified finals.

A source-linked report is not sufficient by itself: at least three independently
verified played player rows for each side must prove the exact final game and
the alleged nonparticipant must have no contradictory played player row.
"""
import json
from pathlib import Path
from urllib.parse import urlparse
from iphone_bot.fetch_final_boxscores import verified_dnp_player
from iphone_bot.paper_pick_pipeline import strict_player_name

ROOT=Path(__file__).resolve().parents[1]
FIXTURE=ROOT/"docs/confirmed_nonparticipants_2026-11-09.json"
SOURCE="VERIFIED_FINAL_BOXSCORE_DNP_CROSSCHECKED"
VALID={"NBA_CDN_FINAL","ESPN_FINAL"}
OFFICIAL_KINDS={"OFFICIAL_BOX_INACTIVE","OFFICIAL_POSTGAME_RECAP_CONFIRMED_ABSENCE",
                "OFFICIAL_GAME_DAY_OUT","OFFICIAL_PLAYER_REPORT_OUT"}
OTHER_KINDS={"FINAL_BOXSCORE_INACTIVE","FINAL_GAME_AP_RECAP_CONFIRMED_ABSENCE",
             "FINAL_BOXSCORE_INACTIVE_OR_DNP","FINAL_GAME_REPORT_CONFIRMED_ABSENCE",
             "FINAL_GAME_INJURY_OUT"}
HOSTS={"www.nba.com","www.basketball-reference.com","www.cbssports.com",
       "www.silverscreenandroll.com","www.si.com","arizonasports.com"}
IDS={"0022600203","0022600204","0022600205","0022600206","0022600207",
     "0022600208","0022600209","0022600210"}

def nonparticipants(final_rows,fixture):
    if fixture.get("status")!="CROSSCHECKED_NOV9_NONPARTICIPANTS" or fixture.get("date_eastern")!="2026-11-09":
        raise ValueError("Invalid historical nonparticipant fixture")
    by_id={}
    for row in final_rows:
        gid=str(row.get("source_game_id") or "")
        if (gid not in IDS or row.get("date")!="2026-11-09" or
            row.get("source") not in VALID or row.get("final_confirmed") is not True or
            row.get("dnp_final_verified") is True):continue
        by_id.setdefault(gid,[]).append(row)
    result=[]
    seen=set()
    for g in fixture.get("groups",[]):
        gid=str(g.get("game_id") or "")
        away,home=g.get("away"),g.get("home")
        url=g.get("url","")
        kind=g.get("kind")
        if (gid not in IDS or kind not in OFFICIAL_KINDS|OTHER_KINDS or
            urlparse(url).scheme!="https" or urlparse(url).hostname not in HOSTS or
            (kind in OFFICIAL_KINDS and urlparse(url).hostname!="www.nba.com")):
            raise ValueError("Invalid nonparticipant source")
        if kind in ("OFFICIAL_BOX_INACTIVE","FINAL_BOXSCORE_INACTIVE","FINAL_BOXSCORE_INACTIVE_OR_DNP") and gid not in url and "basketball-reference" not in url:
            raise ValueError("Boxscore game ID mismatch")
        matched=[x for x in by_id.get(gid,[]) if
                 (x.get("team"),x.get("opponent")) in ((away,home),(home,away))]
        if min(sum(x.get("team")==t for x in matched) for t in (away,home))<3:
            continue
        for item in g.get("players",[]):
            name,team=item.get("player"),item.get("team")
            if team not in (away,home) or not strict_player_name(name) or not item.get("reason"):
                raise ValueError("Invalid player provenance")
            ident=(gid,team,strict_player_name(name))
            if ident in seen:raise ValueError("Duplicate source confirmed player")
            seen.add(ident)
            if any(x.get("team")==team and strict_player_name(x.get("player"))==ident[2] for x in matched):
                # Any verified played row defeats the absence claim.
                continue
            opponent=home if team==away else away
            row=verified_dnp_player(name,team,opponent,"2026-11-09",item["reason"],
                   "NBA_OFFICIAL_INACTIVE_CROSSCHECKED" if kind in OFFICIAL_KINDS else SOURCE,gid)
            if row:
                row["crosscheck_source_url"]=url
                row["crosscheck_kind"]=kind
                result.append(row)
    return result

def load_nonparticipants(final_rows,path=FIXTURE):
    try:return nonparticipants(final_rows,json.loads(Path(path).read_text()))
    except OSError:return []
