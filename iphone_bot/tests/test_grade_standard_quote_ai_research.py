import datetime as dt
import unittest
from iphone_bot.archive_standard_quote_ai_research import merge
from iphone_bot.grade_standard_quote_ai_research import reconcile

PRETIP=dt.datetime(2026,11,10,18,tzinfo=dt.timezone.utc)
POST=dt.datetime(2026,11,11,6,tzinfo=dt.timezone.utc)
def receipt(**changes):
    original={
        "source":"independent_prizepicksapi_com","provider_projection_id":"pp1",
        "player":"Sample","player_id":"123","team":"BOS",
        "opponent":"PHI","game":"Boston Celtics @ Philadelphia 76ers",
        "start":"2026-11-11T01:00:00+00:00","stat":"PTS",
        "line":24.5,"projection":27.1,"ai_direction":"MORE",
        "observed_at":"2026-11-10T17:15:00+00:00",
        "model_generated_at":"2026-11-10T16:00:00+00:00",
        "more_tier":"standard","less_tier":"standard",
        "research_only":True,"confidence_percent":None,"estimated_ev":None,
        "reliability_screen":{"validated":False}}
    original.update(changes)
    return original

def archive(*rows):
    return merge({"status":"FRESH_RESEARCH_ONLY_PRIZEPICKS_AI_COMPARISONS","comparisons":list(rows)},
                 now=PRETIP)

def final(actual=26,status="GRADED",source="NBA_CDN_FINAL",**change):
    row={"status":status,"final_source":source,"source_game_id":"0022600300",
         "player_id":"123","team":"BOS","game":"Boston Celtics @ Philadelphia 76ers",
         "start":"2026-11-11T01:00:00+00:00","stat":"PTS","actual":actual}
    row.update(change)
    return row

class FinalResearchTests(unittest.TestCase):
    def test_only_verified_final_after_tip_can_settle(self):
        a=archive(receipt())
        self.assertEqual(reconcile(a,{"records":[final()]},now=PRETIP)["records"][0]["grade"],"UNSETTLED_RESEARCH")
        b=reconcile(a,{"records":[final()]},now=POST)
        self.assertEqual(b["records"][0]["grade"],"HIT")
        self.assertEqual(b["research_directional_hit_rate"],1)
        self.assertEqual(b["records"][0]["line"],24.5)
        self.assertEqual(b["records"][0]["projection"],27.1)

    def test_push_void_and_wrong_side(self):
        base=archive(receipt())
        self.assertEqual(reconcile(base,{"records":[final(24.5)]},now=POST)["records"][0]["grade"],"PUSH")
        self.assertEqual(reconcile(base,{"records":[final(22)]},now=POST)["records"][0]["grade"],"MISS")
        self.assertEqual(reconcile(base,{"records":[final(status="EXCLUDED_VERIFIED_DNP",source="NBA_OFFICIAL_INACTIVE_CROSSCHECKED",actual=None)]},now=POST)["records"][0]["grade"],"VOID")

    def test_identity_and_source_mismatches_remain_unsettled(self):
        a=archive(receipt())
        for bad in (
            final(source="UNVERIFIED"),
            final(player_id="another"),
            final(game="wrong"),
            final(stat="AST"),
            final(source_game_id=None),
        ):
            self.assertEqual(reconcile(a,{"records":[bad]},now=POST)["records"][0]["grade"],"UNSETTLED_RESEARCH")

    def test_conflicting_final_stats_quarantined(self):
        a=archive(receipt())
        b=reconcile(a,{"records":[final(28),final(29)]},now=POST)
        self.assertEqual(b["records"][0]["grade"],"UNSETTLED_RESEARCH")

    def test_repeated_grading_is_idempotent_and_no_stale_overwrite(self):
        original=archive(receipt())
        graded=reconcile(original,{"records":[final(26)]},now=POST)
        replay=reconcile(graded,{"records":[]},now=POST)
        self.assertEqual(replay["records"][0]["grade"],"HIT")
        self.assertEqual(replay["research_directional_sample"],1)
        self.assertEqual(replay["records"][0]["source_snapshot"],original["records"][0]["source_snapshot"])
        self.assertEqual(replay["research_grading_checked_at"],graded["research_grading_checked_at"])
        self.assertEqual(replay,graded)

    def test_alternate_tier_cannot_become_grading_receipt(self):
        original=archive(receipt())
        original["records"][0]["more_tier"]="demon"
        with self.assertRaises(ValueError):
            reconcile(original,{"records":[final()]},now=POST)

if __name__=="__main__":
    unittest.main()
