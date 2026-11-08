import gzip
import json
import tempfile
import unittest
from pathlib import Path

from iphone_bot.preserve_research_inputs import preserve

def files(d):
    root=Path(d)
    root.mkdir(parents=True,exist_ok=True)
    return root

class SourceEvidenceTests(unittest.TestCase):
    def test_preserves_full_original_two_sided_bookmaker_lines(self):
        with tempfile.TemporaryDirectory() as t:
            docs=files(Path(t)/"docs")
            original={"updated_at":"2026-11-07T20:00:00Z","picks":[
                {"game":"Denver Nuggets @ Indiana Pacers","player":"Nikola Jokic",
                 "stat":"Points","line":30.5,"direction":"More","odds":-110},
                {"game":"Denver Nuggets @ Indiana Pacers","player":"Nikola Jokic",
                 "stat":"Points","line":30.5,"direction":"Less","odds":-110}]}
            (docs/"data.json").write_text(json.dumps(original))
            (docs/"odds_compact.json").write_text(json.dumps(original))
            (docs/"odds_fetch_status.json").write_text(json.dumps({"status":"FETCHED"}))
            path,created=preserve("odds",docs,Path(t)/"archive")
            self.assertTrue(created)
            self.assertEqual(json.loads(gzip.decompress(path.read_bytes()))["full_odds_feed"],original)
            again,new=preserve("odds",docs,Path(t)/"archive")
            self.assertEqual((again,new),(path,False))

    def test_zero_or_unverified_sportsbook_data_not_saved_as_real(self):
        with tempfile.TemporaryDirectory() as t:
            docs=files(Path(t)/"docs")
            for name,report in {
                "data.json":{"updated_at":"2026-11-07T20:00:00Z","picks":[]},
                "odds_compact.json":{"updated_at":"2026-11-07T20:00:00Z","picks":[]},
                "odds_fetch_status.json":{"status":"CREDITS_BELOW_RESERVE_PRESERVED"}}.items():
                (docs/name).write_text(json.dumps(report))
            self.assertEqual(preserve("odds",docs,Path(t)/"archive"),(None,False))

    def test_prizepicks_full_slate_source_is_not_bookmaker_american_odds(self):
        with tempfile.TemporaryDirectory() as t:
            docs=files(Path(t)/"docs")
            pp={"status":"LIVE_THIRD_PARTY_PRIZEPICKS_LINES",
                "generated_at":"2026-11-07T20:00:00Z",
                "board_offers":[{"id":"pp_123","player":"Example","team":"BOS",
                 "stat":"PTS","line":28.5,"more_tier":"standard",
                 "less_tier":"standard","observed_at":"2026-11-07T19:59:00Z"}]}
            (docs/"prizepicks.json").write_text(json.dumps(pp))
            path,_=preserve("prizepicks",docs,Path(t)/"archive")
            content=json.loads(gzip.decompress(path.read_bytes()))
            self.assertEqual(content["feed"],pp)
            self.assertTrue(content["is_pickem_not_sportsbook_american_odds"])
            self.assertTrue(content["not_a_retroactive_pregame_paper_pick"])

    def test_schedule_keeps_uncovered_games_and_source_limitations(self):
        with tempfile.TemporaryDirectory() as t:
            docs=files(Path(t)/"docs")
            games={"generated_at":"2026-11-07T20:00:00Z",
                   "coverage_complete":False,
                   "games":[{"game":"Game A","game_state":"pre"},
                            {"game":"Game B","game_state":"post","home_score":109}]}
            (docs/"nba_schedule.json").write_text(json.dumps(games))
            path,_=preserve("schedule",docs,Path(t)/"archive")
            report=json.loads(gzip.decompress(path.read_bytes()))
            self.assertEqual(len(report["schedule"]["games"]),2)
            self.assertTrue(report["not_proof_of_complete_slate"])
            self.assertTrue(report["not_sportsbook_lines"])

if __name__=="__main__":unittest.main()
