import datetime as dt
import unittest
from iphone_bot.archive_prizepicks_pregame_lines import build, safe_row,STATUS

NOW=dt.datetime(2026,11,10,0,30,tzinfo=dt.timezone.utc)
def line(**overrides):
    row={"id":"pp_123","player":"Test Player","team":"WAS",
         "game":"Washington Wizards @ Detroit Pistons","stat":"PTS","line":15.5,
         "starts_at":"2026-11-10T00:00:00Z","observed_at":"2026-11-09T23:54:00Z",
         "more_tier":"standard","less_tier":"standard",
         "source":"independent_prizepicksapi_com","is_demo":False}
    return {**row,**overrides}

def board(**overrides):
    return {"status":"LIVE_THIRD_PARTY_PRIZEPICKS_LINES",
            "source":"independent_prizepicksapi_com",
            "generated_at":"2026-11-09T23:58:00Z",
            "board_offers":[line()],**overrides}

class ObservedPregameArchiveTests(unittest.TestCase):
    def test_saved_before_tip_is_persisted(self):
        out=build(board(),now=NOW)
        self.assertEqual(out["status"],STATUS)
        self.assertEqual(out["count"],1)
        self.assertEqual(out["quotes"][0]["line"],15.5)
        self.assertEqual(out["quotes"][0]["tier"],"standard")
    def test_verified_day_ahead_standard_lines_are_not_dropped_before_tip(self):
        # Six-hour cutoff silently lost the afternoon's genuine lines.
        early=board(generated_at="2026-11-09T17:00:00Z",
                    board_offers=[line(starts_at="2026-11-10T00:30:00Z",
                                       observed_at="2026-11-09T16:55:00Z")])
        result=build(early,now=dt.datetime(2026,11,9,17,1,tzinfo=dt.timezone.utc))
        self.assertEqual(result["count"],1)
        self.assertEqual(result["quotes"][0]["tier"],"standard")
        too_early=board(generated_at="2026-11-08T17:00:00Z",
                    board_offers=[line(starts_at="2026-11-10T00:30:00Z",
                                       observed_at="2026-11-08T16:55:00Z")])
        self.assertEqual(build(too_early,now=dt.datetime(2026,11,8,17,1,tzinfo=dt.timezone.utc))["count"],0)

    def test_later_post_tip_source_cannot_erase_old_capture(self):
        old=build(board(),now=NOW)
        newer=board(generated_at="2026-11-10T00:20:00Z",
                    board_offers=[line(observed_at="2026-11-10T00:19:00Z",line=21.5)])
        out=build(newer,old,now=NOW)
        self.assertEqual(out["count"],1)
        self.assertEqual(out["quotes"][0]["line"],15.5)
    def test_provider_outage_keeps_pretip_archive(self):
        old=build(board(),now=NOW)
        self.assertEqual(build({},old,now=NOW)["quotes"],old["quotes"])
    def test_reject_invalid_or_post_tip_observation(self):
        for bad in [line(is_demo=True),line(source="unverified"),line(less_tier=None),
                    line(observed_at="2026-11-10T00:03:00Z"),line(line=-4),
                    line(starts_at="2026-11-09T18:00:00Z"),
                    line(more_tier="demon",less_tier="goblin")]:
            self.assertEqual(build(board(board_offers=[bad]),now=NOW)["count"],0)
    def test_conflicting_same_tier_refuses_promotion(self):
        self.assertEqual(build(board(board_offers=[line(),line(id="different",line=18.5)]),
                               now=NOW)["count"],0)
    def test_do_not_keep_forever(self):
        ancient=NOW+dt.timedelta(days=15)
        old=build(board(),now=NOW)
        self.assertEqual(build({},old,now=ancient)["count"],0)
if __name__=="__main__":unittest.main()
