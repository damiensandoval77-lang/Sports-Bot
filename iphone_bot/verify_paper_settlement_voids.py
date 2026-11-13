"""Fail-closed NBA immutable paper-market DNP-void provenance checks."""
import datetime as dt
from urllib.parse import urlparse
from zoneinfo import ZoneInfo
from iphone_bot.paper_pick_pipeline import strict_player_name
from iphone_bot.dnp_settlement import load_fixture

VALID_STATUSES={"SETTLED","PENDING","INVALID_LATE_CAPTURE","VOID_DNP"}

def verified_fixture_match(row,fixture):
    if fixture.get("status")!="MANUALLY_VERIFIED_DNP_FROM_PUBLISHED_TEAM_OR_NBA_REPORTS":
        return False
    try:
        tip=dt.datetime.fromisoformat(row["event_start"].replace("Z","+00:00"))
        captured=dt.datetime.fromisoformat(row["captured_at"].replace("Z","+00:00"))
        date=tip.astimezone(ZoneInfo("America/New_York")).date().isoformat()
    except (KeyError,AttributeError,ValueError,TypeError):
        return False
    if tip.tzinfo is None or captured.tzinfo is None or captured>=tip:
        return False
    matches=[e for e in fixture.get("records",[]) if
      str(e.get("date_eastern"))==date and e.get("game")==row.get("game")
      and e.get("team")==row.get("team") and
      str(e.get("player_id"))==str(row.get("player_id")) and
      strict_player_name(e.get("player"))==strict_player_name(row.get("player"))
      and e.get("source_url")==row.get("void_source_url")
      and e.get("reason")==row.get("void_reason")]
    return len(matches)==1

def verify(rows,report,fixture=None):
    statuses={}
    for row in rows:
        status=row.get("status","MISSING")
        statuses[status]=statuses.get(status,0)+1
        if status not in VALID_STATUSES:
            raise ValueError("UNKNOWN_FROZEN_STATUS: "+str(status))
        if status!="VOID_DNP":
            continue
        url=row.get("void_source_url","")
        parsed=urlparse(url)
        parts=parsed.path.strip("/").split("/")
        reasons=[]
        if row.get("result")!="VOID":reasons.append("not_void_result")
        if not str(row.get("void_reason") or "").strip():reasons.append("no_dnp_reason")
        if parsed.scheme!="https" or parsed.netloc!="www.nba.com":
            reasons.append("unexpected_url_origin")
        has_game_id=len(parts)>=2 and parts[0]=="game" and bool(parts[1])
        if not has_game_id:
            if fixture is None:
                fixture=load_fixture()
            if not verified_fixture_match(row,fixture):
                reasons.append("missing_game_id_and_no_exact_manual_fixture_match")
        if reasons:
            raise ValueError("NBA_DNP_VOID_MISSING_VERIFIED_FINAL_PROVENANCE: "+
                             ",".join(reasons)+
                             " url_path="+parsed.path[:80]+
                             " evidence_keys="+",".join(sorted(
                               k for k in row if k.startswith("void_"))))
        try:
            at=dt.datetime.fromisoformat(row["void_recorded_at"].replace("Z","+00:00"))
        except (KeyError,AttributeError,ValueError) as exc:
            raise ValueError("NBA_DNP_VOID_MISSING_RECORD_TIMESTAMP") from exc
        if at.tzinfo is None:
            raise ValueError("NBA_DNP_VOID_MISSING_RECORD_TIMESTAMP")
    expected=report.get("void_dnp")
    actual=statuses.get("VOID_DNP",0)
    if expected!=actual:
        raise ValueError("NBA_DNP_VOID_COUNT_MISMATCH: reported="+str(expected)+
                         " immutable="+str(actual))
    return statuses
