import unittest
from iphone_bot.dnp_settlement import apply_verified_dnp

SOURCE={"status":"MANUALLY_VERIFIED_DNP_FROM_PUBLISHED_TEAM_OR_NBA_REPORTS",
        "records":[{"date_eastern":"2026-11-07",
                    "game":"Orlando Magic @ Golden State Warriors",
                    "team":"ORL","player_id":"1630217","player":"Desmond Bane",
                    "source_url":"https://www.nba.com/magic/news/verified",
                    "reason":"Ruled out before tipoff"}]}

def pick(status="PENDING",player="Desmond Bane"):
    return {"status":status,"event_start":"2026-11-08T01:40:00Z",
            "captured_at":"2026-11-07T20:00:00Z",
            "game":"Orlando Magic @ Golden State Warriors",
            "team":"ORL","player_id":"1630217","player":player,
            "market":"PTS","line":20.5,"side":"OVER"}

class VerifiedDNPTests(unittest.TestCase):
    def test_exact_game_and_player_voids_no_result_inferred(self):
        rows=apply_verified_dnp([pick()],SOURCE,now="2026-11-08T05:00:00Z")
        self.assertEqual(rows[0]["status"],"VOID_DNP")
        self.assertEqual(rows[0]["result"],"VOID")
        self.assertNotIn("actual",rows[0])
        self.assertEqual(rows[0]["line"],20.5)

    def test_same_name_wrong_identity_or_event_not_voided(self):
        wrong=pick()
        wrong["player_id"]="other"
        self.assertEqual(apply_verified_dnp([wrong],SOURCE,now="2026-11-08T05:00:00Z")[0]["status"],"PENDING")
        self.assertEqual(apply_verified_dnp([pick("PENDING","Another Bane")],SOURCE,now="2026-11-08T05:00:00Z")[0]["status"],"PENDING")

    def test_prior_settled_and_future_picks_immutable(self):
        self.assertEqual(apply_verified_dnp([pick("SETTLED")],SOURCE,now="2026-11-08T05:00:00Z")[0]["status"],"SETTLED")
        self.assertEqual(apply_verified_dnp([pick()],SOURCE,now="2026-11-07T23:00:00Z")[0]["status"],"PENDING")

    def test_reject_fake_evidence_or_duplicate_identity(self):
        bad={"status":SOURCE["status"],"records":[dict(SOURCE["records"][0],source_url="https://not-nba.example/")]}
        with self.assertRaises(ValueError):apply_verified_dnp([pick()],bad)
        duplicate={"status":SOURCE["status"],"records":SOURCE["records"]*2}
        with self.assertRaises(ValueError):apply_verified_dnp([pick()],duplicate)

if __name__=="__main__":unittest.main()
