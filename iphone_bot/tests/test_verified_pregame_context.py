"""Source identity, rights and time safeguards for game-day context."""
import unittest
try:
    from iphone_bot.verified_pregame_context import context,ContextRejected
except ImportError:
    from verified_pregame_context import context,ContextRejected

PLAYER="123"
GAME="0022600123"
TIP="2026-11-10T00:30:00Z"
CAPTURE="2026-11-09T23:00:00Z"
def field(source,**details):
    return {"source":source,"rights_confirmed":True,
            "published_at":"2026-11-09T21:00:00Z","game_id":GAME,**details}

def record():
    return {"player_id":PLAYER,"team":"BOS","opponent":"NYK","game_id":GAME,
            "usage":field("OFFICIAL_NBA_ADVANCED",pct=24.0),
            "injuries":field("OFFICIAL_NBA_INJURY_REPORT",team="BOS",out_player_ids=["234"]),
            "position":field("OFFICIAL_NBA_ROSTER",player_id=PLAYER,role="G"),
            "position_defense":field("LICENSED_POSITION_ALLOWANCE",opponent="NYK",
                         role="G",sample_games=5,latest_game_date="2026-11-08")}

def call(r):
    return context(r,player_id=PLAYER,team="BOS",opponent="NYK",game_id=GAME,
                   event_start=TIP,as_at=CAPTURE)

class ContextTests(unittest.TestCase):
    def test_verified_context_is_descriptive_only(self):
        v=call(record())
        self.assertEqual(v["usage_pct"],24.0)
        self.assertEqual(v["verified_out_player_ids"],["234"])
        self.assertEqual(v["position_role"],"G")
        self.assertEqual(v["position_defense_sample"],5)
        self.assertFalse(v["apply_to_trained_matchup_model"])

    def test_future_injury_status_is_rejected_not_inferred(self):
        r=record()
        r["injuries"]["published_at"]="2026-11-09T23:30:00Z"
        v=call(r)
        self.assertEqual(v["verified_out_player_ids"],[])
        self.assertIn("INJURIES_NOT_AVAILABLE_AT_CAPTURE",v["reason_codes"])

    def test_usage_with_missing_rights_rejected(self):
        r=record()
        r["usage"]["rights_confirmed"]=False
        v=call(r)
        self.assertIsNone(v["usage_pct"])

    def test_mismatched_fixture_rejected(self):
        r=record()
        r["game_id"]="wrong"
        with self.assertRaises(ContextRejected):call(r)

    def test_mismatched_defense_role_rejected(self):
        r=record()
        r["position_defense"]["role"]="F"
        v=call(r)
        self.assertIsNone(v["position_defense_sample"])

    def test_post_tip_capture_rejected(self):
        with self.assertRaises(ContextRejected):
            context(record(),player_id=PLAYER,team="BOS",opponent="NYK",
                game_id=GAME,event_start=TIP,as_at="2026-11-10T01:00:00Z")

if __name__=="__main__":
    unittest.main()
