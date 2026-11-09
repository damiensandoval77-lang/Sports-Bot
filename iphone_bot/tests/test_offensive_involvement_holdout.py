"""No future-target usage, team-leakage, or production promotion."""
import unittest
try:
    from iphone_bot.offensive_involvement_holdout import predict,evaluate
except ImportError:
    from offensive_involvement_holdout import predict,evaluate


def game(day,pts=20,mins=30,fga=16,fta=3,tov=2):
    return dict(date=day,season="2025-26",id="123",team="BOS",
        PTS=float(pts),MIN=float(mins),FGA=float(fga),
        FTA=float(fta),TOV=float(tov))


class InvolvementTests(unittest.TestCase):
    def test_rejects_missing_prior_games(self):
        self.assertIsNone(predict([game("2026-01-01")]*7))

    def test_fixed_history_never_uses_target_stats(self):
        rows=[game(f"2026-01-{d:02d}",pts=20+d) for d in range(1,9)]
        initial=predict(rows)
        self.assertIsNotNone(initial)
        self.assertEqual(initial,predict(list(rows)))
        self.assertLessEqual(abs(initial["challenger"]-initial["baseline"]),
                             .25*.15*max(1,initial["baseline"])+1e-7)

    def test_target_does_not_enter_current_prediction(self):
        base=[game(f"2026-01-{d:02d}",pts=20) for d in range(1,9)]
        low=evaluate(base+[game("2026-01-09",pts=2)])
        high=evaluate(base+[game("2026-01-09",pts=60)])
        self.assertEqual(low["overall"]["n"],1)
        self.assertEqual(low["overall"]["baseline_mae"],18)
        self.assertEqual(high["overall"]["baseline_mae"],40)
        self.assertFalse(low["production_modified"])
        self.assertFalse(high["automatic_promotion"])

    def test_missing_usage_proxy_is_not_zero(self):
        rows=[game(f"2026-01-{d:02d}") for d in range(1,9)]
        rows[0]["FGA"]=None
        self.assertIsNone(predict(rows))

    def test_duplicate_same_date_excluded(self):
        rows=[game(f"2026-01-{d:02d}") for d in range(1,9)]
        rows += [game("2026-01-09",15),game("2026-01-09",25),game("2026-01-10")]
        result=evaluate(rows)
        self.assertEqual(result["overall"]["n"],1)
        self.assertEqual(result["excluded"]["AMBIGUOUS_PLAYER_DATE"],2)


if __name__=="__main__":
    unittest.main()
