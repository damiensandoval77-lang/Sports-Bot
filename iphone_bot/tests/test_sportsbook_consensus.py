import unittest
from iphone_bot.sportsbook_consensus import consensus_markets
from iphone_bot.fetch_props import balanced_bookmaker_rows

class SportsbookConsensusTest(unittest.TestCase):
    def quote(self,book,line):
        return {"player":"Sample Player","player_id":"123","team":"BOS",
                "stat":"PTS","game":"Boston Celtics @ Miami Heat",
                "start":"2026-11-12T01:00:00Z","sportsbook":book,
                "line":line,"over_odds":-110,"under_odds":-110,
                "features":{"MIN_L5":30}}
    def test_median_and_book_count(self):
        rows=[self.quote("FanDuel",23.5),self.quote("DraftKings",24.5),
              self.quote("BetMGM",25.5)]
        result=consensus_markets(rows)
        self.assertEqual(len(result),1)
        self.assertEqual(result[0]["line"],24.5)
        self.assertEqual(result[0]["line_book_count"],3)
        self.assertEqual(result[0]["line_type"],"MULTIBOOK_MEDIAN")
        self.assertEqual(result[0]["line_range"],[23.5,25.5])
        self.assertEqual(len(result[0]["book_quotes"]),3)

    def test_single_is_not_misrepresented_as_consensus(self):
        result=consensus_markets([self.quote("FanDuel",23.5)])
        self.assertEqual(result[0]["line_book_count"],1)
        self.assertEqual(result[0]["line_type"],"SINGLE_BOOK_FALLBACK")

    def test_duplicate_book_cannot_dominate_median(self):
        result=consensus_markets([self.quote("FanDuel",11.5),
             self.quote("fanduel",13.5),self.quote("DraftKings",25.5)])
        self.assertEqual(result[0]["line_book_count"],2)
        self.assertEqual(result[0]["line"],18.5)

    def test_no_combining_distinct_players_or_events(self):
        a=self.quote("A",20.5)
        b=dict(self.quote("B",30.5),player_id="456")
        self.assertEqual(len(consensus_markets([a,b])),2)

    def test_book_round_robin_preserves_complete_sides(self):
        event={"away_team":"Boston Celtics","home_team":"Miami Heat",
               "commence_time":"2026-11-12T01:00:00Z"}
        books=[]
        for name in ("Book A","Book B","Book C"):
            markets=[]
            for market in ("player_points","player_rebounds"):
                outcomes=[]
                for k in range(7):
                    outcomes.extend([
                      {"name":"Over","description":"Player "+str(k),
                       "point":k+.5,"price":-110},
                      {"name":"Under","description":"Player "+str(k),
                       "point":k+.5,"price":-115}])
                markets.append({"key":market,"last_update":"2026-11-11T20:00:00Z",
                                "outcomes":outcomes})
            books.append({"title":name,"markets":markets})
        rows=balanced_bookmaker_rows(books,event,18)
        self.assertEqual(len(rows),18)
        self.assertEqual(len({r["source"] for r in rows}),3)
        self.assertEqual(len({r["stat"] for r in rows}),2)
        for i in range(0,len(rows),2):
            self.assertEqual({rows[i]["direction"],rows[i+1]["direction"]},{"More","Less"})
            self.assertEqual(rows[i]["source"],rows[i+1]["source"])

if __name__=="__main__":unittest.main()
