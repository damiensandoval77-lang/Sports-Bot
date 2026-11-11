import copy
import unittest
from datetime import datetime,timedelta,timezone
from research.opportunity_tempo_proxies import build

NOW="2026-11-11T21:00:00Z"
TIP="2026-11-12T00:00:00Z"

def fixtures(games=6):
    logs=[]
    for idx in range(games):
        date=(datetime(2026,10,20,tzinfo=timezone.utc)+timedelta(days=idx)).date().isoformat()
        for t,o in (("BOS","NYK"),("NYK","BOS")):
            for j in range(8):
                logs.append({"date":date,"team":t,"opponent":o,
                    "id":t+str(j),"FGA":10+j,"TOV":1+j%3,"MIN":24})
    return logs

def sources():
    form={"season":"2026-27","source_url":"https://example.org/logs",
        "updated_at":"2026-11-11T18:00:00Z"}
    joined={"status":"SOURCED_MATCHUP_CONTEXT_RESEARCH_NOT_LIVE",
        "captured_at":"2026-11-11T20:00:00Z",
        "production_hit_estimate_eligible":False,
        "player_records":[{"game_id":"future","player_id":"BOS0",
          "team":"BOS","opponent":"NYK","start":TIP,
          "captured_at":"2026-11-11T20:00:00Z"}]}
    return form,joined

class OpportunityTempoTests(unittest.TestCase):
    def test_actual_source_proxies_not_official_model_factors(self):
        f,j=sources();r=build(fixtures(),f,j,captured_at=NOW)
        self.assertEqual(r["with_both_descriptive_proxies"],1)
        self.assertGreater(r["records"][0]["fga_plus_tov_share_research"],0)
        self.assertFalse(r["records"][0]["is_official_usage_pct"])
        self.assertFalse(r["records"][0]["is_verified_possessions_pace"])
        self.assertFalse(r["production_hit_estimate_eligible"])

    def test_only_four_prior_games_produces_no_proxies(self):
        f,j=sources();r=build(fixtures(4),f,j,captured_at=NOW)
        self.assertEqual(r["with_both_descriptive_proxies"],0)

    def test_never_use_data_from_future_match_day(self):
        f,j=sources();a=build(fixtures(),f,j,captured_at=NOW)
        extra=fixtures(1)
        for x in extra:
            x["date"]="2026-11-11"
            x["FGA"]=500
        b=build(fixtures()+extra,f,j,captured_at=NOW)
        self.assertEqual(a["records"][0]["fga_plus_tov_share_research"],
                         b["records"][0]["fga_plus_tov_share_research"])

    def test_no_mixed_future_source(self):
        f,j=sources();f["updated_at"]="2026-11-11T22:00:00Z"
        with self.assertRaises(ValueError):build(fixtures(),f,j,captured_at=NOW)

    def test_ambiguous_duplicate_player_identity_rejected(self):
        f,j=sources();j["player_records"].append(copy.deepcopy(j["player_records"][0]))
        with self.assertRaises(ValueError):build(fixtures(),f,j,captured_at=NOW)

    def test_corrupt_game_does_not_inflate_opportunities(self):
        f,j=sources();x=fixtures(5)
        x[0]["FGA"]=-1
        r=build(x,f,j,captured_at=NOW)
        self.assertGreater(r["blockers"]["insufficient_player_shot_involvement_games"],0)

    def test_already_started_game_not_prospective(self):
        f,j=sources();j["player_records"][0]["start"]="2026-11-11T19:00:00Z"
        self.assertEqual(build(fixtures(),f,j,captured_at=NOW)["count"],0)

    def test_unknown_teammate_splits_remain_unknown(self):
        f,j=sources();r=build(fixtures(),f,j,captured_at=NOW)
        self.assertFalse(r["verified_teammate_splits"])
        self.assertIsNone(r["records"][0]["teammate_injury_usage_adjustment"])

if __name__=="__main__":unittest.main()
