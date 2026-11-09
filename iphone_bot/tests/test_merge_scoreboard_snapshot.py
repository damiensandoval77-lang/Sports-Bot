import unittest
from iphone_bot.merge_scoreboard_snapshot import select

def row(stamp,status="OBSERVED_NBA_LIVE_SCOREBOARD",day="2026-11-09"):
    return {"generated_at":stamp,"status":status,"dates_eastern":[day],
            "games":[{"game":"A @ B","home_score":10,"away_score":12}]}
class ScoreboardMergeTests(unittest.TestCase):
    def test_newer_live_replaces_old_schedule(self):
        old=row("2026-11-09T13:00:00Z","NBA_CDN_SCHEDULE_FALLBACK_NOT_CONFIRMED_LIVE")
        new=row("2026-11-09T14:00:00Z")
        self.assertIs(select(old,new),new)
    def test_older_fallback_does_not_replace_newer_live(self):
        old=row("2026-11-09T14:00:00Z")
        new=row("2026-11-09T13:00:00Z","NBA_CDN_SCHEDULE_FALLBACK_NOT_CONFIRMED_LIVE")
        self.assertIs(select(old,new),old)
    def test_same_timestamp_preserves_real_scores(self):
        old=row("2026-11-09T14:00:00Z")
        new=row("2026-11-09T14:00:00Z","NBA_CDN_SCHEDULE_FALLBACK_NOT_CONFIRMED_LIVE")
        self.assertIs(select(old,new),old)
    def test_next_day_replaces_yesterday(self):
        old=row("2026-11-09T23:00:00Z",day="2026-11-08")
        new=row("2026-11-10T00:00:00Z",day="2026-11-09")
        self.assertIs(select(old,new),new)
    def test_empty_provider_response_cannot_erase_games(self):
        old=row("2026-11-09T14:00:00Z")
        self.assertIs(select(old,{"status":"UNAVAILABLE_UPSTREAM_ERROR","games":[]}),old)
    def test_missing_current_can_accept_valid_candidate(self):
        new=row("2026-11-09T14:00:00Z")
        self.assertIs(select({},new),new)

if __name__=="__main__":
    unittest.main()
