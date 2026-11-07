"""Validate predicted defensive assignments are historical and explicitly unverified."""
import unittest
from iphone_bot.defender_v3_assignment import (
    projected_assignment,assignment_points_scenario,position_affinity,evaluate_assignment
)


def past(off="10",defender="21",poss=60,switches=8,team="NYK",day="2026-01-01"):
    return {(off,defender):{"poss":poss,"switches":switches,"def_team":team,
         "last_seen":day,"two_a":25.,"two_m":8.,"three_a":10.,"three_m":3.}}


class AssignmentTests(unittest.TestCase):
    def test_recent_opponent_matchup_and_rotation(self):
        rotation=[("21",32.),("22",30.),("23",25.)]
        allocation=projected_assignment("10","NYK",rotation,past(),
            {"10":"G","21":"G"},"2026-01-10")
        self.assertEqual(allocation["status"],"HISTORICAL_ASSIGNMENT_PROJECTION_RESEARCH_ONLY")
        self.assertEqual(allocation["predicted_top_defender"],"21")
        self.assertEqual(allocation["unassigned_share"],.25)
        self.assertFalse(allocation["confirmed_assignment"])
        self.assertLessEqual(sum(r["estimated_exposure_share"] for r in allocation["candidate_defenders"]),.75+.0001)

    def test_wrong_team_future_or_old_pair_is_excluded(self):
        rotation=[("21",35.),("22",30.),("23",20.)]
        for kwargs in ({"team":"BOS"},{"day":"2026-02-01"},{"day":"2026-01-10"}):
            prior=past(**kwargs)
            result=projected_assignment("10","NYK",rotation,prior,{},"2026-01-11")
            self.assertEqual(result["status"],"NO_RECENT_DIRECT_ASSIGNMENT_EVIDENCE")
            self.assertIsNone(result["predicted_top_defender"])

    def test_switching_reduces_assignment_weight_and_position_is_optional(self):
        rotation=[("21",32.),("22",30.),("23",26.)]
        prior={**past("10","21",poss=80,switches=80),
               **past("10","22",poss=80,switches=0)}
        normal=projected_assignment("10","NYK",rotation,prior,{},"2026-01-10")
        self.assertEqual(normal["predicted_top_defender"],"22")
        self.assertEqual(position_affinity(None,"G"),1.)
        self.assertGreater(position_affinity("G","G"),position_affinity("G","C"))

    def test_points_scenario_not_created_without_valid_allocation(self):
        baseline={"expected_points":25.,"expected_2pa":12.,"expected_3pa":8.,
                  "expected_2p_pct":.52,"expected_3p_pct":.36}
        empty=projected_assignment("10","NYK",[("21",32.)],past(),{},"2026-01-10")
        self.assertIsNone(assignment_points_scenario(baseline,empty,past(),"10"))
        alloc=projected_assignment("10","NYK",[("21",32.),("22",30.),("23",26.)],
                                  past(),{},"2026-01-10")
        estimate=assignment_points_scenario(baseline,alloc,past(),"10")
        self.assertLess(estimate,25.)
        self.assertGreaterEqual(estimate,23.)

    def test_top_defender_accuracy_uses_separate_true_outcomes(self):
        forecast={"status":"HISTORICAL_ASSIGNMENT_PROJECTION_RESEARCH_ONLY",
                  "predicted_top_defender":"21","minutes_only_top":"22"}
        result=evaluate_assignment({("g1","10"):{"top_defender":"21"}},
                                   {("g1","10"):forecast})
        self.assertEqual(result["eligible_games"],1)
        self.assertEqual(result["predicted_top_defender_accuracy"],1.)
        self.assertEqual(result["minutes_only_top_defender_accuracy"],0.)


if __name__=="__main__":unittest.main()
