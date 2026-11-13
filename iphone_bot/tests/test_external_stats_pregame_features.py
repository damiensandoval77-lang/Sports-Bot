"""Fail-closed, point-in-time research feature contract tests."""
import unittest
try:
    from iphone_bot.external_stats_pregame_features import build_pregame_features
    from iphone_bot.external_stats_snapshot import SnapshotError
except ImportError:
    from external_stats_pregame_features import build_pregame_features
    from external_stats_snapshot import SnapshotError


def snapshot(kind, rows):
    return dict(kind=kind, rows=rows, as_of="2026-11-08",
                season="2026-2027", status="VALIDATED_OFFLINE_RESEARCH_ONLY",
                production_modified=False, calibrated=False)


class PregameFeatureTests(unittest.TestCase):
    def setUp(self):
        self.p = snapshot("player", [
            {"NAME":"Example Player","TEAM":"BOS","MpG":33.0,"USG%":29.0,
             "PpG":23.0,"RpG":6.0,"ApG":7.0}])
        self.t = snapshot("team", [
            {"TEAM":"BOS","PACE":98.0,"oEFF":119.0,"dEFF":109.0},
            {"TEAM":"NYK","PACE":94.0,"oEFF":112.0,"dEFF":106.0}])
        self.mapping = {("Example Player","BOS"):"123"}

    def build(self):
        return build_pregame_features(self.p,self.t,self.mapping,player_id="123",
            team="BOS",opponent="NYK",event_date="2026-11-09")

    def test_point_in_time_baseline(self):
        r=self.build()
        self.assertEqual(r["opponent_defensive_efficiency"],106.0)
        self.assertEqual(r["player_id"],"123")
        self.assertFalse(r["production_modified"])
        self.assertFalse(r["position_defense_verified"])

    def test_same_day_leakage(self):
        self.p["as_of"]="2026-11-09"
        with self.assertRaises(SnapshotError):self.build()

    def test_future_team_leakage(self):
        self.t["as_of"]="2026-11-10"
        with self.assertRaises(SnapshotError):self.build()

    def test_unverified_player_identity(self):
        self.mapping={}
        with self.assertRaises(SnapshotError):self.build()

    def test_wrong_player_id(self):
        self.mapping={("Example Player","BOS"):"987"}
        with self.assertRaises(SnapshotError):self.build()

    def test_missing_opponent_data(self):
        self.t["rows"].pop()
        with self.assertRaises(SnapshotError):self.build()

    def test_missing_usage(self):
        self.p["rows"][0]["USG%"]=None
        with self.assertRaises(SnapshotError):self.build()

    def test_mismatched_season(self):
        self.t["season"]="2025-2026"
        with self.assertRaises(SnapshotError):self.build()


if __name__=="__main__":
    unittest.main()
