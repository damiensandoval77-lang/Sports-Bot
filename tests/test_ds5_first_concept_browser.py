"""Browser smoke test for the FIRST DS5 Sports Media concept.
Only local published snapshots are used; third-party live score/photo calls are disabled.
Tests functional navigations and valid empty-data handling, not mocked predictions.
"""
import contextlib
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get("DS5_SCREENSHOT_DIR", "/tmp/ds5-first-concept"))
OUT.mkdir(parents=True, exist_ok=True)
port = 18765
server = subprocess.Popen(
    [sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1", "--directory", str(ROOT / "docs")],
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL
)
try:
    url = os.environ.get("DS5_BASE_URL", f"http://127.0.0.1:{port}/dames-picks/")
    for _ in range(70):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                break
        except OSError:
            time.sleep(.2)
    else:
        raise AssertionError("Local Pages test server failed to start")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        for name, viewport in [
            ("desktop", {"width": 1560, "height": 1000}),
            ("phone", {"width": 390, "height": 844})
        ]:
            page = browser.new_page(viewport=viewport, device_scale_factor=1)
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.add_init_script(
                "window.DAMES_DISABLE_EXTERNAL_PHOTOS=true;"
                "window.DAMES_DISABLE_DIRECT_SCORES=true;"
            )
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            try:
                page.wait_for_selector("body.ds5-first-concept .ds5-dashboard", timeout=15000)
            except Exception:
                print("DEBUG title:", page.title(), flush=True)
                print("DEBUG body class:", page.locator("body").get_attribute("class"), flush=True)
                print("DEBUG dashboard count:", page.locator(".ds5-dashboard").count(), flush=True)
                print("DEBUG scripts:", [x.get_attribute("src") for x in page.locator("script[src]").all()], flush=True)
                print("DEBUG page errors:", errors[:10], flush=True)
                page.screenshot(path=str(OUT / f"ds5-{name}-failed.png"), full_page=True)
                raise
            assert page.locator(".ds5-sidebar").count()==1, "missing DS5 sidebar"
            assert page.locator(".ds5-main .ds5-titlebar").is_visible(), "missing first-concept heading"
            assert page.locator(".ds5-player-feature .hero").count()==1, "missing connected player profile"
            assert page.locator(".ds5-matchup-feature #matchup").count()==1, "missing matching research panel"
            assert page.locator("#ds5-props-rows").count()==1, "missing actual line summary"
            assert page.locator("#ds5-live-info").count()==1, "missing real score summary"
            assert page.locator("#ds5-grade-rate").count()==1, "missing graded records summary"
            assert page.locator(".topbar .brandbolt").inner_text().replace("\n","").strip()=="DS5"
            assert page.locator("link[href*='ds5-v1.css']").count()==1
            assert page.locator(".ds5-sidebar").is_visible()
            if name=="phone":
                assert page.locator(".ds5-sidebar").bounding_box()["width"]<=viewport["width"], "sidebar overflows phone"
            page.screenshot(path=str(OUT / f"ds5-{name}.png"), full_page=True)
            page.locator(".ds5-side-nav button").filter(has_text="Live Tracker").first.click()
            page.wait_for_selector("body.unified-tool-mode", timeout=5000)
            assert page.locator("#unified-workspace").is_visible(), "live tracker navigation failed"
            page.locator(".unified-navigation button[data-workspace=player]").click()
            page.wait_for_selector("body:not(.unified-tool-mode) .ds5-main", timeout=5000)
            assert page.locator(".ds5-main").is_visible(), "could not return to dashboard"
            assert not errors, f"{name} JavaScript errors: {errors[:5]}"
            print(f"PASS {name}: first-concept layout, nav, live adapter, labels, and no runtime exception")
            page.close()
        browser.close()
finally:
    server.terminate()
    with contextlib.suppress(Exception):
        server.wait(timeout=8)
