"""Offline checks for bounded PrizePicks targeted acquisition selection.

No paid provider requests or production quotes are used in these tests.
"""
import unittest
from datetime import datetime,timedelta,timezone

from iphone_bot.fetch_prizepicks import targeted_team_searches

NOW=datetime(2026,11,9,12,tzinfo=timezone.utc)

def fixture(name,hours):
    return {"game":name,"start":(NOW+timedelta(hours=hours)).isoformat()}

class TargetedSelection(unittest.TestCase):
    def test_only_verified_near_tipoff_missing_teams(self):
        games=[
            fixture("Boston Celtics @ Milwaukee Bucks",4),
            fixture("LA Clippers @ Phoenix Suns",6),
            fixture("Miami Heat @ Utah Jazz",10),
            fixture("Orlando Magic @ Sacramento Kings",30),
        ]
        board={"board_offers":[{"game":"Boston Celtics @ Milwaukee Bucks"}]}
        codes=targeted_team_searches({"games":games},board,NOW)
        self.assertEqual(codes,["LAC","PHX","MIA"])

    def test_never_spend_on_far_future_or_started(self):
        games=[fixture("LA Clippers @ Phoenix Suns",25),
               fixture("Orlando Magic @ Sacramento Kings",-1)]
        self.assertEqual(targeted_team_searches({"games":games},{},NOW),[])

    def test_missing_game_identity_not_queried(self):
        games=[fixture("Not a known matchup",2)]
        self.assertEqual(targeted_team_searches({"games":games},{},NOW),[])

    def test_no_duplicate_team_queries(self):
        games=[fixture("LA Clippers @ Phoenix Suns",3),
               fixture("LA Clippers @ Sacramento Kings",4)]
        codes=targeted_team_searches({"games":games},{},NOW,limit=9)
        self.assertEqual(codes,["LAC","PHX","SAC"])

    def test_hard_limit_and_no_schedule(self):
        games=[fixture("LA Clippers @ Phoenix Suns",3),
               fixture("Miami Heat @ Utah Jazz",4)]
        self.assertEqual(len(targeted_team_searches({"games":games},{},NOW,limit=1)),1)
        self.assertEqual(targeted_team_searches({}, {}, NOW),[])

if __name__=="__main__":
    unittest.main()
