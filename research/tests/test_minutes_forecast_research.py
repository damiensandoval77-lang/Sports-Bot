"""Tests prove no target-date leakage, source freshness and honest fallback."""
import copy
import unittest
from datetime import date
from research.minutes_forecast_research import parse_logs, predict, evaluate, prospective

FIELDS=["date","opponent","PTS","MIN"]
def person(values=None):
    values=values or [21,23,25,27,29,31,32,33,30,29,35]
    return {"player_id":"1","team":"BOS","player":"Test",
      "log":[[f"2026-10-{idx+1:02d}","NYK",10,v] for idx,v in enumerate(values)]}
def form():
    return {"updated_at":"2026-11-11T02:00:00Z","log_fields":FIELDS,
            "players":[person()]}
def evidence():
    return {"status":"SOURCE_LINKED_PREGAME_RESEARCH_ONLY",
            "captured_at":"2026-11-11T03:00:00Z",
            "future_games":[{"game_id":"gameA"}],
            "research_players":[{"game_id":"gameA","player_id":"1","team":"BOS",
            "opponent":"NYK","date_eastern":"2026-11-11",
            "start":"2026-11-12T00:00:00Z","minutes_source":"https://source.example/log",
            "minutes_source_published_at":"2026-11-11T02:00:00Z",
            "injury_status":"UNKNOWN_NOT_LISTED"}]}

class ForecastTests(unittest.TestCase):
    def test_research_minutes_is_not_a_production_hit_estimate(self):
        output=prospective(form(), evidence())
        self.assertEqual(output["prediction_count"],1)
        row=output["predictions"][0]
        self.assertFalse(row["production_approved"])
        self.assertFalse(row["matchup_hit_estimate_eligible"])
        self.assertTrue(row["unknown_injury_status"])
        self.assertEqual(row["model_id"],"NBA_MINUTES_L5_SHRUNK_V1_RESEARCH")

    def test_target_game_cannot_leak_into_pregame_features(self):
        p=person()
        p["log"].append(["2026-11-11","NYK",10,46])
        with self.assertRaises(ValueError):
            parse_logs(p,FIELDS,date(2026,11,11))

    def test_duplicate_player_dates_fail_closed(self):
        p=person()
        p["log"].append(p["log"][0])
        with self.assertRaises(ValueError):
            parse_logs(p,FIELDS,date.max)

    def test_future_published_form_rejected(self):
        f=form()
        f["updated_at"]="2026-11-11T04:00:00Z"
        with self.assertRaises(ValueError):prospective(f,evidence())

    def test_missing_minutes_observations_rejected(self):
        f=form()
        f["players"][0]["log"]=f["players"][0]["log"][:2]
        self.assertEqual(prospective(f,evidence())["prediction_count"],0)

    def test_official_out_or_doubtful_suppressed(self):
        for status in ("Out","Doubtful"):
            e=evidence()
            e["research_players"][0]["injury_status"]=status
            self.assertEqual(prospective(form(),e)["prediction_count"],0)

    def test_available_does_not_mean_calibrated(self):
        e=evidence()
        e["research_players"][0]["injury_status"]="Available"
        row=prospective(form(),e)["predictions"][0]
        self.assertFalse(row["production_approved"])

    def test_source_version_mismatch_rejected(self):
        e=evidence()
        e["research_players"][0]["minutes_source_published_at"]="2026-11-10T02:00:00Z"
        self.assertEqual(prospective(form(),e)["prediction_count"],0)

    def test_duplicate_identity_rejected(self):
        f=form()
        f["players"].append(copy.deepcopy(f["players"][0]))
        self.assertEqual(prospective(f,evidence())["prediction_count"],0)

    def test_walk_forward_evaluation_no_random_holdout(self):
        results=evaluate(form())
        self.assertGreater(results["samples"],0)
        self.assertFalse(results["production_approved"])
        self.assertFalse(results["prospective_snapshot_validation"])
        self.assertEqual(set(results["candidate_metrics"]),{"last3","last5","shrunk_last5"})

    def test_latest_outcome_changes_metrics_but_cannot_change_prior_window(self):
        f=form()
        before=parse_logs(f["players"][0],FIELDS,date.max)
        before_prediction=predict(before[:-1])
        f["players"][0]["log"][-1][-1]=45
        after=parse_logs(f["players"][0],FIELDS,date.max)
        self.assertEqual(before_prediction,predict(after[:-1]))

    def test_zero_minute_dnp_not_assumed_played(self):
        p=person([0,0,21,22,23,24,25,26])
        hist=parse_logs(p,FIELDS,date.max)
        self.assertEqual(len(hist),6)

    def test_corrupt_minutes_fail_closed(self):
        for value in (-1,61,True,float("nan")):
            p=person()
            p["log"][0][-1]=value
            with self.assertRaises(ValueError):parse_logs(p,FIELDS,date.max)

if __name__=="__main__":
    unittest.main()
