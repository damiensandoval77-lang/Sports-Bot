import json
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
HTML=(ROOT/"docs/dames-picks/index.html").read_text()
FEEDS=(ROOT/"docs/dames-picks/feeds.js").read_text()
LANDING=(ROOT/"docs/index.html").read_text()

class ProjectionDeliverySmoke(unittest.TestCase):
    def test_current_unified_board_does_not_fabricate_lines_from_no_line_research(self):
        self.assertIn('url=./dames-picks/', LANDING)
        self.assertIn('lagged_matchup_all_market_ledger.json', HTML)
        self.assertIn('function includeArchivedStandard(rows,archive)', FEEDS)
        self.assertIn('projection:null,direction:null,chance:null', FEEDS)
        self.assertIn('quoteOnly:true', FEEDS)
        self.assertIn('!x.quoteOnly&&x.projection!==null&&x.direction!==null', HTML)
        self.assertIn('No sample data is substituted', HTML)
        self.assertIn('p.quoteOnly?"NO AI"', HTML)
        # Price-free forecasts stay separately archived, never fabricated as
        # an observed PrizePicks price or a false calibrated hit chance.
        self.assertTrue((ROOT/"docs/ai_no_line_pregame_archive.json").exists())

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
