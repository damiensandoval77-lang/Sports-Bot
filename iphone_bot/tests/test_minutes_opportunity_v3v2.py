import unittest
from iphone_bot.minutes_v3_research import forecast as minutes3,team_context
from iphone_bot.opportunity_v2_research import forecast as opportunity2
def games(n=13):
 return [{"date":f"2026-10-{i:02d}","team":"BOS","id":"11",
          "MIN":30.+(i%3),"AST":5.+(i%2),"REB":7.+(i%2)}
         for i in range(1,n+1)]
class MinutesAndOpportunityV2(unittest.TestCase):
 def test_both_models_past_only_and_valid_proxies(self):
  past=games(12)
  mv=minutes3(past,"2026-10-13","BOS",player_id="11")
  self.assertEqual(mv["status"],"PREGAME_MINUTES_V3_RESEARCH")
  self.assertFalse(mv["verified_out_context_applied"])
  op=opportunity2(past,"2026-10-13","BOS",player_id="11",minutes=mv,
                  baseline_by_stat={"AST":5,"REB":7})
  for stat in ("AST","REB"):
   self.assertEqual(op["markets"][stat]["status"],"PREGAME_OPPORTUNITY_V2_RESEARCH")
   self.assertEqual(op["markets"][stat]["source_kind"],"BOX_SCORE_RATE_PROXY")
   self.assertFalse(op["markets"][stat]["is_potential_assists"])
   self.assertFalse(op["markets"][stat]["is_rebound_chances"])
   self.assertFalse(op["markets"][stat]["research_only"] is False)
  future=games(15)[12:]
  result=opportunity2(past+future,"2026-10-13","BOS",player_id="11",
                      baseline_by_stat={"AST":5,"REB":7})
  self.assertEqual(result["markets"]["AST"]["projection"],op["markets"]["AST"]["projection"])
 def test_team_context_requires_independently_verified_out_status(self):
  history=games(12)
  # Realistic full-team coverage and multiple with/without completed dates.
  full=[]
  for idx,row in enumerate(history):
   full.append(row)
   for other in range(20,28):
    if other==20 and idx%2:continue
    full.append(dict(row,id=str(other),MIN=10.))
  context=team_context(full)
  no=minutes3(history,"2026-10-13","BOS",player_id="11",
              verified_out_ids=["20"],team_games=context,
              pretip_injury_verified=False)
  yes=minutes3(history,"2026-10-13","BOS",player_id="11",
              verified_out_ids=["20"],team_games=context,
              pretip_injury_verified=True)
  self.assertFalse(no["verified_out_context_applied"])
  self.assertTrue(yes["verified_out_context_applied"])
  self.assertEqual(yes["teammates_evaluated"],1)
 def test_no_future_lookahead_or_fake_verified_tracking(self):
  data=games(7)
  self.assertIsNone(minutes3(data,"2026-10-08","BOS")["expected_minutes"])
  p=opportunity2(data,"2026-10-08","BOS",player_id="11")
  self.assertIsNone(p["markets"]["AST"]["projection"])
  self.assertIsNone(p["markets"]["REB"]["projection"])
