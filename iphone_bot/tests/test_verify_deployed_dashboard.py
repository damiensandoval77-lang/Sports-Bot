import datetime as dt
import json
import unittest
from iphone_bot.verify_deployed_dashboard import evaluate, run

NOW=dt.datetime(2026,11,9,18,0,tzinfo=dt.timezone.utc)
HTML='<div id="cards"></div><script src="feeds.js?bundle=r17"></script> m.nba('
HEALTH={"status":"FRESH_RESEARCH_ONLY_PRIZEPICKS_AI_COMPARISONS",
        "generated_at":"2026-11-09T17:50:00+00:00",
        "provider_generated_at":"2026-11-09T17:45:00+00:00",
        "offers_matched":12,"matched_by_game":{"Away @ Home":12},
        "partial_provider_board":False,"source_coverage_complete":True}

class PublicDeploymentCanaryTests(unittest.TestCase):
    def test_valid_public_page_and_fresh_complete_data(self):
        responses={"https://example.github.io/Sports-Bot/dames-picks/":HTML,
                   "https://example.github.io/Sports-Bot/ai_prizepicks_quick_join_health.json":json.dumps(HEALTH)}
        result=run("https://example.github.io/Sports-Bot/",NOW,request=responses.__getitem__)
        self.assertEqual(result["status"],"READY")
        self.assertEqual(result["matched_offers"],12)
        self.assertIs(result["browser_render_verified"],False)

    def test_deployed_old_html_fails_even_if_repo_has_newer_code(self):
        r=evaluate("https://example.github.io/Sports-Bot/",'<div id="ai-board"></div>',HEALTH,NOW)
        self.assertIn("DEPLOYED_HTML_MISSING_NEW_PRIZEPICKS_HANDOFF",r["reasons"])
        self.assertEqual(r["status"],"DEGRADED")

    def test_public_url_unreachable_reported_not_falsely_ready(self):
        def unavailable(url):
            raise OSError("Could not reach website")
        r=run("https://example.github.io/Sports-Bot/",NOW,request=unavailable)
        self.assertEqual(r["status"],"DEGRADED")
        self.assertTrue(any("HTTP_FAILED" in reason for reason in r["reasons"]))

    def test_partial_provider_must_not_claim_full_reliability(self):
        h={**HEALTH,"partial_provider_board":True,"source_coverage_complete":False}
        r=evaluate("https://example.github.io/Sports-Bot/",HTML,h,NOW)
        self.assertIn("PUBLIC_PROVIDER_BOARD_INCOMPLETE",r["reasons"])

    def test_old_public_json_rejected(self):
        h={**HEALTH,"generated_at":"2026-11-08T10:00:00+00:00"}
        r=evaluate("https://example.github.io/Sports-Bot/",HTML,h,NOW)
        self.assertIn("PUBLIC_COMPARISON_REPORT_STALE",r["reasons"])

if __name__=="__main__":
    unittest.main()
