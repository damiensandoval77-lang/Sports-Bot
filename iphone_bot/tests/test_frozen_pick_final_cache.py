import copy
import datetime as dt
import unittest
from iphone_bot.frozen_pick_final_cache import augment_final_outcomes
from iphone_bot.multimarket_forecast_ledger import merge
from iphone_bot.merge_new_ai_publishing import durable_merge
from iphone_bot.published_pick_settlement import evaluate

PICK={"player":"Scottie Barnes","player_id":"1630567","team":"TOR","opponent":"NYK",
      "game":"New York Knicks @ Toronto Raptors","start":"2026-11-15T23:00:00+00:00",
      "stat":"PTS","line":17.5,"projection":23.859,"grade":"PENDING",
      "market_updated":"2026-11-15T21:50:01+00:00","captured_at":"2026-11-15T21:56:14+00:00",
      "pickem_tier":"standard","standard_line_two_sided_verified":True,"research_only":True,
      "calibrated_probability":None,"estimated_hit_chance":{"modeled_direction":"More"}}
ROW={"player":"Scottie Barnes","nba_person_id":"1630567","team":"TOR","opponent":"NYK",
     "date":"2026-11-15","source":"NBA_CDN_FINAL","source_game_id":"0022600241",
     "final_confirmed":True,"PTS":30,"REB":9,"AST":4,"PRA":43,"MIN":36.3167}
def ledger(*rows): return {"status":"FROZEN_NEW_AI_ALL_MARKET","records":list(rows)}
class FrozenFinalCacheTests(unittest.TestCase):
    def test_missing_other_model_forecast_settles_original_picks_and_reconciles(self):
        original=ledger(PICK,{**PICK,"stat":"PRA","line":29.5,"projection":36.814})
        before=copy.deepcopy(original)
        finals={"records":[]}
        outcomes=augment_final_outcomes(original,finals,[ROW])
        self.assertEqual(finals,{"records":[]})
        self.assertEqual(original,before)
        self.assertEqual(len(outcomes["records"]),2)
        now=dt.datetime(2026,11,16,12,tzinfo=dt.timezone.utc)
        self.assertEqual(evaluate(original,outcomes,now)["actionable_verified_finals"],2)
        graded=merge(original,{},outcomes)
        durable=durable_merge(original,graded,outcomes)
        self.assertEqual([r["actual"] for r in durable["records"]],[43.,30.])
        self.assertTrue(all(r["direction_hit"] for r in durable["records"]))
        self.assertEqual(evaluate(durable,outcomes,now)["status"],"READY")
        self.assertEqual(evaluate(durable,outcomes,now)["counts"]["graded"],2)
        self.assertEqual(merge(durable,{},outcomes)["new_verified_grades"],0)
    def test_wrong_identity_unverified_live_zero_and_malformed_rejected(self):
        for change in [{"nba_person_id":"999"},{"player":"Other"},{"team":"NYK"},
                       {"opponent":"BOS"},{"date":"2026-11-14"},{"source":"ESPN_FINAL"},
                       {"final_confirmed":False},{"source_game_id":"401909990"},
                       {"MIN":0},{"PTS":float('nan')},{"PRA":42}]:
            with self.subTest(change=change):
                self.assertEqual(augment_final_outcomes(ledger(PICK),{"records":[]},[{**ROW,**change}])["records"],[])
    def test_conflicting_cache_rows_fail_closed(self):
        for change in [{"PTS":31,"PRA":44},{"source_game_id":"0022600242"},
                       {"dnp_final_verified":True,"dnp_reason":"Inactive"}]:
            self.assertEqual(augment_final_outcomes(ledger(PICK),{"records":[]},[ROW,{**ROW,**change}])["records"],[])
    def test_existing_final_never_overwritten_or_duplicated(self):
        existing={**PICK,"status":"GRADED","actual":25,"final_source":"ESPN_FINAL","source_game_id":"401909990"}
        self.assertEqual(augment_final_outcomes(ledger(PICK),{"records":[existing]},[ROW]),{"records":[existing]})
    def test_verified_explicit_dnp_only(self):
        dnp={**ROW,"dnp_final_verified":True,"dnp_reason":"Inactive"}
        result=augment_final_outcomes(ledger(PICK),{"records":[]},[dnp])
        self.assertEqual(result["records"][0]["status"],"EXCLUDED_VERIFIED_DNP")
        self.assertIsNone(result["records"][0]["actual"])
        self.assertEqual(augment_final_outcomes(ledger(PICK),{"records":[]},[{**dnp,"dnp_reason":""}])["records"],[])
    def test_direct_script_entrypoint_recovers_cached_final(self):
        import json, shutil, subprocess, sys, tempfile
        from pathlib import Path
        root=Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp)
            shutil.copytree(root/"iphone_bot",target/"iphone_bot",ignore=shutil.ignore_patterns("tests","__pycache__"))
            (target/"docs").mkdir()
            (target/"docs/lagged_matchup_all_market_ledger.json").write_text(json.dumps(ledger(PICK)))
            (target/"docs/verified_final_player_cache.json").write_text(json.dumps({"version":1,"rows":[ROW]}))
            result=subprocess.run([sys.executable,str(target/"iphone_bot/multimarket_forecast_ledger.py")],cwd=tmp,text=True,capture_output=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(json.loads((target/"docs/lagged_matchup_all_market_ledger.json").read_text())["records"][0]["actual"],30)
    def test_malformed_frozen_rows_remain_for_audit_without_crash(self):
        self.assertEqual(augment_final_outcomes(ledger(None, 7, {**PICK,"start":7}, {**PICK,"player_id":None}, {**PICK,"player":None}), {"records":[]}, [ROW])["records"], [])
    def test_wrong_frozen_opponent_and_naive_start_rejected(self):
        for change in [{"opponent":"BOS"},{"start":"2026-11-15T23:00:00"}]:
            self.assertEqual(augment_final_outcomes(ledger({**PICK,**change}),{"records":[]},[ROW])["records"],[])
