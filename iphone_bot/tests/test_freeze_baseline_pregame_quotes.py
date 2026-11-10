import copy,datetime as dt,unittest
from iphone_bot.freeze_baseline_pregame_quotes import freeze,STATUS
from iphone_bot.grade_frozen_baseline_join import grade
NOW=dt.datetime(2026,11,10,1,40,tzinfo=dt.timezone.utc)
GAME={"game":"San Antonio Spurs @ Phoenix Suns","start":"2026-11-10T02:00:00Z",
 "date_eastern":"2026-11-09","home_abbreviation":"PHX","away_abbreviation":"SAS"}
SC={"coverage_complete":True,"games":[GAME]}
AI={"status":"IMMUTABLE_OBSERVED_PRETIP_NOLINE_AI_ARCHIVE",
 "predictions":[{"player":"Devin Booker","player_id":"x1","team":"PHX",
    "game":GAME["game"],"stat":"PTS","start":GAME["start"],
    "projection":23.3,"line":None,"calibrated_probability":None,
    "is_pregame_prediction":True,"captured_at":"2026-11-09T20:00:00Z"}]}
Q={"status":"VERIFIED_PRETIP_PRIZEPICKS_QUOTES_ARCHIVE",
 "quotes":[{"id":"pp_real","player":"Devin Booker","team":"PHX","game":GAME["game"],
 "stat":"PTS","starts_at":GAME["start"],"line":24.5,"tier":"standard",
 "more_tier":"standard","less_tier":"standard",
 "observed_at":"2026-11-10T01:31:00Z",
 "source_generated_at":"2026-11-10T01:32:00Z",
 "source":"independent_prizepicksapi_com","is_demo":False}]}
class FreezeBaselineTests(unittest.TestCase):
 def test_eligible_source_quotes_are_locked_once(self):
    first=freeze({},Q,AI,SC,now=NOW)
    self.assertEqual(first["status"],STATUS)
    self.assertEqual(first["record_count"],1)
    self.assertEqual(first["records"][0]["line"],24.5)
    self.assertEqual(first["records"][0]["model_projection"],23.3)
    self.assertTrue(first["records"][0]["not_a_wager"])
    moved=copy.deepcopy(Q);moved["quotes"][0]["line"]=26.5
    newer=freeze(first,moved,AI,SC,now=NOW+dt.timedelta(minutes=1))
    self.assertEqual(newer["new_pretip_locks"],0)
    self.assertEqual(newer["records"][0],first["records"][0])
 def test_after_tip_does_not_backfill_missing_records(self):
    out=freeze({},Q,AI,SC,now=NOW+dt.timedelta(minutes=22))
    self.assertEqual(out["record_count"],0)
 def test_prior_locked_capture_survives_provider_outage(self):
    old=freeze({},Q,AI,SC,now=NOW)
    with self.assertRaises(ValueError):
        freeze(old,{"status":"UNVERIFIED","quotes":[]},AI,SC,now=NOW)
    # No invalid new snapshot is published. Retain last-good old object.
    self.assertEqual(old["record_count"],1)
 def test_wrong_team_tier_or_posttip_observation_never_frozen(self):
    for diff in ({"team":"GSW"},{"tier":"demon","more_tier":"demon","less_tier":"demon"},
                 {"observed_at":"2026-11-10T02:01:00Z"},
                 {"source":"unverified"},{"is_demo":True}):
        wrong=copy.deepcopy(Q);wrong["quotes"][0].update(diff)
        self.assertEqual(freeze({},wrong,AI,SC,now=NOW)["record_count"],0)
 def test_same_automatic_snapshot_is_gradeable_only_on_verified_final(self):
    snapshot=freeze({},Q,AI,SC,now=NOW)
    cold=grade(snapshot,{"records":[]})
    self.assertEqual(cold["pending"],1)
    r=snapshot["records"][0]
    valid={k:r[k] for k in ("player_id","team","game","start","stat")}
    valid.update({"status":"GRADED","actual":27,
       "final_source":"ESPN_FINAL","source_game_id":"0022601001"})
    completed=grade(snapshot,{"records":[valid]})
    self.assertEqual(completed["verified_final_grades"],1)
    self.assertEqual(completed["pending"],0)
    self.assertEqual(snapshot["records"][0]["grade"],"PENDING")
 def test_no_duplicated_identity(self):
    q=copy.deepcopy(Q);q["quotes"]=[Q["quotes"][0],copy.deepcopy(Q["quotes"][0])]
    out=freeze({},q,AI,SC,now=NOW)
    self.assertEqual(out["record_count"],1)
if __name__=="__main__":unittest.main()
