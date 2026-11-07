import datetime as dt
import unittest
import urllib.error
from iphone_bot.research_context import minutes_estimate,positional_allowance,teammate_on_off,injury_minutes_research,minutes_walkforward_backtest
from iphone_bot.weight_research import walkforward_weights
from iphone_bot.model_performance import compute_performance
from iphone_bot.fetch_official_injuries import parse_rows,report_links,parse_espn_injuries,failure_label,fallback_links

def ledger(day,stat="PTS",original=24,shadow=20,actual=23):
    time=dt.datetime(2026,1,1,tzinfo=dt.timezone.utc)+dt.timedelta(days=day)
    return {"player_id":str(day),"market":stat,"event_start":time.isoformat(),
            "captured_at":(time-dt.timedelta(hours=4)).isoformat(),
            "status":"SETTLED","line":21.5,"actual":actual,
            "original_projection":original,"opponent_shadow_projection":shadow,
            "combined_projection":(original+shadow)/2,"bookmaker":"FanDuel",
            "american_odds":-110,"side":"OVER"}

class ResearchUpgradeTests(unittest.TestCase):
    def test_minutes_strictly_pregame(self):
        days=[{"date":f"2026-11-{day:02d}","MIN":v}
              for day,v in enumerate([26,28,29,30,32,52],start=1)]
        result=minutes_estimate(days,"2026-11-06")
        self.assertEqual(result["games"],5)
        self.assertLess(result["expected_minutes"],40)
        self.assertFalse(result["is_confirmed"])
        self.assertIsNone(minutes_estimate(days,"2026-11-04")["expected_minutes"])

    def test_injury_minutes_scenario_requires_verified_absence_history(self):
        # 8 prior games: teammate plays four, misses four, both represented
        # by a well-covered team player log.
        all_games=[]
        history=[]
        for day in range(1,9):
            date=f"2026-10-{day:02d}"
            history.append({"id":"100","date":date,"team":"BOS","MIN":26 if day<=4 else 32})
            for idx in range(7):
                all_games.append({"id":str(idx+200),"date":date,"team":"BOS","MIN":20})
            if day<=4:
                all_games.append({"id":"900","date":date,"team":"BOS","MIN":25})
        all_games.extend(history)
        result=injury_minutes_research(history,all_games,"2026-11-01","BOS",
            [{"player":"Verified Out Teammate","player_id":"900","team":"BOS"}])
        self.assertEqual(result["status"],"HISTORICAL_SCENARIO_RESEARCH_ONLY")
        self.assertEqual(result["delta_minutes"],5.0) # capped from +6
        self.assertFalse(result["live_adjustment_applied"])
        self.assertEqual(result["with_games"],4)
        self.assertEqual(result["without_games"],4)
        no_out=injury_minutes_research(history,all_games,"2026-11-01","BOS",[])
        self.assertIsNone(no_out["scenario_minutes"])

    def test_minutes_scenario_prevents_future_leakage(self):
        history=[{"id":"100","team":"BOS","date":f"2026-10-{i:02d}","MIN":30}
                 for i in range(1,7)]
        future={"id":"100","team":"BOS","date":"2026-11-10","MIN":55}
        result=injury_minutes_research(history+[future],history+[future],
              "2026-11-01","BOS",[])
        self.assertEqual(result["baseline_minutes"],30)
        self.assertIsNone(result["scenario_minutes"])

    def test_minutes_holdout_requires_sufficient_pregame_games(self):
        rows=[{"id":"8","date":f"2026-10-{i:02d}","MIN":28} for i in range(1,8)]
        result=minutes_walkforward_backtest(rows)
        self.assertEqual(result["status"],"INSUFFICIENT_HOLDOUT_MINUTES")
        self.assertIsNone(result["injury_scenario_mae"])

    def test_position_is_group_level_not_defender(self):
        games=[]
        for day in range(1,18):
            for defensive_team in ("MIA","CLE"):
                for pos in ("PG","SG"):
                    games.append({"date":f"2026-10-{day:02d}",
                                  "team":"BOS","opponent":defensive_team,
                                  "position":pos,"PTS":12+int(defensive_team=="MIA"),
                                  "REB":3,"AST":4,"PRA":19})
        r=positional_allowance(games,"2026-11-01","MIA","PG","PTS")
        self.assertEqual(r["position_group"],"G")
        self.assertEqual(r["games"],5)
        self.assertIn("NOT_INDIVIDUAL",r["status"])
        self.assertIsNone(positional_allowance(games,"2026-11-01","MIA",None,"PTS"))

    def test_teammate_split_observed_no_injury_inference(self):
        history=[{"date":f"2026-10-{day:02d}","PTS":day} for day in range(1,9)]
        teammates=[{"date":f"2026-10-{day:02d}","id":"45","MIN":20}
                   for day in (1,2,3,4)]
        r=teammate_on_off(history,teammates,"2026-11-01","45","PTS")
        self.assertEqual(r["without_games"],4)
        self.assertEqual(r["status"],"OBSERVED_SPLIT_NOT_CAUSAL")

    def test_official_pdf_names_only_not_assumed_available(self):
        players=[{"player":"Payton Pritchard","player_id":"11","team":"BOS"},
                 {"player":"Jaylen Brown","player_id":"12","team":"BOS"}]
        parsed=parse_rows("11/07/2026 BOS@CHA Boston Celtics Pritchard, Payton Questionable Injury/Illness - Eye\n",players)
        self.assertEqual(len(parsed),1)
        self.assertEqual(parsed[0]["status"],"Questionable")
        self.assertNotIn("12",{x["player_id"] for x in parsed})

    def test_official_pdf_rejects_status_without_a_game_date(self):
        roster=[{"player":"Payton Pritchard","player_id":"11","team":"BOS"}]
        # A PDF fragment or header can contain the right name and team
        # without proving which game date the report applies to.
        self.assertEqual(parse_rows(
            "Boston Celtics Pritchard, Payton Out Injury/Illness",roster),[])
        rows=parse_rows(
            "Boston Celtics Pritchard, Payton Out "
            "11/07/2026 BOS@CHA Boston Celtics Pritchard, Payton Questionable",roster)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["game_date"],"2026-11-07")
        self.assertEqual(rows[0]["status"],"Questionable")

    def test_official_pdf_matches_team_and_correct_game_date(self):
        roster=[{"player":"Jaylen Williams","player_id":"101","team":"BOS"},
                {"player":"Jaylen Williams","player_id":"102","team":"CHA"},
                {"player":"Anthony Davis","player_id":"103","team":"WAS"}]
        pdf_text=(
            "Game Date Game Time Matchup Team Player Name Current Status Reason\n"
            "11/06/2026 07:00 (ET) BOS@CHA Boston Celtics Williams, Jaylen Out Injury\n"
            "Charlotte Hornets Williams, Jaylen Available -\n"
            "WAS@ATL Washington Wizards Davis, Anthony Questionable Injury\n"
            "11/07/2026 08:00 (ET) WAS@OKC Washington Wizards Davis, Anthony Out Injury\n"
        )
        rows=parse_rows(pdf_text,roster)
        statuses={(r["player_id"],r["game_date"],r["team"]):r["status"] for r in rows}
        self.assertEqual(statuses[("101","2026-11-06","BOS")],"Out")
        self.assertEqual(statuses[("102","2026-11-06","CHA")],"Available")
        self.assertEqual(statuses[("103","2026-11-06","WAS")],"Questionable")
        self.assertEqual(statuses[("103","2026-11-07","WAS")],"Out")
        self.assertEqual(len(rows),4)

    def test_official_pdf_does_not_infer_unlisted_player(self):
        roster=[{"player":"Anthony Davis","player_id":"103","team":"WAS"},
                {"player":"Jalen Johnson","player_id":"104","team":"ATL"}]
        text="11/06/2026 WAS@ATL Washington Wizards Davis, Anthony Questionable Injury\nAtlanta Hawks NOT YET SUBMITTED\n"
        rows=parse_rows(text,roster)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["game_date"],"2026-11-06")
        self.assertEqual(rows[0]["player_id"],"103")

    def test_espn_backup_is_third_party_and_team_matched(self):
        roster=[{"player":"Sample Player","player_id":"7","team":"BOS"},
                {"player":"Another Player","player_id":"8","team":"NYK"}]
        payload={"injuries":[{"team":{"abbreviation":"BOS"},"injuries":[
            {"athlete":{"displayName":"Sample Player"},"status":"Day-To-Day"},
            {"athlete":{"displayName":"Another Player"},"status":"Out"}]}]}
        parsed=parse_espn_injuries(payload,roster)
        self.assertEqual(len(parsed),1)
        self.assertEqual(parsed[0]["status"],"DAY_TO_DAY")
        self.assertEqual(parsed[0]["provider"],"ESPN_THIRD_PARTY")

    def test_nba_403_is_diagnosed_not_silently_generic(self):
        error=urllib.error.HTTPError("https://ak-static.cms.nba.com",403,"Forbidden",{},None)
        self.assertEqual(failure_label(error),"HTTP_403")
        self.assertEqual(failure_label(urllib.error.URLError("DNS error")),"URL_ERROR")

    def test_official_fallback_urls_are_bounded_and_on_nba_host(self):
        now=dt.datetime(2026,11,6,22,30,tzinfo=dt.timezone.utc)
        urls=fallback_links(now)
        self.assertEqual(len(urls),12)
        self.assertTrue(all(url.startswith("https://ak-static.cms.nba.com/referee/injury/")
                            for _,url in urls))
        self.assertTrue(all(stamp<=now for stamp,_ in urls))

    def test_published_pdf_only(self):
        now=dt.datetime(2026,11,6,3,tzinfo=dt.timezone.utc)
        html='<a href="https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-05_09_00PM.pdf">Official</a>'
        candidates=report_links(html,now)
        self.assertEqual(len(candidates),1)
        self.assertTrue(candidates[0][1].endswith(".pdf"))

    def test_stats_broken_down_by_market(self):
        rows=[ledger(1,"PTS"),ledger(2,"REB"),ledger(3,"AST")]
        out=compute_performance(rows)
        self.assertEqual(out["by_stat"]["PTS"]["original"]["observations"],1)
        self.assertEqual(out["by_stat"]["REB"]["combined"]["observations"],1)
        self.assertEqual(out["by_stat"]["PRA"]["original"]["observations"],0)

    def test_weight_search_uses_later_holdout_without_live_change(self):
        records=[ledger(d,"PTS",original=20,shadow=28,actual=21) for d in range(90)]
        out=walkforward_weights(records)
        v=out["weights"]["PTS"]
        self.assertEqual(v["status"],"OUT_OF_SAMPLE_RESEARCH_ONLY")
        self.assertEqual(v["selected_original_weight"],0.75)  # tied MAE favors weight closest to 50/50
        self.assertGreaterEqual(v["training_count"],50)
        self.assertGreaterEqual(v["test_count"],20)
        self.assertFalse(v["applied_to_live_model"])
        self.assertTrue(out["live_model_unchanged"])

    def test_too_few_samples_do_not_autoweight(self):
        out=walkforward_weights([ledger(i) for i in range(15)])
        self.assertEqual(out["weights"]["PTS"]["status"],"INSUFFICIENT_WALKFORWARD_SAMPLES")
        self.assertIsNone(out["weights"]["PTS"]["selected_original_weight"])

if __name__=="__main__":unittest.main()
