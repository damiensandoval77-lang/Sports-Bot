import unittest
from datetime import datetime,timezone
try:
    from iphone_bot.underdog_nba_alerts import player_alerts
    from iphone_bot.new_ai_injury_context import live_out,minutes_shift,injury_adjustment
except ImportError:
    from underdog_nba_alerts import player_alerts
    from new_ai_injury_context import live_out,minutes_shift,injury_adjustment

TIP="2026-11-10T00:00:00+00:00"
NOW=datetime(2026,11,9,22,30,tzinfo=timezone.utc)
ROSTER=[{"player":"Austin Reaves","player_id":"1630559","team":"LAL"},
        {"player":"Quentin Grimes","player_id":"1629656","team":"LAL"}]
SCHEDULE=[{"id":"401","game":"Los Angeles Lakers @ Atlanta Hawks",
           "start":TIP,"date_eastern":"2026-11-09","game_state":"pre",
           "away_abbreviation":"LAL","home_abbreviation":"ATL"}]
def post(text,author="456",stamp="2026-11-09T22:20:00Z"):
    return [{"id":"1234567890123456789","author_id":author,"created_at":stamp,"text":text}]
def official(status,issued="2026-11-09T22:00:00Z"):
    return {"status":"OFFICIAL_NBA_REPORT_VERIFIED","injury_data_verified":True,
       "report_issued_at":issued,"players":[{"player":"Austin Reaves",
        "player_id":"1630559","team":"LAL","game_date":"2026-11-09","status":status}]}
class AlertsTests(unittest.TestCase):
    def test_authenticated_ruled_out_tweet_matches_fixture(self):
        alerts=player_alerts(post("Austin Reaves (illness) ruled out Monday."),
                             ROSTER,SCHEDULE,NOW,verified_author_id="456")
        self.assertEqual(len(alerts),1)
        self.assertEqual(alerts[0]["status"],"OUT")
        self.assertEqual(alerts[0]["player_id"],"1630559")
        self.assertFalse(alerts[0]["official_nba_confirmed"])

    def test_wrong_author_or_questionable_cannot_infer_out(self):
        self.assertEqual(player_alerts(post("Austin Reaves ruled out Monday.","other"),
                            ROSTER,SCHEDULE,NOW,verified_author_id="456"),[])
        self.assertEqual(player_alerts(post("Austin Reaves questionable Monday."),
                            ROSTER,SCHEDULE,NOW,verified_author_id="456"),[])
        self.assertEqual(player_alerts(post("Austin Reaves not ruled out Monday."),
                            ROSTER,SCHEDULE,NOW,verified_author_id="456"),[])

    def test_newer_authentic_tweet_can_provisionally_supersede_questionable(self):
        a=player_alerts(post("Austin Reaves (illness) ruled out Monday."),
                        ROSTER,SCHEDULE,NOW,verified_author_id="456")
        out=live_out(official("Questionable"),
            {"status":"UNDERDOGNBA_X_AUTHENTICATED_POLL",
             "verified_x_posts":True,"alerts":a},
            "2026-11-09",TIP,NOW)
        self.assertEqual(out[("1630559","LAL")]["source"],"UNDERDOGNBA_X_PROVISIONAL")

    def test_newer_official_available_overrides_old_news_out(self):
        a=player_alerts(post("Austin Reaves (illness) ruled out Monday.",
                             stamp="2026-11-09T21:00:00Z"),
                        ROSTER,SCHEDULE,NOW,verified_author_id="456")
        out=live_out(official("Available","2026-11-09T22:00:00Z"),
            {"status":"UNDERDOGNBA_X_AUTHENTICATED_POLL",
             "verified_x_posts":True,"alerts":a},
            "2026-11-09",TIP,NOW)
        self.assertEqual(out,{})

    def test_own_out_projections_removed(self):
        x=injury_adjustment({"PTS":20},"1630559","LAL","ATL","2026-11-09",TIP,
          NOW,official("OUT"),{},[])
        self.assertEqual(x["status"],"PLAYER_REPORTED_OUT_SUPPRESS_ALL_MARKETS")

    def test_absent_lineup_splits_no_fabrication(self):
        self.assertIsNone(minutes_shift("123","456","LAL","2026-11-09",[]))
        a=player_alerts(post("Austin Reaves (illness) ruled out Monday."),
                        ROSTER,SCHEDULE,NOW,verified_author_id="456")
        x=injury_adjustment({"PTS":20},"1629656","LAL","ATL","2026-11-09",
           TIP,NOW,official("OUT"),
           {"status":"UNDERDOGNBA_X_AUTHENTICATED_POLL",
            "verified_x_posts":True,"alerts":a},[])
        self.assertEqual(x["status"],"INJURY_MATCHUP_DATA_INSUFFICIENT")
        self.assertIsNone(x["factor"])

if __name__=="__main__":unittest.main()
