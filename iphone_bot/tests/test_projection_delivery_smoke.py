import json
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
HTML=(ROOT/"docs/index.html").read_text()

class ProjectionDeliverySmoke(unittest.TestCase):
    def test_main_board_does_not_depend_on_betting_lines(self):
        self.assertIn('const independent=(!entries.length&&noLineForecast?',HTML)
        self.assertIn('independent.length+" independent AI estimates',HTML)
        self.assertIn('if(!list.length&&independent.length)',HTML)
        self.assertIn('independent?"AI PROJECTIONS READY"',HTML)
        self.assertIn('const displayed=independent?model:priced',HTML)
        self.assertIn('"PrizePicks line","Unavailable"',HTML)
        self.assertIn('noLineArchive=await fetchJSON("ai_no_line_pregame_archive.json")',HTML)

    def test_frozen_archive_has_verified_pretip_captures(self):
        archive=json.loads((ROOT/"docs/ai_no_line_pregame_archive.json").read_text())
        self.assertEqual(archive["status"],"IMMUTABLE_OBSERVED_PRETIP_NOLINE_AI_ARCHIVE")
        self.assertTrue(archive["predictions"],"An empty archive cannot support live games")
        for p in archive["predictions"]:
            created=datetime.fromisoformat(p["captured_at"].replace("Z","+00:00"))
            start=datetime.fromisoformat(p["start"].replace("Z","+00:00"))
            self.assertLess(created,start)
            self.assertIsNone(p["line"])
            self.assertIsNone(p["direction"])
            self.assertIsNone(p["calibrated_probability"])

    def test_latest_valid_fallback_has_forecasts_if_it_claims_success(self):
        feed=json.loads((ROOT/"docs/ai_projection_fallback.json").read_text())
        if feed["status"]=="PREGAME_PROJECTIONS_NO_LINES":
            self.assertGreater(len(feed["predictions"]),0)
            self.assertTrue(all(datetime.fromisoformat(feed["generated_at"]) <
                datetime.fromisoformat(p["start"]) for p in feed["predictions"]))

if __name__=="__main__":unittest.main()
