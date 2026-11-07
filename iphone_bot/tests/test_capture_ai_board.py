"""Pregame AI lock cannot be backdated, duplicated or replaced after games."""
import unittest
from datetime import datetime,timezone
from iphone_bot.capture_ai_board import capture


def comparison(start="2026-11-13T00:30:00Z",projection=24.2):
    return {"player":"Example Player","player_id":"123","team":"BOS",
        "game":"Boston Celtics @ Miami Heat","start":start,"stat":"PTS",
        "projection":projection,"combined_projection":24,
        "shadow_projection":23.8,"combined_model_count":2,
        "book_quotes":[{"name":"FanDuel","line":22.5,
                        "over":-110,"under":-120,
                        "over_model_probability":0.6}]}


def report(timestamp="2026-11-12T22:00:00Z",markets=None):
    return {"status":"EXPERIMENTAL_NON_CALIBRATED",
        "verified_current_matchups":True,"generated_at":timestamp,
        "comparisons":[comparison()] if markets is None else markets}


class CaptureTests(unittest.TestCase):
    def test_initial_capture_and_repeated_runs_do_not_change_first_record(self):
        first=capture(report(),[],"2026-11-12T22:01:00Z")
        self.assertEqual(len(first),1)
        self.assertEqual(first[0]["captured_at"],"2026-11-12T22:01:00+00:00")
        self.assertEqual(first[0]["original_projection"],24.2)
        changed=report("2026-11-12T22:10:00Z",[comparison(projection=15)])
        later=capture(changed,first,"2026-11-12T22:11:00Z")
        self.assertEqual(len(later),1)
        self.assertEqual(later[0]["original_projection"],24.2)
        self.assertEqual(later[0]["captured_at"],first[0]["captured_at"])

    def test_cannot_capture_after_tipoff_even_if_generated_earlier(self):
        saved=capture(report(),[],"2026-11-13T00:31:00Z")
        self.assertEqual(len(saved),0)

    def test_stale_or_future_timestamp_refused(self):
        with self.assertRaises(ValueError):
            capture(report("2026-11-12T20:00:00Z"),[],"2026-11-12T22:00:00Z")
        with self.assertRaises(ValueError):
            capture(report("2026-11-12T22:30:00Z"),[],"2026-11-12T22:00:00Z")

    def test_reject_untrained_comparisons(self):
        d=report()
        d["status"]="FORM_BASELINE_RESEARCH_ONLY"
        with self.assertRaises(ValueError):capture(d,[],"2026-11-12T22:01:00Z")

    def test_existing_settled_records_are_immutable(self):
        existing=capture(report(),[],"2026-11-12T22:01:00Z")
        existing[0].update(status="SETTLED",actual=29,result="WIN")
        kept=capture(report("2026-11-12T22:10:00Z"),existing,"2026-11-12T22:11:00Z")
        self.assertEqual(kept[0],existing[0])


if __name__=="__main__":unittest.main()
