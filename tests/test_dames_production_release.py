#!/usr/bin/env python3
"""Public Pages smoke against the ACTUAL deployed URL, no paid API polling."""
import os,time
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
URL=os.getenv("DAME_SITE_URL","https://damiensandoval77-lang.github.io/Sports-Bot/dames-picks/")
OUTPUT=Path("test-artifacts");OUTPUT.mkdir(exist_ok=True)
EXPECTED="dp-concept3-unified-20261117-r1"
def main():
 with sync_playwright() as pw:
  for bt in (pw.chromium,pw.webkit):
   browser=bt.launch(headless=True)
   for width in (393,1448):
    page=browser.new_page(viewport={"width":width,"height":900},device_scale_factor=1)
    errors=[]
    page.on("pageerror",lambda e:errors.append(str(e)))
    page.add_init_script("window.DAMES_DISABLE_EXTERNAL_PHOTOS=true;window.DAMES_DISABLE_DIRECT_SCORES=true")
    page.goto(URL+"?release_smoke="+EXPECTED,wait_until="domcontentloaded",timeout=45000)
    release=page.locator('meta[name="dames-release"]').get_attribute("content")
    assert release==EXPECTED,(release,EXPECTED)
    expect(page.locator(".unified-tab")).to_have_count(6,timeout=20000)
    expect(page.locator(".panel")).to_have_count(10,timeout=20000)
    for _ in range(150):
     banner=page.locator(".connected-banner").inner_text()
     if banner.startswith("NBA connected"):break
     if banner.startswith("Connected view failed"):raise AssertionError(banner)
     time.sleep(.1)
    else:raise AssertionError("Public NBA feed not connected: "+banner)
    assert page.locator(".hero h1").inner_text().strip()!="Connecting player data"
    page.screenshot(path=str(OUTPUT/f"dames-LIVE-{bt.name}-{width}.png"),full_page=True)
    page.locator('[data-workspace="board"]').click()
    expect(page.locator("#unified-workspace")).to_be_visible(timeout=20000)
    expect(page.frame_locator("#unified-frame").locator('[data-view="board"]')).to_have_class("active",timeout=30000)
    page.locator('[data-workspace="saved"]').click()
    expect(page.frame_locator("#unified-frame").locator('[data-view="saved"]')).to_have_class("active",timeout=15000)
    page.locator('[data-workspace="tennis"]').click()
    expect(page.frame_locator("#unified-frame").locator('[data-league="TENNIS"]')).to_have_class("active",timeout=15000)
    page.locator('[data-workspace="player"]').click()
    expect(page.locator(".wrap")).to_be_visible(timeout=10000)
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"),"Horizontal overflow on public site"
    assert not errors,errors
    print(f"PASS DEPLOYED {bt.name} {width}px: release marker, real data, Board, Saved, Tennis, Concept #3",flush=True)
    page.close()
   browser.close()
if __name__=="__main__":main()
