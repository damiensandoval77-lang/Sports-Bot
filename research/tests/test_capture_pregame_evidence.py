import copy
import unittest
from research.capture_pregame_evidence import capture

FREEZE="2026-11-11T04:00:00Z"

def sources():
    form={"updated_at":"2026-11-11T02:00:00Z",
          "source_url":"https://example.org/published-player-logs",
          "log_fields":["date","opponent","PTS","MIN"],
          "players":[{"player_id":"100","player":"Player A","team":"BOS",
                      "latest_game":"2026-11-09",
                      "log":[["2026-11-05","NYK",12,28],["2026-11-07","CHI",16,30],
                             ["2026-11-09","MIA",10,32]]}]}
    schedule={"generated_at":"2026-11-11T03:00:00Z",
              "source_url":"https://example.org/published-fixtures",
              "games":[{"id":"g1","start":"2026-11-12T00:00:00Z",
                        "date_eastern":"2026-11-11",
                        "home_abbreviation":"BOS","away_abbreviation":"NYK"}]}
    injury={"injury_data_verified":True,"report_issued_at":"2026-11-11T03:20:00Z",
            "source_pdf":"https://example.org/official-injury-report",
            "players":[{"player_id":"100","team":"BOS","game_date":"2026-11-11",
                        "status":"Available"}]}
    return form,schedule,injury

class CaptureTests(unittest.TestCase):
    def test_sourced_minute_observations_not_fake_projection(self):
        f,s,i=sources()
        out=capture(f,s,i,frozen_at=FREEZE)
        self.assertEqual(out["future_game_count"],1)
        self.assertEqual(out["research_player_count"],1)
        p=out["research_players"][0]
        self.assertEqual(p["opponent"],"NYK")
        self.assertEqual(p["observed_minutes_last3"],30)
        self.assertEqual(p["injury_status"],"Available")
        self.assertFalse(p["eligible_for_hit_estimate"])
        self.assertNotIn("projected_minutes",p)

    def test_unlisted_injury_remains_unknown(self):
        f,s,i=sources()
        i["players"]=[]
        out=capture(f,s,i,frozen_at=FREEZE)
        self.assertEqual(out["research_players"][0]["injury_status"],"UNKNOWN_NOT_LISTED")
        self.assertIsNone(out["research_players"][0]["injury_source"])

    def test_future_source_publish_rejected(self):
        f,s,i=sources()
        f["updated_at"]="2026-11-11T05:00:00Z"
        with self.assertRaises(ValueError):capture(f,s,i,frozen_at=FREEZE)

    def test_future_injury_report_rejected(self):
        f,s,i=sources()
        i["report_issued_at"]="2026-11-11T05:00:00Z"
        with self.assertRaises(ValueError):capture(f,s,i,frozen_at=FREEZE)

    def test_no_backfill_after_tipoff(self):
        f,s,i=sources()
        out=capture(f,s,i,frozen_at="2026-11-12T00:01:00Z")
        self.assertEqual(out["future_game_count"],0)
        self.assertEqual(out["research_player_count"],0)

    def test_player_games_after_fixture_are_not_used(self):
        f,s,i=sources()
        f["players"][0]["log"].append(["2026-11-12","NYK",20,39])
        self.assertEqual(capture(f,s,i,frozen_at=FREEZE)["research_player_count"],0)

    def test_duplicate_player_ids_rejected(self):
        f,s,i=sources()
        f["players"].append(copy.deepcopy(f["players"][0]))
        self.assertEqual(capture(f,s,i,frozen_at=FREEZE)["research_player_count"],0)

    def test_injury_status_for_other_day_must_not_attach(self):
        f,s,i=sources()
        i["players"][0]["game_date"]="2026-11-10"
        self.assertEqual(capture(f,s,i,frozen_at=FREEZE)["research_players"][0]["injury_status"],"UNKNOWN_NOT_LISTED")

    def test_conflicting_injuries_do_not_attach(self):
        f,s,i=sources()
        other=copy.deepcopy(i["players"][0]);other["status"]="Out";i["players"].append(other)
        self.assertEqual(capture(f,s,i,frozen_at=FREEZE)["research_player_count"],0)

    def test_missing_source_url_rejected(self):
        f,s,i=sources()
        f["source_url"]=None
        with self.assertRaises(ValueError):capture(f,s,i,frozen_at=FREEZE)

if __name__=="__main__":
    unittest.main()
