import unittest
from iphone_bot.shooting_efficiency_v1 import (
    rates,forecast,opponent_defense_index,defense_adjustment)
def sample(day,team="BOS",opponent="NYK",pid=1,threes=2):
    return {"id":str(pid),"date":f"2026-10-{day:02d}",
      "season":"2026-27","team":team,"opponent":opponent,
      "MIN":30.,"FGA":12.,"FG3A":5.,"FGM":6.,
      "FG3M":float(threes),"FTA":4.,"FTM":3.,
      "PTS":float(2*(6-threes)+3*threes+3)}
class ShootingV1Tests(unittest.TestCase):
 def test_attempt_weighted_shooting_and_shot_volume(self):
    hist=[sample(i) for i in range(1,13)]
    a=rates(hist,"2026-10-13","BOS")
    self.assertAlmostEqual(a["last5"]["fg_pct"],.5)
    self.assertAlmostEqual(a["last10"]["three_pct"],.4)
    self.assertAlmostEqual(a["season"]["ft_pct"],.75)
    self.assertAlmostEqual(a["season"]["effective_fg_pct"],(6+.5*2)/12,places=4)
    self.assertEqual(a["last5"]["three_pa_per_game"],5)
    p=forecast(hist,"2026-10-13","BOS","NYK",30,combined_baseline=17)
    self.assertEqual(p["status"],"PREGAME_SHOOTING_SHADOW_RESEARCH")
    self.assertEqual(p["expected_2pa"]+p["expected_3pa"],p["expected_2pa"]+p["expected_3pa"])
    self.assertEqual(p["expected_2pa"],7)
    self.assertEqual(p["expected_3pa"],5)
    self.assertFalse(p["production_applied"])
    self.assertIsNotNone(p["blended_projection"])
 def test_future_shooting_hot_streak_is_ignored(self):
    hist=[sample(i) for i in range(1,12)]
    p=forecast(hist,"2026-10-12","BOS",expected_minutes=30)
    future=[sample(12,threes=5),sample(13,threes=5)]
    q=forecast(hist+future,"2026-10-12","BOS",expected_minutes=30)
    self.assertEqual(p["projection"],q["projection"])
    self.assertEqual(p["season_shooting"],q["season_shooting"])
 def test_ignores_other_team_games_and_too_little_history(self):
    hist=[sample(i) for i in range(1,7)]
    self.assertEqual(forecast(hist,"2026-10-13","BOS")["status"],
                     "INSUFFICIENT_SHOOTING_DATA")
    other=[sample(i,team="CHI") for i in range(7,13)]
    self.assertIsNone(rates(hist+other,"2026-10-13","BOS"))
 def test_opponent_adjustment_uses_only_earlier_complete_team_games(self):
    games=[]
    for d in range(1,10):
       games.extend(sample(d,team="NYK",opponent="BOS",pid=i) for i in range(1,9))
    idx=opponent_defense_index(games)
    previous=defense_adjustment(idx,"BOS","2026-10-06","2026-27")
    self.assertEqual(previous["status"],"LAGGED_OPPONENT_TEAM_SHOOTING_PROXY")
    self.assertEqual(previous["games"],5)
    q=defense_adjustment(idx,"BOS","2026-10-05","2026-27")
    self.assertEqual(q["status"],"NO_VERIFIED_OPPONENT_SHOOTING_SAMPLE")
    self.assertFalse(previous["individual_defender_inferred"])
 def test_without_prior_verified_defense_no_imagined_boost(self):
    hist=[sample(i) for i in range(1,13)]
    p=forecast(hist,"2026-10-13","BOS","NYK",30,
               defense_index={},combined_baseline=17)
    self.assertFalse(p["opponent_adjustment_applied"])
    self.assertEqual(p["opponent_shooting"]["two_multiplier"],1)
    self.assertFalse(p["injury_usage_adjustment_applied"])
