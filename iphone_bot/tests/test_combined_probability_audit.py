import unittest
from iphone_bot.combined_probability_audit import locked,report,describe,METHOD

def pick(p=.8,game="2026-11-07T00:10:00Z"):
    return {"status":"SETTLED","captured_at":"2026-11-06T21:00:00Z",
        "event_start":game,"game":"Boston Celtics @ Charlotte Hornets",
        "player_id":"1628369","team":"BOS","player":"Jayson Tatum",
        "market":"PTS","bookmaker":"FanDuel","line":20.5,
        "combined_projection":25.,"side":"OVER","actual":34.,
        "combined_probability_proxy_estimate":p,
        "combined_probability_proxy_side":"OVER",
        "combined_probability_proxy_method":METHOD}

class CombinedProxyAuditTests(unittest.TestCase):
    def test_deduplicates_multiple_book_quotes(self):
        base=pick()
        second={**base,"bookmaker":"DraftKings","line":21.5}
        rows,excluded=locked([base,second])
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["won"],1)
    def test_no_reconstruction_from_unlocked_legacy_estimate(self):
        old=pick()
        old.pop("combined_probability_proxy_estimate")
        old["experimental_estimate"]=.99
        r=report([old])
        self.assertEqual(r["overall"]["sample_size"],0)
        self.assertEqual(r["excluded"]["no_pregame_frozen_proxy"],1)
    def test_invalid_side_and_capture_rejected(self):
        wrong=pick()
        wrong["combined_probability_proxy_side"]="UNDER"
        late=pick()
        late["captured_at"]="2026-11-07T01:00:00Z"
        self.assertEqual(report([wrong,late])["overall"]["sample_size"],0)
    def test_band_summary_and_uncertainty(self):
        rows=[{**pick(.8),"player_id":str(i)} for i in range(20)]
        result=report(rows)
        self.assertEqual(result["overall"]["sample_size"],20)
        self.assertEqual(result["overall"]["wins"],20)
        self.assertFalse(result["is_calibrated"])
        self.assertFalse(result["show_as_verified_confidence"])
        self.assertEqual(result["bands"][4]["sample_size"],20)
        self.assertFalse(result["bands"][4]["reliable"])
        self.assertLess(result["overall"]["observed_hit_rate_wilson95"][0],1)
    def test_push_is_not_a_win(self):
        x=pick()
        x["actual"]=x["line"]
        self.assertEqual(report([x])["overall"]["sample_size"],0)
        self.assertEqual(report([x])["excluded"]["push"],1)

if __name__=="__main__":unittest.main()
