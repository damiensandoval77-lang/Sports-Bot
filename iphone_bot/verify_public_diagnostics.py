"""Check actual public iPhone-width board diagnostics visibility.

Public users should see cards immediately after Search, with no internal
capture/grade/source/build/debug text. An explicit ?diagnostics=1 query reveals
a collapsed developer disclosure. This opt-in is UI-only, not access control.
"""
import json
import time
from datetime import datetime,timezone
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE="https://damiensandoval77-lang.github.io/Sports-Bot/dames-picks/"
EXPECTED=json.loads((Path(__file__).resolve().parents[1]/"docs/dames-picks/release.json").read_text())["release_id"]
def audit():
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=["--no-sandbox"])
        try:
            page=browser.new_page(viewport={"width":390,"height":844},
                      device_scale_factor=3,is_mobile=True,has_touch=True)
            errors=[]
            page.on("pageerror",lambda e:errors.append(str(e)[:300]))
            # GitHub Pages may serve an older release briefly after the
            # push-triggered canary starts. Poll for the checked-out release HTML
            # instead of misclassifying deployment latency as UI regression.
            live_release=None
            for attempt in range(16):
                page.goto(BASE+"?verify-public="+str(time.time_ns()),
                          wait_until="domcontentloaded",timeout=45000)
                live_release=page.locator('meta[name="dames-release"]').get_attribute("content")
                if live_release==EXPECTED and page.locator("#diagnostics").count()==1:
                    break
                if attempt<15:time.sleep(5)
            if live_release!=EXPECTED:
                raise SystemExit("DEPLOYMENT_RELEASE_MISMATCH: hosted release="+str(live_release))
            page.wait_for_function("() => typeof state!=='undefined' && !state.loading && !!state.updated",timeout=60000)
            public=page.evaluate("""() => ({
              release:document.querySelector('meta[name="dames-release"]')?.content,
              diagnosticDisplay:getComputedStyle(document.querySelector('#diagnostics')).display,
              diagnosticVisible:!!document.querySelector('#diagnostics').getClientRects().length,
              statusVisible:!!document.querySelector('#status').getClientRects().length,
              verifyVisible:!!document.querySelector('#verify-app').getClientRects().length,
              cardsVisible:!!document.querySelector('#cards').getClientRects().length,
              cardsCount:document.querySelectorAll('#cards button[data-id]').length,
              healthTextVisible:(document.querySelector('#board')?.innerText||'').includes('provider standard markets withheld')
            })""")
            page.goto(BASE+"?diagnostics=1",wait_until="domcontentloaded",timeout=45000)
            page.wait_for_function("() => typeof state!=='undefined' && !state.loading && !!state.updated",timeout=60000)
            debug=page.evaluate("""() => ({
              diagnosticDisplay:getComputedStyle(document.querySelector('#diagnostics')).display,
              summaryVisible:!!document.querySelector('#diagnostics summary').getClientRects().length,
              open:document.querySelector('#diagnostics').open,
              verifyInitiallyVisible:!!document.querySelector('#verify-app').getClientRects().length
            })""")
            page.locator("#diagnostics summary").click()
            debug["verifyAfterOpen"]=page.locator("#verify-app").is_visible()
            debug["statusAfterOpen"]=page.locator("#status").is_visible()
            page.locator("#verify-app").click()
            page.wait_for_function("() => document.querySelector('#verify-result').textContent.includes('HTML and executing JS match') || document.querySelector('#verify-result').textContent.includes('OUTDATED APP') || document.querySelector('#verify-result').textContent.includes('Cannot verify')",timeout=30000)
            debug["releaseVerified"]=page.locator("#verify-result").inner_text().find("HTML and executing JS match")>=0
            checked_at=datetime.now(timezone.utc).isoformat()
            result={"checked_at":checked_at,"public":public,"diagnostics":debug,"errors":errors}
            result["status"]="READY" if (
                public["release"]==EXPECTED and
                public["diagnosticDisplay"]=="none" and
                not public["diagnosticVisible"] and
                not public["statusVisible"] and
                not public["verifyVisible"] and
                public["cardsVisible"] and
                public["cardsCount"]>0 and
                not public["healthTextVisible"] and
                debug["diagnosticDisplay"]!="none" and
                debug["summaryVisible"] and not debug["open"] and
                not debug["verifyInitiallyVisible"] and
                debug["verifyAfterOpen"] and debug["statusAfterOpen"] and
                debug["releaseVerified"] and not errors
            ) else "BLOCKED"
            Path("public-diagnostics-visibility.json").write_text(json.dumps(result,indent=2)+"\n")
            print("PUBLIC_DIAGNOSTICS_AUDIT",json.dumps(result))
            if result["status"]!="READY":
                raise SystemExit("Public diagnostic privacy/layout or owner query access not verified")
        finally:
            browser.close()
if __name__=="__main__":audit()
