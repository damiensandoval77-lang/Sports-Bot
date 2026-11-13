import unittest
from datetime import datetime,timezone
from iphone_bot.fetch_cbs_final_boxscores import parse_final,collect,shortname,cbs_boxscore_url

def pick(player,team="WAS"):
    return {"status":"PENDING","player":player,"team":team,
            "game":"Washington Wizards @ Atlanta Hawks",
            "event_start":"2026-11-07T00:10:00Z"}

def synthetic(final=True):
    top="FINAL" if final else "3rd quarter"
    return f"""<html><body><h1>Washington Wizards at Atlanta Hawks</h1>
    <div>WAS 132 {top} ATL 139 · Nov. 6</div>
    <table><tr><th>Starters</th><th>PTS</th><th>REB</th><th>AST</th><th>MIN</th></tr>
      <tr><td>K. George</td><td>33</td><td>4</td><td>7</td><td>40</td></tr>
      <tr><td>T. Young</td><td>23</td><td>2</td><td>10</td><td>36</td></tr>
      <tr><td>A. Sarr</td><td>13</td><td>8</td><td>3</td><td>30</td></tr>
    </table>
    <table><tr><th>Starters</th><th>PTS</th><th>REB</th><th>AST</th><th>MIN</th></tr>
      <tr><td>D. Daniels</td><td>13</td><td>9</td><td>12</td><td>34</td></tr>
      <tr><td>O. Okongwu</td><td>22</td><td>10</td><td>1</td><td>33</td></tr>
      <tr><td>L. Dort</td><td>25</td><td>7</td><td>4</td><td>32</td></tr>
    </table></body></html>"""

def records():
    return [pick("Kyshawn George"),pick("Trae Young"),pick("Alex Sarr"),
            pick("Dyson Daniels","ATL"),pick("Onyeka Okongwu","ATL"),
            pick("Luguentz Dort","ATL")]

class CBSFallbackTests(unittest.TestCase):
    def test_exact_short_name_resolves_without_fuzzy_identity(self):
        self.assertEqual(shortname("K. George"),shortname("Kyshawn George"))
        self.assertNotEqual(shortname("K. George"),shortname("A. George"))

    def test_final_only_with_both_teams_and_matched_player(self):
        actual=parse_final(synthetic(),"2026-11-06","WAS","ATL",records())
        self.assertEqual(len(actual),6)
        self.assertTrue(all(x["final_confirmed"] is True for x in actual))
        self.assertEqual(next(x for x in actual if x["player"]=="Trae Young")["PRA"],35)
        self.assertEqual(parse_final(synthetic(False),"2026-11-06","WAS","ATL",records()),[])

    def test_missing_opponent_or_roster_fails_closed(self):
        self.assertEqual(parse_final(synthetic(),"2026-11-06","BOS","CHA",records()),[])
        self.assertEqual(parse_final(synthetic(),"2026-11-06","WAS","ATL",records()[:2]),[])

    def test_collector_queries_single_game_and_finds_final(self):
        urls=[]
        def grab(url):
            urls.append(url)
            return synthetic()
        result,status=collect(records(),now=datetime(2026,11,7,6,tzinfo=timezone.utc),request=grab)
        self.assertEqual(len(result),6)
        self.assertEqual(status["finished_matchups"],1)
        self.assertTrue(urls[0].endswith("NBA_20261106_WAS%40ATL/"))
    def test_cbs_uses_verified_short_url_codes(self):
        self.assertTrue(cbs_boxscore_url("2026-11-07","NYK","CLE").endswith(
            "NBA_20261107_NY%40CLE/"))
        self.assertTrue(cbs_boxscore_url("2026-11-07","ORL","GSW").endswith(
            "NBA_20261107_ORL%40GS/"))
        self.assertTrue(cbs_boxscore_url("2026-11-06","WAS","ATL").endswith(
            "NBA_20261106_WAS%40ATL/"))

    def test_cbs_live_route_recovers_from_boxscore_404(self):
        urls=[]
        def fetch(url):
            urls.append(url)
            if "/boxscore/" in url:raise OSError("HTTP 404")
            return synthetic()
        found,status=collect(records(),now=datetime(2026,11,7,6,tzinfo=timezone.utc),
                             request=fetch)
        self.assertEqual(len(found),6)
        self.assertEqual(status["finished_matchups"],1)
        self.assertEqual(len(urls),2)
        self.assertIn("/live/",urls[-1])

    def test_no_pending_projections_no_network(self):
        def forbidden(_):
            raise AssertionError("Cannot search unrelated games")
        self.assertEqual(collect([],request=forbidden)[0],[])

if __name__=="__main__":unittest.main()
