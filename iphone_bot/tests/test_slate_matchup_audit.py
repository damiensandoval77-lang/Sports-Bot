import unittest
from iphone_bot.slate_matchup_audit import coverage

def example():
    slate = {"dates_eastern": ["2026-11-09"],"source":"fixture",
             "games":[{"game":"Indiana Pacers @ Dallas Mavericks","date_eastern":"2026-11-09","game_state":"pre"},
                      {"game":"Los Angeles Lakers @ Atlanta Hawks","date_eastern":"2026-11-09","game_state":"in"},
                      {"game":"Boston Celtics @ Philadelphia 76ers","date_eastern":"2026-11-10","game_state":"pre"}]}
    return slate

class SlateMatchupAuditTests(unittest.TestCase):
    def test_missing_dallas_named_without_inventing_lines(self):
        result=coverage(example(),{"events_covered":[{"game":"Los Angeles Lakers @ Atlanta Hawks"}]},"2026-11-09")
        self.assertEqual(result["missing_game_names"],["Indiana Pacers @ Dallas Mavericks"])
        self.assertFalse(result["coverage_complete"])

    def test_complete_matching(self):
        rows=[{"game":g["game"]} for g in example()["games"][:2]]
        result=coverage(example(),{"events_covered":rows},"2026-11-09")
        self.assertTrue(result["coverage_complete"])

    def test_no_games_on_valid_date(self):
        s=example()
        s["games"]=[]
        self.assertTrue(coverage(s,{"events_covered":[]},"2026-11-09")["coverage_complete"])

    def test_stale_schedule_date_is_not_success(self):
        self.assertFalse(coverage(example(),{},"2026-11-11")["coverage_complete"])

    def test_completed_games_not_missing(self):
        s=example()
        s["games"][0]["game_state"]="post"
        r=coverage(s,{"events_covered":[{"game":"Los Angeles Lakers @ Atlanta Hawks"}]},"2026-11-09")
        self.assertTrue(r["coverage_complete"])

    def test_whitespace_case_normalization(self):
        r=coverage(example(),{"events_covered":[{"game":"  INDIANA  pacers @ Dallas Mavericks"},
                                                {"game":"Los Angeles Lakers @ Atlanta Hawks"}]},"2026-11-09")
        self.assertTrue(r["coverage_complete"])

if __name__=="__main__":
    unittest.main()
