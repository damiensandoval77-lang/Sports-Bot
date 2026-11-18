#!/usr/bin/env python3
"""Browser-test the actual Cloudflare staging site; no paid provider requests."""
import os
import time
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
BASE=os.environ.get("DAMES_CF_STAGE_URL","https://dames-picks-staging.damiensandoval77.workers.dev").rstrip("/")
URL=BASE+"/dames-picks/"
out=Path("test-artifacts")
out.mkdir(exist_ok=True)
def main():
 with sync_playwright() as pw:
  for browser_type in (pw.chromium,pw.webkit):
   browser=browser_type.launch(headless=True)
   for width in (393,1448):
    page=browser.new_page(viewport={"width":width,"height":940},device_scale_factor=1)
    errors=[]
    page.on("pageerror",lambda error:errors.append(str(error)))
    page.add_init_script("window.DAMES_DISABLE_EXTERNAL_PHOTOS=true;window.DAMES_DISABLE_DIRECT_SCORES=true")
    page.goto(URL+"?qa=cloudflare-live",wait_until="domcontentloaded",timeout=45000)
    expect(page.locator(".unified-tab")).to_have_count(6,timeout=30000)
    expect(page.locator(".panel")).to_have_count(10,timeout=30000)
    assert page.locator("#cloudflare-staging-banner").is_visible(),"Missing truthful staging banner"
    for i in range(200):
     t=page.locator(".connected-banner").inner_text()
     if t.startswith("NBA connected"):break
     if t.startswith("Connected view failed"):raise AssertionError(t)
     time.sleep(.1)
    else:raise AssertionError("Data UI not connected: "+page.locator(".connected-banner").inner_text())
    assert page.locator(".hero h1").inner_text().strip() not in ["","Connecting player data"]
    assert page.locator(".bar").count()>0,"No real player game logs"
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"),"Horizontal page overflow"
    page.screenshot(path=str(out/f"dames-CF-LIVE-{browser_type.name}-{width}.png"),full_page=True)
    page.locator('[data-workspace="board"]').click()
    expect(page.locator("#unified-workspace")).to_be_visible(timeout=10000)
    old=page.frame_locator("#unified-frame")
    expect(old.locator('[data-view="board"]')).to_have_class("active",timeout=30000)
    page.locator('[data-workspace="saved"]').click()
    expect(old.locator('[data-view="saved"]')).to_have_class("active",timeout=15000)
    page.locator('[data-workspace="tennis"]').click()
    expect(old.locator('[data-league="TENNIS"]')).to_have_class("active",timeout=15000)
    page.locator('[data-workspace="player"]').click()
    expect(page.locator(".wrap")).to_be_visible(timeout=10000)
    assert not errors,errors[:4]
    print(f"PASS LIVE Cloudflare {browser_type.name} {width}px: design, real stats, Board/Saved/Tennis, no horizontal overflow or JS errors",flush=True)
    page.close()
   browser.close()
if __name__=="__main__":main()
