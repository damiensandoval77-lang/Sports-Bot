"""Locked pregame minutes scenario evaluation invariants."""
import unittest
from iphone_bot.minutes_scenario_validation import snapshot,settle,report


START="2026-11-07T00:10:00+00:00"
CAPTURE="2026-11-06T22:55:00+00:00"
ISSUED="2026-11-06T22:45:00+00:00"


def fixture():
    injury={"status":"OFFICIAL_NBA_REPORT_VERIFIED","injury_data_verified":True,
            "report_issued_at":ISSUED,"source_pdf":"https://ak-static.cms.nba.com/injury.pdf",
            "players":[{"player_id":"8","team":"BOS","game_date":"2026-11-06","status":"Out"}]}
    scenario={"status":"HISTORICAL_SCENARIO_RESEARCH_ONLY",
              "baseline_minutes":30.0,"scenario_minutes":33.0,
              "teammate_id":"8","teammate":"Unavailable Teammate",
              "live_adjustment_applied":False}
    market={"player_id":"7","player":"Example Player","team":"BOS",
            "start":START,"game":"Boston Celtics @ Charlotte Hornets",
            "injury_minutes_research":scenario}
    comparisons={"status":"EXPERIMENTAL_NON_CALIBRATED","generated_at":CAPTURE,
                 "comparisons":[market,dict(market,stat="REB")]}
    return comparisons,injury


class MinutesScenarioValidationTest(unittest.TestCase):
    def test_pregame_snapshot_is_immutable_and_independent_of_stat(self):
        comp,inj=fixture()
        rows=snapshot(comp,inj)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["status"],"PENDING")
        changed,inj2=fixture()
        changed["comparisons"][0]["injury_minutes_research"]["scenario_minutes"]=45
        self.assertEqual(snapshot(changed,inj2,rows),rows)

    def test_no_retroactive_snapshot_or_late_injury_report(self):
        comp,inj=fixture()
        late=dict(comp,generated_at="2026-11-07T01:00:00+00:00")
        self.assertEqual(snapshot(late,inj),[])
        altered=dict(inj,report_issued_at="2026-11-06T23:05:00+00:00")
        self.assertEqual(snapshot(comp,altered),[])

    def test_team_date_and_source_required(self):
        comp,inj=fixture()
        for new in (dict(inj,status="THIRD_PARTY_ESPN_INJURY_CONTEXT"),
                    dict(inj,players=[dict(inj["players"][0],game_date="2026-11-07")]),
                    dict(inj,players=[dict(inj["players"][0],team="CHA")]),
                    dict(inj,players=[dict(inj["players"][0],status="Questionable")])):
            self.assertEqual(snapshot(comp,new),[])
        out_player=dict(inj,players=inj["players"]+[
            {"player_id":"7","game_date":"2026-11-06","team":"BOS","status":"Out"}])
        self.assertEqual(snapshot(comp,out_player),[])

    def test_settlement_after_buffer_requires_exact_game_team_opponent(self):
        comp,inj=fixture()
        rows=snapshot(comp,inj)
        actual={"id":"7","date":"2026-11-06","team":"BOS","opponent":"CHA","MIN":32}
        early=settle(rows,[actual],now="2026-11-07T02:00:00+00:00")
        self.assertEqual(early[0]["status"],"PENDING")
        wrong=settle(rows,[dict(actual,opponent="NYK")],now="2026-11-07T06:00:00+00:00")
        self.assertEqual(wrong[0]["status"],"PENDING")
        done=settle(rows,[actual],now="2026-11-07T06:00:00+00:00")
        self.assertEqual(done[0]["status"],"SETTLED")
        self.assertEqual(done[0]["baseline_abs_error"],2)
        self.assertEqual(done[0]["scenario_abs_error"],1)
        metrics=report(done,now="2026-11-07T06:01:00+00:00")["same_game_comparison"]
        self.assertEqual(metrics["scenario_minus_baseline_mae"],-1)
        self.assertEqual(metrics["scenario_better_games"],1)
        self.assertFalse(metrics["sufficient_sample"])

    def test_dnp_and_ambiguous_matches_do_not_fabricate_outcome(self):
        comp,inj=fixture()
        rows=snapshot(comp,inj)
        g={"id":"7","date":"2026-11-06","team":"BOS","opponent":"CHA","MIN":0}
        self.assertEqual(settle(rows,[g],now="2026-11-07T06:00:00+00:00")[0]["status"],"PENDING")
        self.assertEqual(settle(rows,[dict(g,MIN=30),dict(g,MIN=35)],now="2026-11-07T06:00:00+00:00")[0]["status"],"PENDING")


if __name__=="__main__":unittest.main()
