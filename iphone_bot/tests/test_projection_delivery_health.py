import unittest
from datetime import datetime,timezone,timedelta
from iphone_bot.projection_delivery_health import report
NOW=datetime(2026,11,9,1,0,tzinfo=timezone.utc)
GAME="Brooklyn Nets @ Dallas Mavericks"
TIP=(NOW-timedelta(minutes=30)).isoformat()
CAP=(NOW-timedelta(hours=2)).isoformat()
def fixture():
    return {"source":"Verified NBA fixture schedule","coverage_complete":True,
      "games":[{"game":GAME,"start":TIP}]}
def row():
    return {"player_id":"1","player":"Example","team":"DAL","game":GAME,
      "start":TIP,"captured_at":CAP,"stat":"PTS","projection":20.5,
      "line":None,"direction":None,"is_pregame_prediction":True}
class CoverageTests(unittest.TestCase):
    def test_preserved_forecasts_keep_started_games_covered(self):
        archive={"status":"IMMUTABLE_OBSERVED_PRETIP_NOLINE_AI_ARCHIVE",
                 "predictions":[row()]}
        result=report(fixture(),{},archive,NOW)
        self.assertEqual(result["status"],"ALL_LISTED_GAMES_HAVE_PREGAME_AI")
        self.assertEqual(result["games"][0]["state"],"started")
        self.assertEqual(result["games"][0]["preserved_pretip_player_stats"],1)
    def test_missing_matchup_is_visible(self):
        result=report(fixture(),{},{"predictions":[]},NOW)
        self.assertEqual(result["missing_ai_games"],[GAME])
        self.assertEqual(result["status"],"PROJECTION_COVERAGE_GAPS")
    def test_after_tipoff_capture_does_not_qualify(self):
        fake={**row(),"captured_at":NOW.isoformat()}
        result=report(fixture(),{},{"status":"IMMUTABLE_OBSERVED_PRETIP_NOLINE_AI_ARCHIVE",
                                   "predictions":[fake]},NOW)
        self.assertEqual(result["missing_ai_games"],[GAME])
if __name__=="__main__":unittest.main()
