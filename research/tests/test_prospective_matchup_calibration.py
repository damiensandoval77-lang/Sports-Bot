import copy
import unittest
from research.archive_matchup_forecasts import add, STATUS
from research.audit_prospective_matchup_calibration import report

QUOTE="2026-11-11T00:00:00Z"
FEATURE="2026-11-11T01:00:00Z"
MODEL="2026-11-11T02:00:00Z"
SNAPSHOT="2026-11-11T02:01:00Z"
TIP="2026-11-11T04:00:00Z"
AFTER="2026-11-11T08:00:00Z"
def source():
    chance={"method":"POSITION_V_POSITION_DEF_RATING_RESEARCH_ANALYTIC_V1",
      "modeled_selected_probability":.62,"calibrated":False,"research_only":True,
      "verified_betting_edge":False,"opponent_aware_inputs_sourced":True,
      "opponent_adjustment_validated":False,
      "source_provenance":{k:FEATURE for k in
         ("position_observed_at","rating_observed_at","player_observed_at","minutes_snapshot_at")}}
    market={"player_id":"42","player":"Example","team":"BOS","opponent":"NYK",
      "stat":"PTS","start":TIP,"line":20.5,"original_side":"MORE",
      "captured_at":MODEL,"matchup_projection":23.0,"original_projection":21.0,
      "estimated_hit_chance":chance}
    shadow={"status":"POSITION_MATCHUP_RESEARCH_ONLY_PROBABILITY",
      "captured_at":SNAPSHOT,"model_id":"pregame-position",
      "eligible_opponent_conditioned_estimates":1,"production_approved":False,
      "published_to_cards":False,"calibrated":False,"records":[market]}
    ledger={"status":"FROZEN_NEW_AI_ALL_MARKET","records":[{
       "player_id":"42","team":"BOS","opponent":"NYK",
       "start":TIP,"stat":"PTS","line":20.5,"captured_at":QUOTE,
       "pickem_tier":"standard","standard_line_two_sided_verified":True,
       "estimated_hit_chance":{"modeled_direction":"More",
                                 "modeled_selected_probability":.56},
       "grade":"GRADED","actual":25,"direction_hit":True,
       "final_source":"NBA_CDN_FINAL","source_game_id":"NBA001"}]}
    return shadow,ledger

class ProspectiveTests(unittest.TestCase):
    def test_archive_is_append_only_and_idempotent(self):
        s,l=source()
        a,n=add(None,s)
        self.assertEqual(n,1)
        b,n2=add(a,s)
        self.assertEqual(n2,0)
        self.assertEqual(a,b)
        altered=copy.deepcopy(s)
        altered["records"][0]["estimated_hit_chance"]["modeled_selected_probability"]=.95
        with self.assertRaises(ValueError):add(a,altered)

    def test_rating_after_original_quote_but_before_model_is_prospective(self):
        s,l=source()
        archive,_=add(None,s)
        result=report(archive,l,checked_at=AFTER)
        self.assertEqual(result["paired_final_grades"],1)
        self.assertEqual(result["total"]["n"],1)
        self.assertEqual(result["total"]["observed_hit_rate"],1)
        self.assertFalse(result["eligibility_gate_passed"])
        self.assertFalse(result["calibration_certified"])

    def test_no_graded_outcome_before_tip(self):
        s,l=source()
        archive,_=add(None,s)
        self.assertEqual(report(archive,l,checked_at="2026-11-11T03:00:00Z")["paired_final_grades"],0)

    def test_outstanding_game_never_faked_into_grade(self):
        s,l=source()
        l["records"][0]["grade"]="PENDING"
        l["records"][0]["actual"]=None
        l["records"][0]["direction_hit"]=None
        archive,_=add(None,s)
        result=report(archive,l,checked_at=AFTER)
        self.assertEqual(result["paired_final_grades"],0)
        self.assertEqual(result["exclusions"]["awaiting_independently_verified_final_grade"],1)

    def test_multiple_pregame_refreshes_count_as_one_resolved_outcome(self):
        s,l=source()
        archive,_=add(None,s)
        later=copy.deepcopy(s)
        later["captured_at"]="2026-11-11T02:08:00Z"
        later["records"][0]["captured_at"]="2026-11-11T02:05:00Z"
        later["records"][0]["estimated_hit_chance"]["modeled_selected_probability"]=.91
        archive,added=add(archive,later)
        self.assertEqual(added,1)
        self.assertEqual(len(archive["forecasts"]),2)
        result=report(archive,l,checked_at=AFTER)
        self.assertEqual(result["paired_final_grades"],1)
        self.assertEqual(result["total"]["brier"],round((.62-1)**2,5))
        self.assertEqual(result["exclusions"]["repeated_model_snapshot_same_outcome"],1)
        self.assertTrue(result["unique_outcome_policy"].startswith("ONE_EARLIEST"))
        # Archive insertion order cannot select a later, better probability.
        archive["forecasts"].reverse()
        reversed_result=report(archive,l,checked_at=AFTER)
        self.assertEqual(reversed_result["total"]["brier"],result["total"]["brier"])

    def test_wrong_line_cannot_be_paired(self):
        s,l=source();l["records"][0]["line"]=22.5
        a,_=add(None,s)
        self.assertEqual(report(a,l,checked_at=AFTER)["paired_final_grades"],0)

    def test_nonstandard_market_is_not_grade(self):
        s,l=source();l["records"][0]["pickem_tier"]="demon"
        a,_=add(None,s)
        self.assertEqual(report(a,l,checked_at=AFTER)["paired_final_grades"],0)

    def test_verified_dnp_is_not_a_miss(self):
        s,l=source()
        l["records"][0].update(grade="EXCLUDED_VERIFIED_DNP",actual=None,direction_hit=None)
        a,_=add(None,s)
        out=report(a,l,checked_at=AFTER)
        self.assertEqual(out["paired_final_grades"],0)
        self.assertEqual(out["exclusions"]["verified_dnp_void"],1)

    def test_wrong_team_final_source_never_graded(self):
        s,l=source();l["records"][0]["final_source"]="UNVERIFIED_APP_SCORE"
        a,_=add(None,s)
        self.assertEqual(report(a,l,checked_at=AFTER)["paired_final_grades"],0)

    def test_invalid_final_direction_is_rejected(self):
        s,l=source();l["records"][0]["direction_hit"]=False
        a,_=add(None,s)
        with self.assertRaises(ValueError):report(a,l,checked_at=AFTER)

    def test_push_not_hit_or_loss(self):
        s,l=source();l["records"][0].update(actual=20.5,direction_hit=False)
        a,_=add(None,s)
        self.assertEqual(report(a,l,checked_at=AFTER)["exclusions"]["push_excluded"],1)

if __name__=="__main__":unittest.main()
