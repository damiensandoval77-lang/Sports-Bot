import unittest
from iphone_bot.tracking_opportunities_v1 import evaluate

def feed():
    rows=[]
    for d in range(15,25):
        rows.append({"player_id":"10","team":"BOS","game_id":f"0022600{d:03d}",
           "game_date":f"2026-10-{d:02d}","observed_at":f"2026-10-{d+1:02d}T08:00:00Z",
           "minutes":30,"potential_assists":12,"assists":6,
           "rebound_chances":16,"rebounds":8})
    return {"status":"AUTHORIZED_TRACKING_RESEARCH","season":"2026-27",
      "licensed_use_verified":True,"source":"TEST_SYNTHETIC_AUTHORIZED_SOURCE",
      "generated_at":"2026-11-06T22:45:00Z",
      "authorization":{"allowed_use":"NBA_PROP_RESEARCH",
         "reviewer_confirmation":"MANUALLY_VERIFIED",
         "permission_reference":"TEST_DATA_NOT_REAL_PROVIDER_PERMISSION"},
      "observations":rows}
def run(market,source=None,**kwargs):
    p=dict(player_id="10",team="BOS",market=market,event_date="2026-11-06",
        baseline=4.0 if market=="AST" else 6.,expected_minutes=30,
        captured_at="2026-11-06T23:00:00Z")
    p.update(kwargs)
    return evaluate(source if source is not None else feed(),**p)

class TrackingTest(unittest.TestCase):
    def test_potential_assists_create_research_not_real_bet(self):
        r=run("AST")
        self.assertEqual(r["status"],"PREGAME_TRACKING_OPPORTUNITY_SHADOW")
        self.assertEqual(r["prior_games"],10)
        self.assertEqual(r["expected_chances"],12.)
        self.assertEqual(r["projection"],4.48)
        self.assertEqual(r["feature"],"potential_assists")
        self.assertFalse(r["live_applied"])
    def test_rebound_chances_and_minutes(self):
        r=run("REB")
        self.assertEqual(r["feature"],"rebound_chances")
        self.assertEqual(r["expected_chances"],16.)
        self.assertEqual(r["projection"],6.5)
    def test_future_outcome_and_duplicates_rejected(self):
        a=feed();a["observations"][0]["game_date"]="2026-11-06"
        self.assertEqual(run("AST",a)["status"],"LOOKAHEAD_REJECTED")
        a=feed();a["observations"].append(dict(a["observations"][0]))
        self.assertEqual(run("REB",a)["status"],"DUPLICATE_GAME_ID")
        a=feed();a["observations"][0]["observed_at"]="2026-11-07T00:00:00Z"
        self.assertEqual(run("AST",a)["status"],"LOOKAHEAD_REJECTED")
    def test_missing_rights_or_stale_feed_is_not_scored(self):
        a=feed();a["licensed_use_verified"]=False
        self.assertIsNone(run("REB",a)["projection"])
        a=feed();a["authorization"]["allowed_use"]="NONCOMMERCIAL_VIEWING"
        self.assertEqual(run("AST",a)["status"],"MISSING_USAGE_PERMISSION")
        a=feed();a["generated_at"]="2026-11-07T01:00:00Z"
        self.assertEqual(run("REB",a)["status"],"UNSAFE_SOURCE_TIMESTAMP")
    def test_sample_and_denominator_sanity(self):
        a=feed();a["observations"]=a["observations"][:5]
        self.assertEqual(run("AST",a)["status"],"INSUFFICIENT_TRACKING_SAMPLE")
        a=feed();a["observations"][0]["assists"]=99
        self.assertEqual(run("AST",a)["status"],"INVALID_OPPORTUNITY_METRICS")
        a=feed();a["observations"][0]["rebound_chances"]=None
        self.assertEqual(run("REB",a)["status"],"INVALID_OPPORTUNITY_METRICS")
    def test_no_external_fetch_is_embedded(self):
        import inspect
        from iphone_bot import tracking_opportunities_v1
        text=inspect.getsource(tracking_opportunities_v1)
        self.assertNotIn("urlopen(",text)
        self.assertNotIn("stats.nba.com/stats",text)

if __name__=="__main__":unittest.main()
