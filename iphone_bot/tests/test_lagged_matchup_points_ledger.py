"""New model first-pregame captures cannot be retroactively rewritten."""
import unittest
try:
    from iphone_bot.lagged_matchup_points_ledger import update
except ImportError:
    from lagged_matchup_points_ledger import update

def pick(projection=22,capture="2026-11-09T17:00:00Z"):
    return {"player_id":"123","team":"BOS","game":"Boston Celtics @ New York Knicks",
            "start":"2026-11-10T00:30:00Z","stat":"PTS",
            "real_prizepicks_line":True,"research_only":True,
            "calibrated_probability":None,"projection":projection,"line":21.5,
            "market_updated":"2026-11-09T16:30:00Z","captured_at":capture}

def source(*rows):
    return {"status":"LIVE_POINTS_CHALLENGER_UNCALIBRATED","predictions":list(rows)}

class LedgerTests(unittest.TestCase):
    def test_first_pregame_projection_is_frozen(self):
        prior=update({},source(pick()),{})
        later=update(prior,source(pick(40,capture="2026-11-09T19:00:00Z")),{})
        self.assertEqual(later["recorded"],1)
        self.assertEqual(later["records"][0]["projection"],22)
        self.assertEqual(later["new_locked"],0)

    def test_late_projection_rejected(self):
        r=update({},source(pick(capture="2026-11-10T00:45:00Z")),{})
        self.assertEqual(r["recorded"],0)

    def test_real_final_box_grades_without_modifying_prediction(self):
        first=update({},source(pick()),{})
        f={"records":[{"status":"GRADED","player_id":"123","team":"BOS",
             "game":"Boston Celtics @ New York Knicks",
             "start":"2026-11-10T00:30:00Z","stat":"PTS",
             "final_source":"NBA_CDN_FINAL",
             "source_game_id":"0022600300","actual":24.0}]}
        after=update(first,{},f)
        self.assertEqual(after["graded"],1)
        self.assertEqual(after["observed_mae"],2.)
        self.assertEqual(after["direction_hit_rate"],1.0)
        self.assertEqual(after["records"][0]["projection"],22)

    def test_unverified_final_does_not_grade(self):
        first=update({},source(pick()),{})
        final={"records":[{"status":"GRADED","player_id":"123","team":"BOS",
             "game":"Boston Celtics @ New York Knicks",
             "start":"2026-11-10T00:30:00Z","stat":"PTS",
             "final_source":"UNVERIFIED","source_game_id":"1","actual":24}]}
        after=update(first,{},final)
        self.assertEqual(after["graded"],0)
        self.assertEqual(after["pending"],1)

if __name__=="__main__":
    unittest.main()
