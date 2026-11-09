import unittest
from datetime import datetime,timezone,timedelta
from iphone_bot.daily_projection_fallback import build,retain_verified_upcoming
class MockEstimator:
 def predict(self,x):return [7.5]
def schedule(now):
 tip=(now+timedelta(hours=4)).isoformat()
 return {"generated_at":now.isoformat(),"games":[{
     "game":"Boston Celtics @ Miami Heat","start":tip,"game_state":"pre"}]}
def history(now):
 today=now.date()
 # prior 8 days, no same-game.
 return [{"id":"1","team":"BOS","date":(today-timedelta(days=d)).isoformat(),
    "PTS":20,"REB":5,"AST":7,"MIN":30,"FGA":13,"FG3A":6,"TOV":2}
    for d in range(1,9)]
def form(now):
 return {"season":"2026-27","updated_at":now.isoformat(),
  "players":[{"player_id":"1","player":"Test Player","team":"BOS"}]}
class ModelFallbackTests(unittest.TestCase):
 def setUp(self):
  self.now=datetime(2026,11,8,20,0,tzinfo=timezone.utc)
  self.models={x:{"features":["PTS_L5","DAYS_REST"],"fill_values":{},
      "model":MockEstimator()} for x in ("PTS","REB","AST","PRA")}
 def test_eligible_games_produce_stats_but_never_fabricated_lines(self):
  report=build(schedule(self.now),form(self.now),history(self.now),self.models,self.now)
  self.assertEqual(report["status"],"PREGAME_PROJECTIONS_NO_LINES")
  self.assertEqual(report["games_covered"],1)
  self.assertEqual(len(report["predictions"]),4)
  self.assertEqual(report["predictions"][0]["projection"],7.5)
  self.assertIsNone(report["predictions"][0]["line"])
  self.assertIsNone(report["predictions"][0]["direction"])
  self.assertFalse(report["has_calibrated_hit_percentages"])
 def test_temporary_failure_keeps_real_upcoming_pretip_forecasts(self):
  old=build(schedule(self.now),form(self.now),history(self.now),self.models,self.now)
  failed={"status":"MODEL_OR_INPUT_UNAVAILABLE","generated_at":(self.now+timedelta(minutes=10)).isoformat(),
          "predictions":[]}
  recovered=retain_verified_upcoming(old,failed,self.now+timedelta(minutes=10))
  self.assertEqual(len(recovered["predictions"]),4)
  self.assertTrue(all(p["retained_verified_pretip"] for p in recovered["predictions"]))
  self.assertTrue(all(p["captured_at"]==self.now.isoformat() for p in recovered["predictions"]))
  expired=retain_verified_upcoming(old,failed,self.now+timedelta(hours=13))
  self.assertEqual(expired["predictions"],[])
 def test_never_reuses_pretip_projection_after_game_starts(self):
  old=build(schedule(self.now),form(self.now),history(self.now),self.models,self.now)
  failed={"status":"MODEL_OR_INPUT_UNAVAILABLE","predictions":[]}
  after=self.now+timedelta(hours=5)
  self.assertFalse(retain_verified_upcoming(old,failed,after)["predictions"])

 def test_stale_schedule_blocks_future_projections(self):
  p=schedule(self.now);p["generated_at"]=(self.now-timedelta(days=2)).isoformat()
  report=build(p,form(self.now),history(self.now),self.models,self.now)
  self.assertEqual(report["status"],"SCHEDULE_STALE")
  self.assertEqual(report["predictions"],[])
 def test_games_after_tipoff_are_hidden(self):
  p=schedule(self.now);p["games"][0]["start"]=(self.now-timedelta(minutes=5)).isoformat()
  self.assertEqual(build(p,form(self.now),history(self.now),
    self.models,self.now)["predictions"],[])
 def test_same_game_outcomes_do_not_change_feature_history(self):
  base=build(schedule(self.now),form(self.now),history(self.now),self.models,self.now)
  future={**history(self.now)[0],"date":self.now.date().isoformat(),"PTS":1000}
  other=build(schedule(self.now),form(self.now),
     history(self.now)+[future],self.models,self.now)
  self.assertEqual(base["predictions"],other["predictions"])
