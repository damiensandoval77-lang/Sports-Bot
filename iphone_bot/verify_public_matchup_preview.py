"""Real public iPhone-width acceptance test for opponent matchup estimates.

A merged PR or local JS test cannot prove deployed Pages or phone cache. This
checks visible DOM at the actual public URL, not GitHub source-only content.
"""
import json
from datetime import datetime,timezone
from pathlib import Path
from playwright.sync_api import sync_playwright

URL="https://damiensandoval77-lang.github.io/Sports-Bot/dames-picks/"
RELEASE="dp-matchup-calibration-20261111-r6"

def verify():
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=["--no-sandbox"])
        try:
            page=browser.new_page(viewport={"width":390,"height":844},
                                     device_scale_factor=3,is_mobile=True,
                                     has_touch=True)
            errs=[]
            page.on("pageerror",lambda e:errs.append(str(e)[:200]))
            page.goto(URL,wait_until="domcontentloaded",timeout=45000)
            page.wait_for_function("() => typeof state !== 'undefined' && !!state.updated && !state.loading",
                                   timeout=60000)
            result=page.evaluate("""() => {
              const previewRows=state.nba.filter(x=>x.matchupPreview);
              const upcoming=shown().filter(x=>x.matchupPreview);
              return {release:document.querySelector('meta[name="dames-release"]')?.content,
                nbaRows:state.nba.length,matchupPreviewRows:previewRows.length,
                visiblePreviewCards:upcoming.length,
                visibleResearchLabel:document.getElementById('cards')?.innerText?.includes('Matchup model')||false,
                firstPlayer:upcoming[0]?.player||null,firstMarket:upcoming[0]?.stat||null,
                firstRate:upcoming[0]?.matchupPreview?.rate||null,
                intactOriginalLine:upcoming[0]?.line??null,
                intactOriginalProjection:upcoming[0]?.projection??null,
                noCertifiedHitChance:upcoming.length?m.hitEstimate(upcoming[0])===null:null};
            }""")
            if result["visiblePreviewCards"]>0:
                page.locator("#cards [data-id]").filter(has_text="Matchup model").first.click()
                result["detailResearchLabel"]=page.locator("#detail-content").inner_text().find("Matchup model")>=0
                result["detailExplainsUncertainty"]="accuracy and probability calibration are being tracked prospectively" in page.locator("#detail-content").inner_text().lower()
                page.screenshot(path="public-matchup-preview-iphone-width.png")
            result["checked_at"]=datetime.now(timezone.utc).isoformat()
            result["browser_errors"]=errs
            result["site_url"]=URL
            result["status"]="READY" if (
                result["release"]==RELEASE and not errs and
                result["matchupPreviewRows"]>=1 and result["visiblePreviewCards"]>=1 and
                result["visibleResearchLabel"] and result.get("detailResearchLabel") and
                result.get("detailExplainsUncertainty") and
                result["noCertifiedHitChance"] is True
            ) else "BLOCKED"
            Path("public-matchup-preview-browser.json").write_text(json.dumps(result,indent=2)+"\n")
            print("PUBLIC_MATCHUP_PREVIEW",json.dumps(result))
            if result["status"]!="READY":
                raise SystemExit("Public iPhone-width page does not yet show verified research preview correctly")
        finally:
            browser.close()

if __name__=="__main__":verify()
