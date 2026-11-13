"""Real public iPhone-width acceptance test for opponent matchup estimates.

A merged PR or local JS test cannot prove deployed Pages or phone cache. This
checks visible DOM at the actual public URL, not GitHub source-only content.
"""
import json
from datetime import datetime,timezone
from pathlib import Path
from playwright.sync_api import sync_playwright

URL="https://damiensandoval77-lang.github.io/Sports-Bot/dames-picks/"
RELEASE=json.loads((Path(__file__).resolve().parents[1]/"docs/dames-picks/release.json").read_text())["release_id"]

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
            # Explicitly switch to NBA Board through the same touch controls
            # the phone user uses; another tab can persist across refreshes.
            page.locator('[data-league="NBA"]').click()
            page.locator('[data-view="board"]').click()
            page.wait_for_function("() => !state.loading && !state.league.includes('NFL')",timeout=15000)
            result=page.evaluate("""() => {
              const previewRows=state.nba.filter(x=>x.matchupPreview);
              const upcoming=shown().filter(x=>x.matchupPreview);
              return {release:document.querySelector('meta[name="dames-release"]')?.content,
                nbaRows:state.nba.length,matchupPreviewRows:previewRows.length,
                visiblePreviewCards:upcoming.length,
                noRedundantCardLabel:!document.getElementById('cards')?.innerText?.includes('Matchup model'),
                firstPlayer:upcoming[0]?.player||null,firstMarket:upcoming[0]?.stat||null,
                firstRate:upcoming[0]?.matchupPreview?.rate||null,
                intactOriginalLine:upcoming[0]?.line??null,
                intactOriginalProjection:upcoming[0]?.projection??null,
                noCertifiedHitChance:upcoming.length?m.hitEstimate(upcoming[0])===null:null};
            }""")
            if result["visiblePreviewCards"]>0:
                # Capture DOM state before touching a card so stale or
                # non-rendered snapshots fail with useful evidence.
                result["renderedCardCount"]=page.locator("#cards button[data-id]").count()
                result["renderedCardExcerpt"]=page.locator("#cards").inner_text()[:400]
                page.evaluate("""() => {
                  const picked=shown().find(x=>x.matchupPreview);
                  if(!picked)throw Error('NO_MATCHUP_PREVIEW_ROW');
                  const id=m.key(picked);
                  const card=[...document.querySelectorAll('#cards button[data-id]')]
                    .find(button=>button.dataset.id===id);
                  if(!card)throw Error('MODEL_PREVIEW_NOT_VISIBLE_ON_CARD');
                  if(card.innerText.includes('Matchup model'))
                    throw Error('REDUNDANT_MATCHUP_LABEL_STILL_VISIBLE');
                  if(!card.innerText.includes('Hit est.'))
                    throw Error('HIT_ESTIMATE_MISSING');
                  card.click();
                }""")
                result["noRedundantDetailLabel"]=page.locator("#detail-content").inner_text().find("Matchup model")<0
                result["detailExplainsUncertainty"]="accuracy and probability calibration are being tracked prospectively" in page.locator("#detail-content").inner_text().lower()
                page.screenshot(path="public-matchup-preview-iphone-width.png")
            result["checked_at"]=datetime.now(timezone.utc).isoformat()
            result["browser_errors"]=errs
            result["site_url"]=URL
            result["status"]="READY" if (
                result["release"]==RELEASE and not errs and
                result["matchupPreviewRows"]>=1 and result["visiblePreviewCards"]>=1 and
                result["noRedundantCardLabel"] and result.get("noRedundantDetailLabel") and
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
