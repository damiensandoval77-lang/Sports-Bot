"""Read-only public GitHub Pages deployment canary.

Runs on an independent GitHub runner, never uses provider API credits, and
does not treat repository files or passing unit tests as proof of deployment.
"""
import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urljoin, urlparse

DEFAULT_SITE="https://damiensandoval77-lang.github.io/Sports-Bot/"
ROOT=Path(__file__).resolve().parents[1]
STATUS=ROOT/"docs/deployed_dashboard_probe.json"
UTC=dt.timezone.utc

def timestamp(value):
    try:
        value=dt.datetime.fromisoformat(str(value).replace("Z","+00:00"))
        return value.astimezone(UTC) if value.tzinfo else None
    except (ValueError,TypeError,OverflowError):
        return None

def fetch(url,timeout=15):
    request=urllib.request.Request(
        url,headers={"User-Agent":"SportsBot-Deployment-Canary/1.0",
                     "Accept":"text/html,application/json"})
    with urllib.request.urlopen(request,timeout=timeout) as response:
        # Public static files only; never retrieve sensitive endpoints.
        if response.status != 200:
            raise ValueError("Unexpected HTTP status "+str(response.status))
        payload=response.read(9_000_001)
        if len(payload)>9_000_000:
            raise ValueError("Public response exceeds 9 MB safety limit")
        return payload.decode("utf-8")

def evaluate(site,html,health,now=None):
    now=now or dt.datetime.now(UTC)
    failed=[]
    def check(ok,reason):
        if not ok:failed.append(reason)
    check('feeds.js?bundle=' in html,
          "DEPLOYED_HTML_MISSING_NEW_PRIZEPICKS_HANDOFF")
    check("m.nba(" in html,
          "DEPLOYED_HTML_MISSING_VERIFIED_CARD_CONVERTER")
    check('id="cards"' in html,"DEPLOYED_HTML_MISSING_AI_BOARD")
    check(isinstance(health,dict) and
          health.get("status")=="FRESH_RESEARCH_ONLY_PRIZEPICKS_AI_COMPARISONS",
          "PUBLIC_AI_JOIN_UNAVAILABLE")
    generated=timestamp(health.get("generated_at")) if isinstance(health,dict) else None
    provider=timestamp(health.get("provider_generated_at")) if isinstance(health,dict) else None
    check(generated is not None and 0<=(now-generated).total_seconds()<=90*60,
          "PUBLIC_COMPARISON_REPORT_STALE")
    check(provider is not None and 0<=(now-provider).total_seconds()<=90*60,
          "PUBLIC_PROVIDER_SNAPSHOT_STALE")
    check(isinstance(health.get("offers_matched"),int) and
          health.get("offers_matched",0)>0,"PUBLIC_COMPARISONS_MISSING")
    check(health.get("partial_provider_board") is not True and
          health.get("source_coverage_complete") is True,
          "PUBLIC_PROVIDER_BOARD_INCOMPLETE")
    return {"status":"READY" if not failed else "DEGRADED",
            "reasons":failed,"matched_offers":health.get("offers_matched"),
            "matched_by_game":health.get("matched_by_game"),
            "provider_partial":health.get("partial_provider_board"),
            "html_handoff_present":'feeds.js?bundle=' in html,
            "note":"Public HTML and JSON readiness, not a browser screenshot, wager or calibrated betting accuracy."}

def run(site,now=None,request=fetch):
    now=now or dt.datetime.now(UTC)
    if urlparse(site).scheme!="https" or not urlparse(site).hostname:
        raise ValueError("Only HTTPS public dashboard URL is permitted")
    base=site.rstrip("/")+"/"
    errors=[]
    try:
        html=request(urljoin(base,"dames-picks/"))
    except (OSError,ValueError,UnicodeError) as exc:
        html=""
        errors.append("PUBLIC_DASHBOARD_HTTP_FAILED:"+type(exc).__name__)
    try:
        health=json.loads(request(urljoin(base,"ai_prizepicks_quick_join_health.json")))
    except (OSError,ValueError,UnicodeError) as exc:
        health={}
        errors.append("PUBLIC_AI_RESEARCH_JSON_HTTP_FAILED:"+type(exc).__name__)
    report=evaluate(site,html,health,now)
    report["checked_at"]=now.isoformat()
    report["site_url"]=base
    report["reasons"]=sorted(set(errors+report["reasons"]))
    if report["reasons"]:report["status"]="DEGRADED"
    # Do not claim rendered cards: browser execution is a separate proof.
    report["browser_render_verified"]=False
    return report

def main():
    site=os.environ.get("SPORTS_BOT_PUBLIC_SITE_URL",DEFAULT_SITE)
    result=run(site)
    STATUS.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("PUBLIC DEPLOYMENT CHECK:",json.dumps(result,sort_keys=True))
    if result["status"]!="READY":
        sys.exit(1)

if __name__=="__main__":
    main()
