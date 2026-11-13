"""Integrity gate for injury-triggered four-market forecasts.

Do not publish a forecast based on an older injury report if a newer,
verified official NBA report arrived while model training was running.
The watchdog compares the same timestamps before scheduling recovery.
"""
import argparse
import json
from datetime import datetime,timezone,timedelta

def ts(value):
    if not value:return None
    try:
        d=datetime.fromisoformat(str(value).replace("Z","+00:00"))
        if d.tzinfo is None or d.utcoffset() is None:return None
        return d.astimezone(timezone.utc)
    except (ValueError,TypeError):return None

def official_version(injuries):
    if injuries.get("status")!="OFFICIAL_NBA_REPORT_VERIFIED" or injuries.get("injury_data_verified") is not True:return None
    return ts(injuries.get("report_issued_at"))

def integrity(official,model,now=None):
    now=now or datetime.now(timezone.utc)
    if now.tzinfo is None:raise ValueError("now must be timezone aware")
    published=ts(model.get("generated_at"))
    used=ts(model.get("official_report_issued_at"))
    latest=official_version(official)
    if model.get("status")!="LIVE_ALL_MARKET_NEW_AI_UNCALIBRATED":
        return {"safe":False,"reason":"INVALID_MODEL_FEED"}
    if not published or published>now+timedelta(minutes=5):
        return {"safe":False,"reason":"MODEL_TIMESTAMP_INVALID"}
    if latest and latest<=now:
        if not used:return {"safe":False,"reason":"UNSTAMPED_MODEL_OFFICIAL_REPORT"}
        if used<latest:return {"safe":False,"reason":"NEWER_OFFICIAL_REPORT_NOT_MODELED"}
        if used>latest:return {"safe":False,"reason":"MODEL_REPORT_NEWER_THAN_PUBLISHED_OFFICIAL"}
    return {"safe":True,"reason":"CURRENT_OFFICIAL_INJURY_VERSION"}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--official",required=True)
    ap.add_argument("--model",required=True)
    ap.add_argument("--check",action="store_true")
    args=ap.parse_args()
    with open(args.official) as f:official=json.load(f)
    with open(args.model) as f:model=json.load(f)
    result=integrity(official,model)
    print(json.dumps(result),flush=True)
    if args.check and not result["safe"]:raise SystemExit(1)

if __name__=="__main__":main()
