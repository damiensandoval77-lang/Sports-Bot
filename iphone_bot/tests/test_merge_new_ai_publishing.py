import copy
import unittest
from iphone_bot.multimarket_forecast_ledger import merge
from iphone_bot.merge_new_ai_publishing import durable_merge

def forecast(i=1,price=15.5):
 return {"player":"Player "+str(i),"player_id":str(i),"team":"CLE",
 "game":"Cleveland Cavaliers @ Charlotte Hornets","start":"2026-11-10T00:00:00Z",
 "stat":"PTS","line":price,"projection":14.3,
 "market_updated":"2026-11-09T22:00:00Z",
 "captured_at":"2026-11-09T22:05:00Z",
 "pickem_tier":"standard","standard_line_two_sided_verified":True,
 "research_only":True,"calibrated_probability":None,
 "estimated_hit_chance":{"modeled_direction":"Less"}}
def frozen(*preds):
 return merge({},{"status":"LIVE_ALL_MARKET_NEW_AI_UNCALIBRATED","predictions":list(preds)},{})
def finished(row):
 return {"records":[{"status":"GRADED","player_id":row["player_id"],"team":row["team"],
 "game":row["game"],"start":row["start"],"stat":row["stat"],
 "actual":12,"final_source":"NBA_CDN_FINAL","source_game_id":"0022601001"}]}
class DurableNewAiTests(unittest.TestCase):
 def test_new_pregame_lines_survive_concurrent_grading(self):
  p=forecast()
  old=merge(frozen(p),{},finished(p))
  runner=frozen(p,forecast(2))
  out=durable_merge(old,runner,{"records":[]})
  self.assertEqual(len(out["records"]),2)
  p1=next(x for x in out["records"] if x["player_id"]=="1")
  self.assertEqual(p1["grade"],"GRADED")
  self.assertEqual(p1["actual"],12)
  self.assertEqual(p1["line"],15.5)
 def test_verified_final_settles_while_merging_live_new_market(self):
  p=forecast()
  out=durable_merge(frozen(p),frozen(p,forecast(2)),finished(p))
  self.assertEqual(next(x for x in out["records"] if x["player_id"]=="1")["grade"],"GRADED")
 def test_line_move_adds_distinct_frozen_version_without_rewriting_original(self):
  p=forecast()
  moved=forecast(price=16.5)
  moved["market_updated"]="2026-11-09T22:10:00Z"
  moved["captured_at"]="2026-11-09T22:15:00Z"
  out=durable_merge(frozen(p),frozen(moved),{})
  self.assertEqual(len(out["records"]),2)
  self.assertEqual(sorted(x["line"] for x in out["records"]),[15.5,16.5])
  self.assertEqual(out["records"][0]["projection"],14.3)
 def test_same_threshold_cannot_rewrite_original_projection(self):
  p=forecast()
  changed=forecast()
  changed["projection"]=11.8
  with self.assertRaises(ValueError):
   durable_merge(frozen(p),frozen(changed),{})
 def test_grade_conflict_rejected(self):
  p=forecast()
  old=merge(frozen(p),{},finished(p))
  new=copy.deepcopy(old)
  new["records"][0]["actual"]=14
  with self.assertRaises(ValueError):durable_merge(old,new,{})
 def test_invalid_late_capture_cannot_enter_repository(self):
  late=forecast();late["captured_at"]="2026-11-10T00:05:00Z"
  incoming={"status":"FROZEN_NEW_AI_ALL_MARKET","records":[late]}
  with self.assertRaises(ValueError):durable_merge(frozen(forecast()),incoming,{})
if __name__=="__main__":unittest.main()

class ConcurrentFirstFreezeTests(unittest.TestCase):
 def test_distinct_pending_race_preserves_published_original_and_new_players(self):
  p=forecast();later=forecast();later['captured_at']='2026-11-09T22:10:00Z';later['projection']=17.1
  out=durable_merge(frozen(p),frozen(later,forecast(2)),{})
  self.assertEqual(next(x for x in out['records'] if x['player_id']=='1'),frozen(p)['records'][0])
  self.assertEqual(len(out['records']),2)
  self.assertEqual(len(out['concurrent_refreezes_ignored']),1)
 def test_late_arriving_earlier_observation_does_not_rewrite_published_original(self):
  p=forecast();earlier=forecast();earlier['captured_at']='2026-11-09T22:01:00Z';earlier['projection']=17.1
  out=durable_merge(frozen(p),frozen(earlier),{})
  self.assertEqual(out['records'],frozen(p)['records'])
 def test_distinct_pending_race_never_reverts_settlement(self):
  p=forecast();old=merge(frozen(p),{},finished(p));later=forecast();later['captured_at']='2026-11-09T22:10:00Z';later['projection']=17.1
  out=durable_merge(old,frozen(later,forecast(2)),{})
  self.assertEqual(next(x for x in out['records'] if x['player_id']=='1'),old['records'][0])
 def test_conflicting_settled_observation_still_rejected(self):
  p=forecast();later=forecast();later['captured_at']='2026-11-09T22:10:00Z';later['projection']=17.1
  with self.assertRaises(ValueError):durable_merge(frozen(p),merge(frozen(later),{},finished(later)),{})
