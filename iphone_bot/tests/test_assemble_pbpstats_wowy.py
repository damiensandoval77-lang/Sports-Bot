"""Entire authorized ON/OFF capture->normalized private research pipeline."""
import unittest
from iphone_bot.assemble_pbpstats_wowy import assemble
from iphone_bot.pbpstats_request_plan import request_plan
from iphone_bot.lineup_onoff_research import evaluate

START="2026-11-08T01:00:00Z"
CAPTURE="2026-11-07T19:00:00Z"

def fixture():
    params=request_plan("100","900","BOS",cutoff_date="2026-11-06")["requests"]
    days=[f"2026-10-{i:02d}" for i in range(2,12)]
    target=[{"PlayerId":"100","Date":day,
             "GameId":f"0022600{i:03d}",
             "Possessions":[{"StartTime":0,"EndTime":2400}]}
            for i,day in enumerate(days,1)]
    teammate=[{"PlayerId":"900","Date":day,
               "GameId":f"0022600{i:03d}",
               "Possessions":[{"StartTime":0,"EndTime":1200}]}
              for i,day in enumerate(days,1)]
    proof=lambda name:{"verified_completed_games":True,"game_dates":days,
                       "request_params":params[name]}
    response=lambda pts:{"multi_row_table_data":[
        {"EntityId":"100","Points":pts,"Rebounds":30,"Assists":20,
         "SecondsPlayed":12000,"Minutes":200}]}
    bundle={"season":"2026-27","source":"FICTIONAL_TEST_CAPTURE",
            "generated_at":"2026-11-07T18:00:00Z",
            "pairs":[{"player_id":"100","teammate_id":"900","team":"BOS",
              "observed_through_at":"2026-11-07T17:00:00Z",
              "data_through":"2026-11-06",
              "with_response":response(100),
              "without_response":response(120),
              "target_distribution":target,
              "teammate_distribution":teammate,
              "with_provenance":proof("with"),
              "without_provenance":proof("without")}]}
    approval={"reviewed_for_betting_analytics":True,
       "allowed_use":"NBA_PROP_RESEARCH",
       "reviewer_confirmation":"MANUALLY_VERIFIED",
       "permission_reference":"TEST_ONLY_FAKE_FIXTURE"}
    form={"players":[{"player_id":"100","team":"BOS"},
                     {"player_id":"900","team":"BOS"}]}
    return bundle,approval,form

class WholePipelineTest(unittest.TestCase):
    def test_end_to_end_all_markets_stay_shadow_only(self):
        args=fixture()
        normalized=assemble(*args)
        self.assertEqual(len(normalized["observations"]),1)
        self.assertEqual(normalized["observations"][0]["with"]["games"],10)
        self.assertEqual(normalized["observations"][0]["without"]["minutes"],200)
        for market in ("PTS","REB","AST","PRA"):
            result=evaluate(normalized,player_id="100",teammate_id="900",
                team="BOS",market=market,baseline=22,
                expected_minutes=30,game_start=START,captured_at=CAPTURE)
            self.assertEqual(result["status"],"PREGAME_LICENSED_ON_OFF_SHADOW")
            self.assertIsNotNone(result["projection"])
            self.assertFalse(result["production_applied"])
    def test_unlicensed_bundle_is_not_normalized(self):
        bundle,approval,form=fixture()
        approval["reviewer_confirmation"]="NOT_VERIFIED"
        with self.assertRaisesRegex(ValueError,"manually verified"):
            assemble(bundle,approval,form)
    def test_wrong_cutoff_query_does_not_create_pretip_sample(self):
        bundle,approval,form=fixture()
        bundle["pairs"][0]["with_provenance"]["request_params"]["ToDate"]="2026-11-08"
        with self.assertRaisesRegex(ValueError,"historical date"):
            assemble(bundle,approval,form)
    def test_missing_or_inconsistent_independent_stints_are_rejected(self):
        bundle,approval,form=fixture()
        bundle["pairs"][0].pop("target_distribution")
        with self.assertRaisesRegex(ValueError,"Missing independent"):
            assemble(bundle,approval,form)
        bundle,approval,form=fixture()
        bundle["pairs"][0]["teammate_distribution"][0]["Possessions"][0]["EndTime"]=600
        with self.assertRaisesRegex(ValueError,"exposure does not match"):
            assemble(bundle,approval,form)
        bundle,approval,form=fixture()
        bundle["pairs"][0]["without_provenance"]["game_dates"].pop()
        with self.assertRaisesRegex(ValueError,"do not match"):
            assemble(bundle,approval,form)

    def test_absent_game_provenance_is_not_inferred(self):
        bundle,approval,form=fixture()
        bundle["pairs"][0]["without_provenance"].pop("game_dates")
        with self.assertRaisesRegex(ValueError,"do not match"):
            assemble(bundle,approval,form)

if __name__=="__main__":unittest.main()
