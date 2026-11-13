import unittest
from iphone_bot.pra_coherence_challenger import candidates,merge

def row(stat,project,at="2026-11-09T20:00:00+00:00",id="123"):
    return {"stat":stat,"projection":project,"start":"2026-11-09T23:00:00+00:00",
      "captured_at":at,"player_id":id,"game":"BKN @ DAL","team":"DAL"}
class PraChallengerTests(unittest.TestCase):
    def test_freezes_pretip_pra_pair(self):
        rows=[row(x,y) for x,y in zip(("PTS","REB","AST","PRA"),(20,5,6,29))]
        result=candidates(rows)
        self.assertEqual(len(result),1)
        self.assertEqual(result[0]["original_pra_forecast"],29)
        self.assertEqual(result[0]["additive_pra_forecast"],31)
        self.assertTrue(result[0]["original_frozen_pretip"])
    def test_does_not_infer_after_tip_or_different_players(self):
        late="2026-11-10T00:00:00+00:00"
        rows=[row(x,y,at=late) for x,y in zip(("PTS","REB","AST","PRA"),(20,5,6,29))]
        self.assertEqual(candidates(rows),[])
        rows=[row("PTS",20),row("REB",5),row("AST",6),row("PRA",29,id="456")]
        self.assertEqual(candidates(rows),[])
    def test_immutable_prior_lock(self):
        rows=[row(x,y) for x,y in zip(("PTS","REB","AST","PRA"),(20,5,6,29))]
        old=candidates(rows)
        updated=candidates([row(x,y) for x,y in zip(("PTS","REB","AST","PRA"),(21,5,6,30))])
        result=merge(old,updated)
        self.assertEqual(len(result),1)
        self.assertEqual(result[0]["additive_pra_forecast"],31)
    def test_duplicate_conflicts_rejected(self):
        rows=[row(x,y) for x,y in zip(("PTS","REB","AST","PRA"),(20,5,6,29))]
        rows.append(row("PTS",40))
        self.assertEqual(candidates(rows),[])
if __name__=="__main__":unittest.main()
