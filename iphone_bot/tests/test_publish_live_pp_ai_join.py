import datetime as dt
import unittest
from iphone_bot.publish_live_pp_ai_join import build
NOW=dt.datetime(2026,11,9,18,tzinfo=dt.timezone.utc)
TIP="2026-11-10T00:00:00+00:00"
STAMP="2026-11-09T17:50:00+00:00"
def data():
    pp={"status":"LIVE_THIRD_PARTY_PRIZEPICKS_LINES","generated_at":STAMP,
        "provider_status":"fresh","partial_board":True,"complete_provider_board":False,
        "board_offers":[{"id":"p-1","player":"Luka Dončić","team":"LAL",
            "opponent":"ATL","game":"Los Angeles Lakers @ Atlanta Hawks",
            "stat":"PTS","line":29.5,"starts_at":TIP,"observed_at":STAMP,
            "source":"independent_prizepicksapi_com","is_demo":False,
            "more_tier":"standard","less_tier":"standard"}]}
    ai={"status":"PREGAME_PROJECTIONS_NO_LINES","generated_at":STAMP,
        "predictions":[{"player_id":"123","player":"Luka Doncic","team":"LAL",
            "game":"Los Angeles Lakers @ Atlanta Hawks","start":TIP,
            "stat":"PTS","projection":31.0,"line":None,"direction":None,
            "is_pregame_prediction":True}]}
    roster={"season":"2026-27","players":[{"player_id":"123",
               "player":"Luka Dončić","team":"LAL"}]}
    return pp,ai,roster

class QuickJoinTests(unittest.TestCase):
    def test_genuine_matching_name_diacritics_and_line(self):
        pp,ai,form=data()
        out=build(pp,ai,form,now=NOW)
        self.assertEqual(out["offers_matched"],1)
        row=out["comparisons"][0]
        self.assertEqual(row["ai_direction"],"MORE")
        self.assertEqual(row["difference"],1.5)
        self.assertTrue(row["research_only"])
        self.assertIsNone(row["confidence_percent"])
        self.assertIsNone(row["odds"])
        self.assertFalse(row["reliability_screen"]["validated"])
    def test_stale_provider_fails_closed(self):
        pp,ai,form=data()
        pp["generated_at"]="2026-11-09T15:00:00Z"
        out=build(pp,ai,form,now=NOW)
        self.assertEqual(out["status"],"STALE_OR_UNVERIFIED_SOURCE")
        self.assertEqual(out["comparisons"],[])
    def test_stale_model_fails_closed(self):
        pp,ai,form=data()
        ai["generated_at"]="2026-11-09T12:00:00Z"
        self.assertEqual(build(pp,ai,form,now=NOW)["offers_matched"],0)
    def test_started_and_demo_or_ambiguous_not_accepted(self):
        for change in ({"starts_at":"2026-11-09T16:00:00Z"},
                       {"is_demo":True},{"opponent":"BOS"}):
            pp,ai,form=data()
            pp["board_offers"][0].update(change)
            self.assertEqual(build(pp,ai,form,now=NOW)["offers_matched"],0)
        pp,ai,form=data()
        form["players"].append({"player_id":"999","player":"Luka Doncic","team":"LAL"})
        self.assertEqual(build(pp,ai,form,now=NOW)["offers_matched"],0)
    def test_only_two_sided_standard_quotes_enter_any_comparison(self):
        for more,less in (("demon","demon"),("goblin","goblin"),
                          ("standard",None),("demon","standard"),(None,"standard")):
            with self.subTest(more=more,less=less):
                pp,ai,form=data()
                pp["board_offers"][0]["more_tier"]=more
                pp["board_offers"][0]["less_tier"]=less
                report=build(pp,ai,form,now=NOW)
                self.assertEqual(report["offers_matched"],0)
                self.assertEqual(report["skipped_reasons"].get("not_two_sided_standard_line"),1)
        pp,ai,form=data()
        self.assertEqual(build(pp,ai,form,now=NOW)["offers_matched"],1)

    def test_roster_player_id_must_agree_with_ai_player_id(self):
        pp,ai,form=data()
        ai["predictions"][0]["player_id"]="999999"
        report=build(pp,ai,form,now=NOW)
        self.assertEqual(report["offers_matched"],0)
        self.assertEqual(report["skipped_reasons"].get("roster_player_id_mismatch"),1)

    def test_unmatched_forecast_does_not_invent_pick(self):
        pp,ai,form=data()
        ai["predictions"]=[]
        self.assertEqual(build(pp,ai,form,now=NOW)["status"],"NO_MATCHED_UPCOMING_MARKETS")
    def test_duplicate_forecast_not_silently_chosen(self):
        pp,ai,form=data()
        ai["predictions"].append({**ai["predictions"][0],"projection":40})
        self.assertEqual(build(pp,ai,form,now=NOW)["offers_matched"],0)
    def test_compact_health_manifest_is_generated_without_relying_on_large_file_reader(self):
        import json, tempfile
        from pathlib import Path
        from unittest.mock import patch
        import iphone_bot.publish_live_pp_ai_join as app
        pp,ai,form=data()
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            for filename,value in (("provider.json",pp),("ai.json",ai),("form.json",form)):
                (folder/filename).write_text(json.dumps(value))
            with patch.object(app,"SOURCE",folder/"provider.json"), patch.object(app,"AI",folder/"ai.json"), patch.object(app,"FORM",folder/"form.json"), patch.object(app,"OUT",folder/"large.json"), patch.object(app,"HEALTH",folder/"health.json"):
                # Use the production main implementation; its result may be empty if
                # actual clock differs from the fixture. The health report must still exist.
                try:app.main()
                except SystemExit:pass
            report=json.loads((folder/"health.json").read_text())
            self.assertIn("offers_matched",report)
            self.assertIn("matched_by_game",report)
            self.assertNotIn("comparisons",report)
            self.assertTrue(report["research_only"])

    def test_overlays_existing_model_without_odds_or_probability(self):
        pp,ai,form=data()
        pp["board_offers"].append({**pp["board_offers"][0],"id":"p-2","line":30.5})
        out=build(pp,ai,form,now=NOW)
        self.assertEqual(out["offers_matched"],2)
        self.assertEqual(out["matched_games"],1)
        self.assertTrue(all(p["confidence_percent"] is None for p in out["comparisons"]))

if __name__=="__main__":unittest.main()
