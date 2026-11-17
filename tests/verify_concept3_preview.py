#!/usr/bin/env python3
"""Repeatable checks for isolated Concept #3 page; browser needed.
Run: python tests/verify_concept3_preview.py [--browser /usr/bin/chromium]
"""
import argparse
from pathlib import Path
from playwright.sync_api import sync_playwright

parser=argparse.ArgumentParser()
parser.add_argument('--browser',default='/usr/bin/chromium')
args=parser.parse_args()
html=(Path(__file__).resolve().parents[1] / 'docs/dames-picks/concept-3-preview.html').read_text(encoding='utf-8')
with sync_playwright() as pw:
    browser=pw.chromium.launch(executable_path=args.browser,headless=True,args=['--no-sandbox'])
    for width in (320,393,768,1448):
        page=browser.new_page(viewport={'width':width,'height':900},device_scale_factor=1)
        errors=[]
        requests=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.on('request',lambda r:requests.append(r.url))
        page.set_content(html,wait_until='load')
        assert page.title()=="Dame's Picks | Player Intelligence"
        assert page.locator('.panel').count()==10
        assert page.locator('.bar').count()==10
        assert page.locator('.greenring').count()==1
        assert page.locator('.hist .bin').count()==12
        assert page.locator('.hero .portrait img').count()==1
        assert page.evaluate('document.documentElement.scrollWidth')<=width
        page.locator('select#stat').select_option('rebounds')
        assert page.locator('#model-proj').inner_text()=='8.8'
        page.locator('[data-action="compare"]').click()
        assert 'production comparison' in page.locator('#aianswer').inner_text().lower()
        assert not errors, errors
        assert not requests, requests
        print(f'PASS {width}px: all panels/charts, controls, no overflow/errors/network')
        page.close()
    browser.close()
