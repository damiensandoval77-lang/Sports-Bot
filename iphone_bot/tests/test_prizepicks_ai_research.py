import unittest
from datetime import datetime,timezone
from iphone_bot.prizepicks_ai_research import generate

NOW=datetime(2026,11,7,19,0,tzinfo=timezone.utc)
START="2026-11-08T01:00:00Z"
class Model:
    def predict(self,x):
        return [27.5]
class PrizePicksAIResearchTests(unittest.TestCase):
    def feed(self):
        return {"status":"LIVE_THIRD_PARTY_PRIZEPICKS_LINES",
            "generated_at":"2026-11-07T18:30:00Z",
            "board_offers":[{"id":"pp_1","player":"Sample Player","team":"BOS",
                "game":"Boston Celtics @ Miami Heat","starts_at":START,
                "stat":"PTS","line":25.5,"observed_at":"2026-11-07T18:30:00Z",
                "source":"independent_prizepicksapi_com","is_demo":False,
                "more_tier":"standard","less_tier":"standard"}]}
    def form(self):
        return {"season":"2026-27","updated_at":"2026-11-07T18:20:00Z",
                "players":[{"player":"Sample Player","player_id":"10","team":"BOS"}]}
    def games(self):
        return [{"id":"10","player":"Sample Player","team":"BOS",
            "date":f"2026-10-{day:02d}","PTS":20.,"REB":5.,"AST":6.,
            "MIN":31.,"FGA":15.,"FG3A":6.,"TOV":2.} for day in range(22,30)]
    def models(self):
        cols=["PTS_L5","PTS_Season","MIN_L5","DAYS_REST"]
        return {"PTS":{"model":Model(),"features":cols,"fill_values":{x:0 for x in cols}}}
    def test_genuine_prizepicks_line_gets_original_trained_prediction(self):
        result=generate(self.feed(),self.form(),self.games(),self.models(),now=NOW)
        self.assertEqual(result["comparison_count"],1)
        pick=result["comparisons"][0]
        self.assertEqual(pick["combined_projection"],27.5)
        self.assertEqual(pick["ai_direction"],"MORE")
        self.assertEqual(pick["combined_method"],"ORIGINAL_AI_FALLBACK")
        self.assertTrue(pick["no_calibrated_hit_percentage"])
        self.assertFalse(result["confidence_calibrated"])
        self.assertFalse(result["sportsbook_american_odds_available"])
        self.assertFalse(result["paper_pick_ledger_modified"])
    def test_started_games_never_reprojected(self):
        x=self.feed()
        x["board_offers"][0]["starts_at"]="2026-11-07T15:00:00Z"
        self.assertEqual(generate(x,self.form(),self.games(),self.models(),now=NOW)["comparison_count"],0)
    def test_unverified_vendor_row_not_modeled(self):
        x=self.feed()
        x["board_offers"][0]["is_demo"]=True
        self.assertEqual(generate(x,self.form(),self.games(),self.models(),now=NOW)["comparison_count"],0)
    def test_unmatched_team_not_guessed(self):
        x=self.feed()
        x["board_offers"][0]["team"]="LAL"
        self.assertEqual(generate(x,self.form(),self.games(),self.models(),now=NOW)["comparison_count"],0)
    def test_official_game_day_out_prevents_prizepicks_projection(self):
        injury={"status":"OFFICIAL_NBA_REPORT_VERIFIED","injury_data_verified":True,
                "report_issued_at":"2026-11-07T18:00:00Z",
                "players":[{"player_id":"10","team":"BOS",
                            "game_date":"2026-11-07","status":"Out"}]}
        # The modeled game is on November 7 Eastern at 8 PM.
        self.assertEqual(generate(self.feed(),self.form(),self.games(),
                                  self.models(),now=NOW,injuries=injury)["comparison_count"],0)
        injury["players"][0]["game_date"]="2026-11-08"
        self.assertEqual(generate(self.feed(),self.form(),self.games(),
                                  self.models(),now=NOW,injuries=injury)["comparison_count"],1)
        injury["players"][0]["game_date"]="2026-11-07"
        injury["report_issued_at"]="2026-11-05T18:00:00Z"
        self.assertEqual(generate(self.feed(),self.form(),self.games(),
                                  self.models(),now=NOW,injuries=injury)["comparison_count"],1)

    def test_missing_history_not_faked(self):
        self.assertEqual(generate(self.feed(),self.form(),self.games()[:3],self.models(),now=NOW)["comparison_count"],0)
    def test_duplicate_lines_carry_same_model_input_without_new_probabilities(self):
        x=self.feed()
        x["board_offers"].append({**x["board_offers"][0],"id":"pp_2","line":26.5})
        out=generate(x,self.form(),self.games(),self.models(),now=NOW)
        self.assertEqual(len(out["comparisons"]),2)
        self.assertEqual(out["comparisons"][0]["combined_projection"],out["comparisons"][1]["combined_projection"])
if __name__=="__main__":unittest.main()
