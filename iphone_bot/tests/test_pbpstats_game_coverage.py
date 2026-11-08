"""Real ON/OFF sample qualification needs game-level seconds, not game box scores."""
import copy
import unittest
from iphone_bot.pbpstats_game_coverage import audit_pair

def fixture():
    target=[];mate=[]
    for d in range(1,8):
        gid=f"0022600{d:03d}"
        day=f"2026-10-{d:02d}"
        target.append({"PlayerId":"100","Date":day,"GameId":gid,
                       "Possessions":[{"StartTime":0,"EndTime":2400}]})
        mate.append({"PlayerId":"900","Date":day,"GameId":gid,
                     "Possessions":[{"StartTime":0,"EndTime":1200}]})
    return target,mate

class GameCoverageTests(unittest.TestCase):
    def test_exact_on_off_game_counts_and_minute_exposure(self):
        t,m=fixture()
        result=audit_pair(t,m,player_id="100",teammate_id="900",cutoff_date="2026-11-06")
        self.assertEqual(result["with"]["games"],7)
        self.assertEqual(result["without"]["games"],7)
        self.assertEqual(result["with"]["minutes"],140)
        self.assertEqual(result["without"]["minutes"],140)
        self.assertEqual(len(result["with"]["game_ids"]),7)
        self.assertFalse(result["rights_verified"])
    def test_zero_duration_possession_does_not_count_as_stint(self):
        t,m=fixture()
        t[0]["Possessions"].append({"StartTime":2400,"EndTime":2400})
        m[0]["Possessions"].append({"StartTime":1200,"EndTime":1200})
        result=audit_pair(t,m,player_id="100",teammate_id="900",cutoff_date="2026-11-06")
        self.assertEqual(result["with"]["minutes"],140)
        self.assertEqual(result["without"]["minutes"],140)

    def test_missing_teammate_produces_no_invented_with_group(self):
        t,m=fixture()
        with self.assertRaisesRegex(ValueError,"Insufficient independent with"):
            audit_pair(t,[],player_id="100",teammate_id="900",cutoff_date="2026-11-06")
    def test_future_and_duplicate_game_rejected(self):
        t,m=fixture()
        t.append({**t[0],"Date":"2026-11-07","GameId":"0022600999"})
        with self.assertRaisesRegex(ValueError,"Future"):
            audit_pair(t,m,player_id="100",teammate_id="900",cutoff_date="2026-11-06")
        t,m=fixture();t.append(copy.deepcopy(t[0]))
        with self.assertRaisesRegex(ValueError,"Duplicate GameId"):
            audit_pair(t,m,player_id="100",teammate_id="900",cutoff_date="2026-11-06")
    def test_merge_overlapping_possessions_without_double_counting(self):
        t,m=fixture()
        t[0]["Possessions"].append({"StartTime":2000,"EndTime":2500})
        result=audit_pair(t,m,player_id="100",teammate_id="900",cutoff_date="2026-11-06")
        self.assertEqual(result["with"]["minutes"],140)
        self.assertAlmostEqual(result["without"]["minutes"],141.6667,places=4)
        t,m=fixture()
        t[0]["Possessions"].append({"StartTime":1000,"EndTime":2000})
        result=audit_pair(t,m,player_id="100",teammate_id="900",cutoff_date="2026-11-06")
        self.assertEqual(result["with"]["minutes"],140)
        self.assertEqual(result["without"]["minutes"],140)

    def test_reject_wrong_person_and_game_day(self):
        t,m=fixture();m[0]["PlayerId"]="101"
        with self.assertRaisesRegex(ValueError,"identity"):
            audit_pair(t,m,player_id="100",teammate_id="900",cutoff_date="2026-11-06")
        t,m=fixture();m[0]["Date"]="2026-10-11"
        with self.assertRaisesRegex(ValueError,"Conflicting"):
            audit_pair(t,m,player_id="100",teammate_id="900",cutoff_date="2026-11-06")

if __name__=="__main__":unittest.main()
