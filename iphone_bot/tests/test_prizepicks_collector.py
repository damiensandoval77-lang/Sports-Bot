import datetime as dt
import unittest
from iphone_bot.collect_prizepicks_board import collect

NOW=dt.datetime(2026,11,9,12,tzinfo=dt.timezone.utc)

def offer(id="pp_1"):
    return {"id":id,"is_demo":False,"player":{"id":"11","name":"Example Player","team":"BOS"},
            "event":{"starts_at":"2026-11-09T23:00:00Z","opponent":"NYK"},
            "market":{"stat":"Points","period":"Full game"},"line":20.5,
            "selections":[{"side":"more","tier":"standard","available":True},
                          {"side":"less","tier":"standard","available":True}],
            "status":"active","observed_at":"2026-11-09T11:59:00Z"}

class PrizePicksCollectorTests(unittest.TestCase):
    def test_single_page_complete(self):
        result=collect(lambda _:{"data":[offer()],"meta":{"mode":"live","source_status":"fresh",
                          "next_cursor":None,"observed_at":"2026-11-09T11:59:00Z"}},now=NOW)
        self.assertEqual(result["status"],"VERIFIED_NBA_PRIZEPICKS_SNAPSHOT")
        self.assertTrue(result["complete_pagination"])
        self.assertEqual(result["rows"][0]["line"],20.5)
        self.assertFalse(result["is_ai_projection"])

    def test_two_pages_deduplicate(self):
        cursors=[]
        def fetch(c):
            cursors.append(c)
            if c is None:
                return {"data":[offer()],"meta":{"source_status":"fresh","next_cursor":"next"}}
            return {"data":[offer(),offer("pp_2")],"meta":{"source_status":"fresh","next_cursor":None}}
        r=collect(fetch,max_pages=2,now=NOW)
        self.assertEqual(cursors,[None,"next"])
        self.assertEqual(len(r["rows"]),2)

    def test_page_budget_reports_partial_not_full(self):
        r=collect(lambda _:{"data":[offer()],"meta":{"source_status":"fresh",
                  "next_cursor":"more"}},max_pages=1,now=NOW)
        self.assertFalse(r["complete_pagination"])
        self.assertEqual(r["status"],"PARTIAL_NBA_PRIZEPICKS_SNAPSHOT")

    def test_reject_demo(self):
        item=offer()
        item["is_demo"]=True
        with self.assertRaises(ValueError):
            collect(lambda _:{"data":[item],"meta":{"source_status":"fresh","next_cursor":None}},now=NOW)

    def test_reject_stale(self):
        with self.assertRaises(ValueError):
            collect(lambda _:{"data":[offer()],"meta":{"source_status":"stale","next_cursor":None}},now=NOW)

    def test_reject_repeated_cursor(self):
        with self.assertRaises(ValueError):
            collect(lambda _:{"data":[offer()],"meta":{"source_status":"fresh",
                      "next_cursor":"same"}},max_pages=3,now=NOW)

    def test_invalid_line_not_fabricated(self):
        item=offer()
        item["line"]=None
        r=collect(lambda _:{"data":[item],"meta":{"source_status":"fresh","next_cursor":None}},now=NOW)
        self.assertEqual(r["rows"],[])

if __name__=="__main__":
    unittest.main()
