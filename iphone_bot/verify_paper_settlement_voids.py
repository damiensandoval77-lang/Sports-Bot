"""Fail-closed NBA immutable paper-market DNP-void provenance checks."""
import datetime as dt
from urllib.parse import urlparse

VALID_STATUSES={"SETTLED","PENDING","INVALID_LATE_CAPTURE","VOID_DNP"}

def verify(rows,report):
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
        if (row.get("result")!="VOID" or not str(row.get("void_reason") or "").strip()
            or parsed.scheme!="https" or parsed.netloc!="www.nba.com"
            or len(parts)<2 or parts[0]!="game" or not parts[1]):
            raise ValueError("NBA_DNP_VOID_MISSING_VERIFIED_FINAL_PROVENANCE")
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
