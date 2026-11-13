import unittest
from research.source_def_rating_2026 import TEAMS,parse_csv,fetch

WHEN="2026-11-10T22:00:00Z"

def csv_data(*,bad_team=None,bad_rating=False):
    rows=["season,team,gp,def_rating_est,pace"]
    for i,(abbr,name) in enumerate(TEAMS.items()):
        key=bad_team if i==0 and bad_team is not None else abbr
        rating="0" if i==0 and bad_rating else str(108+i*.25)
        rows.append(f"2026-27,{key},11,{rating},{98+i*.1}")
    return "\n".join(rows)+"\n"

class DefensiveRatingSourceTests(unittest.TestCase):
    def test_full_current_season_and_correct_rating_metric(self):
        x=parse_csv(csv_data(),captured_at=WHEN)
        self.assertEqual(x["team_count"],30)
        self.assertEqual(x["teams"]["BOS"]["metric"],"ESTIMATED_POINTS_ALLOWED_PER_100_POSSESSIONS")
        self.assertEqual(x["teams"]["BOS"]["played_games"],11)
        self.assertFalse(x["production_approved"])
        self.assertFalse(x["historical_pretip_feature_backfill"])
    def test_source_time_is_observed_not_historical_pick_time(self):
        x=parse_csv(csv_data(),captured_at=WHEN)
        self.assertEqual(x["teams"]["ATL"]["observed_at"],WHEN)
        self.assertEqual(x["teams"]["ATL"]["source"],x["source_url"])
    def test_partial_or_invalid_rating_fails_closed(self):
        with self.assertRaises(ValueError):parse_csv(csv_data(bad_rating=True),captured_at=WHEN)
        with self.assertRaises(ValueError):parse_csv(csv_data(bad_team="SEA"),captured_at=WHEN)
    def test_incorrect_season_fails_closed(self):
        with self.assertRaises(ValueError):parse_csv(csv_data().replace("2026-27","2025-26"),captured_at=WHEN)
    def test_duplicate_team_fails_closed(self):
        text=csv_data()
        text=text.replace("2026-27,BOS,11,","2026-27,ATL,11,")
        with self.assertRaises(ValueError):parse_csv(text,captured_at=WHEN)
    def test_naive_capture_time_fails_closed(self):
        with self.assertRaises(ValueError):parse_csv(csv_data(),captured_at="2026-11-10T22:00:00")
    def test_request_is_injectable_without_any_paid_api(self):
        x=fetch(request=lambda url:csv_data(),captured_at=WHEN)
        self.assertEqual(x["team_count"],30)
if __name__=="__main__":unittest.main()
