import unittest
from datetime import datetime,timezone,timedelta
from iphone_bot.preserve_no_line_forecasts import merge

NOW=datetime(2026,11,9,0,45,tzinfo=timezone.utc)
def row(projection=20,created="2026-11-08T23:43:00Z",start="2026-11-09T00:30:00Z"):
    return {"player_id":"1","player":"Example Player","team":"DAL",
      "game":"Brooklyn Nets @ Dallas Mavericks","start":start,
      "stat":"PTS","projection":projection,"source_recent_games":8,
      "is_pregame_prediction":True,"line":None,"direction":None,
      "calibrated_probability":None,"captured_at":created}
class ArchiveTests(unittest.TestCase):
    def test_frozen_projections_survive_tipoff(self):
        old={"status":"IMMUTABLE_OBSERVED_PRETIP_NOLINE_AI_ARCHIVE","predictions":[row()]}
        new={"status":"PREGAME_PROJECTIONS_NO_LINES","generated_at":"2026-11-09T00:44:00Z","predictions":[]}
        result=merge(old,new,NOW)
        self.assertEqual(result["predictions"][0]["projection"],20)
    def test_after_tipoff_forecast_does_not_enter_archive(self):
        fresh={"status":"PREGAME_PROJECTIONS_NO_LINES",
               "generated_at":"2026-11-09T00:31:00Z",
               "predictions":[row(created="2026-11-09T00:31:00Z")]}
        self.assertEqual(merge({},fresh,NOW)["predictions"],[])
    def test_original_capture_wins_over_later_rerun(self):
        old={"status":"IMMUTABLE_OBSERVED_PRETIP_NOLINE_AI_ARCHIVE","predictions":[row()]}
        fresh={"status":"PREGAME_PROJECTIONS_NO_LINES","generated_at":"2026-11-08T23:55:00Z",
               "predictions":[row(projection=31,created="2026-11-08T23:55:00Z")]}
        self.assertEqual(merge(old,fresh,NOW)["predictions"][0]["projection"],20)
    def test_reject_synthetic_lines(self):
        bad=row();bad["line"]=19.5
        fresh={"status":"PREGAME_PROJECTIONS_NO_LINES",
               "generated_at":"2026-11-08T23:43:00Z","predictions":[bad]}
        self.assertFalse(merge({},fresh,NOW)["predictions"])

if __name__=="__main__":unittest.main()
