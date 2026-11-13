import datetime as dt
import json
import unittest
from iphone_bot.verify_deployed_dashboard import evaluate, run, run_with_retry
from unittest.mock import Mock

NOW=dt.datetime(2026,11,9,18,0,tzinfo=dt.timezone.utc)
HTML='<div id="cards"></div><script src="feeds.js?bundle=r17"></script> m.nba('
HEALTH={"status":"FRESH_RESEARCH_ONLY_PRIZEPICKS_AI_COMPARISONS",
        "generated_at":"2026-11-09T17:50:00+00:00",
        "provider_generated_at":"2026-11-09T17:45:00+00:00",
        "offers_matched":12,"matched_by_game":{"Away @ Home":12},
        "partial_provider_board":False,"source_coverage_complete":True}

class PublicDeploymentCanaryTests(unittest.TestCase):
    def test_pages_propagation_recovers_and_keeps_failed_observation(self):
        failed={"status":"DEGRADED", "reasons":["PUBLIC_AI_JOIN_UNAVAILABLE"]}
        ready={"status":"READY", "reasons":[], "matched_offers":12}
        probe=Mock(side_effect=[failed,ready])
        sleep=Mock()
        result=run_with_retry("https://example.github.io/",probe=probe,sleep=sleep)
        self.assertEqual(result["status"],"READY")
        self.assertEqual(result["attempt_count"],2)
        self.assertEqual(result["attempts"][0]["reasons"],failed["reasons"])
        sleep.assert_called_once_with(20)

    def test_persistent_bad_data_exhausts_budget_without_false_green(self):
        probe=Mock(return_value={"status":"DEGRADED", "reasons":["PUBLIC_PROVIDER_SNAPSHOT_STALE"]})
        sleep=Mock()
        result=run_with_retry("https://example.github.io/",probe=probe,sleep=sleep)
        self.assertEqual(result["status"],"DEGRADED")
        self.assertEqual(result["attempt_count"],3)
        self.assertEqual(probe.call_count,3)
        self.assertEqual(sleep.call_count,2)

    def test_ready_first_probe_does_not_repeat_requests(self):
        probe=Mock(return_value={"status":"READY", "reasons":[]})
        sleep=Mock()
        self.assertEqual(run_with_retry("https://example.github.io/",probe=probe,sleep=sleep)["attempt_count"],1)
        probe.assert_called_once()
        sleep.assert_not_called()

    def test_invalid_retry_budgets_rejected(self):
        for options in [{"attempts":0},{"attempts":4},{"delay":21},{"delay":-1}]:
            with self.subTest(options=options), self.assertRaises(ValueError):
                run_with_retry("https://example.github.io/",**options)

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

    def test_non_object_json_retains_failure_receipt_instead_of_crashing(self):
        for payload in [None, [], "invalid", 42, True]:
            with self.subTest(payload=payload):
                def request(url):
                    return json.dumps(payload) if url.endswith('.json') else HTML
                r=run("https://example.github.io/Sports-Bot/",NOW,request=request)
                self.assertEqual(r["status"],"DEGRADED")
                self.assertIn("PUBLIC_AI_RESEARCH_JSON_INVALID_SHAPE",r["reasons"])
                self.assertIn("PUBLIC_COMPARISONS_MISSING",r["reasons"])
                self.assertIsNone(r["matched_offers"])
                self.assertEqual(r["checked_at"],NOW.isoformat())
                self.assertFalse(r["browser_render_verified"])
                json.dumps(r)

    def test_old_public_json_rejected(self):
        h={**HEALTH,"generated_at":"2026-11-08T10:00:00+00:00"}
        r=evaluate("https://example.github.io/Sports-Bot/",HTML,h,NOW)
        self.assertIn("PUBLIC_COMPARISON_REPORT_STALE",r["reasons"])

if __name__=="__main__":
    unittest.main()
