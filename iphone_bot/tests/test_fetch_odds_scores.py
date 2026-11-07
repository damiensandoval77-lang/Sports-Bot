"""Strict source-linked NBA score tests, no invented zeros or scores."""
import datetime as dt
import unittest
from iphone_bot.fetch_odds_scores import numeric_score,parse_game,build_feed


def source(scores=None,completed=False,id="fixture1",start="2026-11-07T00:10:00Z"):
    return {"id":id,"home_team":"Charlotte Hornets","away_team":"Boston Celtics",
            "commence_time":start,"completed":completed,"scores":scores,
            "last_update":"2026-11-07T00:32:00Z"}


class ScoresTests(unittest.TestCase):
    def test_live_scores_are_matched_to_team_names_not_array_order(self):
        r=parse_game(source([
            {"name":"Charlotte Hornets","score":"101"},
            {"name":"Boston Celtics","score":"99"}]))
        self.assertEqual(r["game_state"],"in")
        self.assertEqual((r["away_score"],r["home_score"]),(99,101))
        self.assertEqual(r["score_updated_at"],"2026-11-07T00:32:00+00:00")

    def test_completed_game_can_have_final_scores(self):
        r=parse_game(source([
            {"name":"Boston Celtics","score":"123"},
            {"name":"Charlotte Hornets","score":"110"}],completed=True))
        self.assertEqual(r["game_state"],"post")
        self.assertEqual(r["away_score"],123)

    def test_missing_partial_and_invalid_scores_do_not_create_zero(self):
        partial=source([{"name":"Boston Celtics","score":"99"}])
        r=parse_game(partial)
        self.assertIsNone(r["away_score"])
        self.assertIsNone(r["home_score"])
        self.assertEqual(r["game_state"],"unknown")
        invalid=source([{"name":"Boston Celtics","score":"100"},
                        {"name":"Charlotte Hornets","score":"NaN"}])
        r=parse_game(invalid)
        self.assertIsNone(r["away_score"])
        self.assertIsNone(r["home_score"])
        self.assertIsNone(numeric_score(True))
        self.assertIsNone(numeric_score(-1))
        self.assertIsNone(numeric_score("Inf"))

    def test_published_schedule_is_never_claimed_complete(self):
        now=dt.datetime(2026,11,7,0,40,tzinfo=dt.timezone.utc)
        result=build_feed([source()],now)
        self.assertEqual(result["total_games"],1)
        self.assertEqual(result["games"][0]["date_eastern"],"2026-11-06")
        self.assertFalse(result["coverage_complete"])
        self.assertFalse(result["has_sportsbook_props"])
        self.assertFalse(result["has_verified_player_availability"])

    def test_does_not_duplicate_games_and_rejects_malformed(self):
        now=dt.datetime(2026,11,7,0,40,tzinfo=dt.timezone.utc)
        r=build_feed([source(),source(),{"id":"bad"}],now)
        self.assertEqual(r["total_games"],1)
        self.assertEqual(r["source_records_rejected"],1)


if __name__=="__main__":unittest.main()
