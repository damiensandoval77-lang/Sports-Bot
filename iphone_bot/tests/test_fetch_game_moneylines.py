import datetime as dt
import unittest
from iphone_bot.fetch_game_moneylines import american,parse_event,build


NOW=dt.datetime(2026,11,7,0,0,tzinfo=dt.timezone.utc)


def event(start="2026-11-07T03:00:00Z"):
    return {"commence_time":start,"home_team":"Los Angeles Lakers",
       "away_team":"Portland Trail Blazers",
       "bookmakers":[{"key":"fanduel","title":"FanDuel","markets":[
         {"key":"h2h","last_update":"2026-11-06T23:50:00Z",
          "outcomes":[{"name":"Los Angeles Lakers","price":-160},
                      {"name":"Portland Trail Blazers","price":140}]}]}]}


class MoneylineTests(unittest.TestCase):
    def test_actual_two_sided_quoted_moneylines(self):
        result=build([event()],NOW)
        self.assertEqual(result["status"],"VERIFIED_PREGAME_NBA_MONEYLINES")
        self.assertEqual(len(result["games"]),1)
        book=result["games"][0]["books"][0]
        self.assertEqual((book["away_ml"],book["home_ml"]),(140,-160))
        self.assertEqual(book["sportsbook"],"FanDuel")

    def test_no_fake_lines_after_start_or_one_sided(self):
        self.assertIsNone(parse_event(event("2026-11-06T23:00:00Z"),NOW))
        only=event()
        only["bookmakers"][0]["markets"][0]["outcomes"].pop()
        self.assertIsNone(parse_event(only,NOW))

    def test_invalid_prices_and_unupdated_quotes_excluded(self):
        for value in (None,float("nan"),0,-99,99,True,"not odds"):
            self.assertIsNone(american(value))
        stale=event()
        stale["bookmakers"][0]["markets"][0]["last_update"]="2026-11-05T23:00:00Z"
        self.assertIsNone(parse_event(stale,NOW))

    def test_only_h2h_market_allowed(self):
        spread=event()
        spread["bookmakers"][0]["markets"][0]["key"]="spreads"
        self.assertIsNone(parse_event(spread,NOW))


if __name__=="__main__":unittest.main()
