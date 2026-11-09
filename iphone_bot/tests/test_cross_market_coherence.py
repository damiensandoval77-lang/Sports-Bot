import unittest
from iphone_bot.cross_market_coherence import audit

START="2026-11-10T00:00:00+00:00"
BEFORE="2026-11-09T22:00:00+00:00"
AFTER="2026-11-10T01:00:00+00:00"
def sample(stat,value,at=BEFORE,player="123",team="DAL"):
    return {"stat":stat,"projection":value,"start":START,
            "captured_at":at,"player_id":player,"player":"Example",
            "game":"Brooklyn Nets @ Dallas Mavericks","team":team}

class CrossMarketCoherenceTests(unittest.TestCase):
    def test_four_market_sum(self):
        rows=[sample(k,v) for k,v in zip(("PTS","REB","AST","PRA"),(20.2,6.1,4.0,30.3))]
        r=audit(rows)
        self.assertEqual(r["groups_checked"],1)
        self.assertEqual(r["groups_inconsistent"],0)
    def test_inconsistent_pra_is_reported_not_changed(self):
        rows=[sample(k,v) for k,v in zip(("PTS","REB","AST","PRA"),(20,6,4,39))]
        original=[dict(x) for x in rows]
        r=audit(rows)
        self.assertEqual(r["groups_inconsistent"],1)
        self.assertEqual(r["largest_discrepancies"][0]["pra_minus_components"],9)
        self.assertEqual(rows,original)
        self.assertFalse(r["settled_hit_rate_improvement_claimed"])
    def test_no_posttip_prediction_leakage(self):
        rows=[sample(k,v,AFTER) for k,v in zip(("PTS","REB","AST","PRA"),(20,6,4,30))]
        self.assertEqual(audit(rows)["groups_checked"],0)
    def test_no_merging_across_capture_or_player_or_team(self):
        rows=[sample("PTS",20),sample("REB",6),sample("AST",4),
              sample("PRA",30,player="999"),sample("PRA",30,team="BKN")]
        self.assertEqual(audit(rows)["groups_checked"],0)
    def test_conflicting_duplicates_rejected(self):
        rows=[sample(k,v) for k,v in zip(("PTS","REB","AST","PRA"),(20,6,4,30))]
        rows.append(sample("PTS",99))
        self.assertEqual(audit(rows)["groups_checked"],0)
if __name__=="__main__":unittest.main()
