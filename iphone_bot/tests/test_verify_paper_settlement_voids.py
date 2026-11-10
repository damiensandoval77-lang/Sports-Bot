import unittest
from iphone_bot.verify_paper_settlement_voids import verify

def void():
    return {"status":"VOID_DNP","result":"VOID","void_reason":"INACTIVE",
            "void_source_url":"https://www.nba.com/game/0022600030",
            "void_recorded_at":"2026-11-10T05:00:00+00:00"}

class FinalVoidTests(unittest.TestCase):
    def test_provenance_verified_voids_are_accounted_but_not_graded(self):
        rows=[void(),{"status":"SETTLED","result":"WIN"},{"status":"PENDING"}]
        result=verify(rows,{"void_dnp":1})
        self.assertEqual(result["VOID_DNP"],1)
        self.assertEqual(result["SETTLED"],1)
    def test_player_page_void_is_valid_only_when_exact_manual_fixture_matches(self):
        fixture={"status":"MANUALLY_VERIFIED_DNP_FROM_PUBLISHED_TEAM_OR_NBA_REPORTS",
            "records":[{"date_eastern":"2026-11-07",
              "game":"Washington Wizards @ Oklahoma City Thunder",
              "team":"WAS","player_id":"203076","player":"Anthony Davis",
              "source_url":"https://www.nba.com/wizards/player/203076/anthony_davis",
              "reason":"Ankle injury; NBA Wizards player update confirms ruled out Saturday"}]}
        row={**void(),"event_start":"2026-11-08T01:00:00Z",
            "captured_at":"2026-11-07T19:00:00Z",
            "game":"Washington Wizards @ Oklahoma City Thunder",
            "team":"WAS","player_id":"203076","player":"Anthony Davis",
            "void_source_url":fixture["records"][0]["source_url"],
            "void_reason":fixture["records"][0]["reason"]}
        self.assertEqual(verify([row],{"void_dnp":1},fixture)["VOID_DNP"],1)
        for change in [{"game":"Another matchup"},{"team":"BOS"},
                       {"player":"Another Davis"},{"player_id":"999"},
                       {"void_reason":"Claim without matching fixture"},
                       {"captured_at":"2026-11-08T02:00:00Z"}]:
            with self.subTest(change=change):
                with self.assertRaisesRegex(ValueError,"NBA_DNP_VOID_MISSING"):
                    verify([{**row,**change}],{"void_dnp":1},fixture)
    def test_mismatched_void_count_is_not_ignored(self):
        with self.assertRaisesRegex(ValueError,"NBA_DNP_VOID_COUNT_MISMATCH"):
            verify([void()],{"void_dnp":0})
    def test_undocumented_void_is_rejected(self):
        for changes in [
            {"result":"LOSS"},
            {"void_reason":""},
            {"void_source_url":"https://example.com/anything"},
            {"void_source_url":"https://www.nba.com/game/"},
            {"void_recorded_at":None},
        ]:
            with self.subTest(changes=changes):
                with self.assertRaises(ValueError):
                    verify([{**void(),**changes}],{"void_dnp":1})
    def test_unknown_status_does_not_pass(self):
        with self.assertRaisesRegex(ValueError,"UNKNOWN_FROZEN_STATUS"):
            verify([{"status":"VOID_UNVERIFIED"}],{"void_dnp":0})
    def test_missing_timezone_does_not_pass(self):
        with self.assertRaisesRegex(ValueError,"NBA_DNP_VOID_MISSING_RECORD_TIMESTAMP"):
            verify([{**void(),"void_recorded_at":"2026-11-10T05:00:00"}],{"void_dnp":1})
if __name__=="__main__":unittest.main()
