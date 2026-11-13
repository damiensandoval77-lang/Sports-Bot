import unittest
from iphone_bot.prizepicks_sample_backtest import evaluate
def prop(**extra):
    r={"player":"Test Player","team":"NYK","stat":"Rebounds",
       "game_date":"2026-10-28","closing_observed_at":"2026-10-28T18:00:00Z",
       "starts_at":"2026-10-28T23:00:00Z","closing_line":4.5,
       "actual_value":2,"result":"under"}
    r.update(extra);return r
def logs():
    return [{"player":"Test Player","team":"NYK",
        "game_date":"2026-10-"+str(d),"confirmed":"True",
        "rebounds":6,"minutes":30} for d in (21,23,24,26)]
class FreeSampleAuditTests(unittest.TestCase):
    def test_strictly_older_games_and_paired_baselines(self):
        data=logs()+[{"player":"Test Player","team":"NYK","game_date":"2026-10-28",
                     "confirmed":"True","rebounds":100,"minutes":30}]
        r=evaluate([prop()],data)
        self.assertEqual(r["usable_market_rows"],1)
        self.assertEqual(r["baseline"]["wins"],0)
        self.assertEqual(r["rate_candidate"]["wins"],0)
        self.assertEqual(r["joined_rows"][0]["last_prior_game"],"2026-10-26")
        self.assertTrue(r["joined_rows"][0]["no_leakage"])
    def test_cannot_look_ahead_to_posttip_quote(self):
        r=evaluate([prop(closing_observed_at="2026-10-29T00:00:00Z")],logs())
        self.assertEqual(r["usable_market_rows"],0)
        self.assertEqual(r["exclusions"]["NOT_VERIFIED_PRETIP_LINE"],1)
    def test_unsupported_stat_and_other_team_rejected(self):
        wrong_team=[dict(x,team="BOS") for x in logs()]
        r=evaluate([prop(stat="Fantasy Score"),prop()],wrong_team)
        self.assertEqual(r["usable_market_rows"],0)
        self.assertEqual(r["exclusions"]["UNSUPPORTED_MARKET"],1)
        self.assertEqual(r["exclusions"]["INSUFFICIENT_CONFIRMED_PRIOR_GAMES"],1)
    def test_unconfirmed_logs_rejected_and_labels_must_agree(self):
        unconfirmed=[dict(x,confirmed="False") for x in logs()]
        self.assertEqual(evaluate([prop()],unconfirmed)["usable_market_rows"],0)
        self.assertEqual(evaluate([prop(result="over")],logs())["exclusions"]["PROVIDER_LABEL_MISMATCH"],1)
    def test_duplicate_conflicts_excluded(self):
        data=logs()+[dict(logs()[0],rebounds=99)]
        self.assertEqual(evaluate([prop()],data)["usable_market_rows"],1)
        self.assertEqual(evaluate([prop()],data)["joined_rows"][0]["prior_games"],3)
