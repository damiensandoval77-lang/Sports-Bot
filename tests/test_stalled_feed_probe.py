"""Real-browser regression: the injected stall must not outlive its check."""
import os
import unittest
from pathlib import Path
from playwright.sync_api import sync_playwright
from scripts.stalled_feed_probe import stalled_feed_deadline


class StalledFeedProbeTest(unittest.TestCase):
    def test_deadline_and_clean_browser_teardown(self):
        html = (Path(__file__).resolve().parents[1] / "docs/dames-picks/index.html").read_text()
        helper = html.split("async function fetchData", 1)[1].split("async function getJSON", 1)[0]
        errors = []
        with sync_playwright() as pw:
            options = {"headless": True}
            if os.environ.get("DAMES_TEST_CHROMIUM"):
                options["executable_path"] = os.environ["DAMES_TEST_CHROMIUM"]
            browser = pw.chromium.launch(**options)
            page = browser.new_page()
            loop = page._impl_obj._loop
            previous_handler = loop.get_exception_handler()
            loop.set_exception_handler(lambda loop, context: errors.append(str(context)))
            try:
                page.route("**/*", lambda route: route.fulfill(body="<html></html>", content_type="text/html"))
                page.goto("https://dames-picks.invalid/")
                page.add_script_tag(content="async function fetchData" + helper)
                evidence = stalled_feed_deadline(page)
                self.assertTrue(evidence["rejected"])
                self.assertEqual(evidence["error"], "Feed request timed out")
                self.assertGreaterEqual(evidence["elapsed_ms"], 80)
                self.assertLess(evidence["elapsed_ms"], 3000)
                browser.close()
                self.assertEqual(errors, [], "Unhandled Playwright callback during teardown")
            finally:
                loop.set_exception_handler(previous_handler)
