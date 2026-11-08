import tempfile
import unittest
from pathlib import Path
from iphone_bot.tracking_opportunity_features import load_tracking,pregame_features,FEATURE_VERSION

class OpportunityTrackingTests(unittest.TestCase):
    def test_missing_source_reports_unavailable_not_fake_values(self):
        with tempfile.TemporaryDirectory() as d:
            rows,coverage=load_tracking(Path(d)/"missing.csv")
            self.assertEqual(coverage["status"],"SOURCE_NOT_CONNECTED")
            self.assertEqual(pregame_features(rows,"123","NYK","2026-11-07")["features"],{})

    def test_pre_tip_only_and_identity_match(self):
        with tempfile.TemporaryDirectory() as d:
            file=Path(d)/"source.csv"
            file.write_text("player_id,game_date,team,source,source_reference,potential_assists,rebound_chances,touches\n"
                "123,2026-11-01,NYK,NBA Tracking,ref1,10,9,55\n"
                "123,2026-11-02,NYK,NBA Tracking,ref2,12,11,57\n"
                "123,2026-11-03,NYK,NBA Tracking,ref3,14,13,59\n"
                "123,2026-11-07,NYK,NBA Tracking,ref4,80,80,80\n"
                "123,2026-11-02,BOS,NBA Tracking,ref5,99,99,99\n")
            rows,coverage=load_tracking(file)
            self.assertEqual(coverage["rows"],5)
            feature=pregame_features(rows,"123","NYK","2026-11-07")
            self.assertEqual(feature["feature_version"],FEATURE_VERSION)
            self.assertEqual(feature["features"]["potential_assists"]["last5"],12)
            self.assertEqual(feature["features"]["rebound_chances"]["last5"],11)
            self.assertEqual(feature["latest_recorded_date"],"2026-11-03")
            self.assertFalse(feature["production_applied"])
            self.assertEqual(pregame_features(rows,"123","BOS","2026-11-07")["status"],"NOT_AVAILABLE")
            self.assertEqual(pregame_features(rows,"999","NYK","2026-11-07")["status"],"NOT_AVAILABLE")

    def test_reject_conflicting_same_game_rows(self):
        with tempfile.TemporaryDirectory() as d:
            file=Path(d)/"source.csv"
            file.write_text("player_id,game_date,team,source,source_reference,potential_assists\n"
                "123,2026-11-01,NYK,NBA,ref1,10\n"
                "123,2026-11-01,NYK,NBA,ref2,20\n")
            with self.assertRaises(ValueError):
                load_tracking(file)

    def test_partial_fields_are_not_fabricated(self):
        with tempfile.TemporaryDirectory() as d:
            file=Path(d)/"source.csv"
            file.write_text("player_id,game_date,team,source,source_reference,potential_assists,rebound_chances\n"
                "123,2026-11-01,NYK,NBA,ref1,5,\n"
                "123,2026-11-02,NYK,NBA,ref2,7,\n"
                "123,2026-11-03,NYK,NBA,ref3,9,\n")
            rows,_=load_tracking(file)
            result=pregame_features(rows,"123","NYK","2026-11-05")
            self.assertIn("potential_assists",result["features"])
            self.assertNotIn("rebound_chances",result["features"])
