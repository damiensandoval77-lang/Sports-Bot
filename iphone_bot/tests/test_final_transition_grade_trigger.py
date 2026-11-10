import unittest
from iphone_bot.final_transition_grade_trigger import new_finals

def snapshot(state="post",seen="2026-11-10T03:00:00+00:00",**change):
    return {"status":"OBSERVED_ESPN_LIVE_BOX_SCORES_SERVER_FALLBACK",
            "date_eastern":"2026-11-09","captured_at":seen,
            "games":[{"game":"Cleveland Cavaliers @ Charlotte Hornets",
                      "event_id":"401909953","state":state,"stale":False,
                      "observed_at":seen,
                      "player_rows":[{"player":"Example","PTS":12}],**change}]}
class FinalTransitionTests(unittest.TestCase):
    def test_first_transition_dispatches_once(self):
        previous=snapshot("in",seen="2026-11-10T02:50:00+00:00")
        current=snapshot("post")
        self.assertEqual(new_finals(current,previous),["401909953"])
        self.assertEqual(new_finals(snapshot("post",seen="2026-11-10T03:05:00+00:00"),current),[])
    def test_never_dispatches_from_live_or_stale_rows(self):
        self.assertEqual(new_finals(snapshot("in"),{}),[])
        self.assertEqual(new_finals(snapshot(stale=True),{}),[])
        self.assertEqual(new_finals(snapshot(observed_at="2026-11-10T02:30:00+00:00"),{}),[])
        self.assertEqual(new_finals(snapshot(player_rows=[]),{}),[])
    def test_stale_or_other_date_prior_does_not_suppress_valid_new_final(self):
        prior=snapshot("post",seen="2026-11-09T03:00:00+00:00")
        prior["date_eastern"]="2026-11-08"
        self.assertEqual(new_finals(snapshot(),prior),["401909953"])
    def test_no_final_grades_or_player_values_emitted(self):
        self.assertEqual(new_finals(snapshot(),{}),["401909953"])
if __name__=="__main__":unittest.main()
