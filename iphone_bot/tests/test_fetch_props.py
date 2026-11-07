"""Full slate availability, per-player balance and provider budget protections."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from iphone_bot import fetch_props


def fixture_event(i):
    return {"id":str(i),"commence_time":"2026-11-08T03:00:00Z",
            "away_team":f"Away {i}","home_team":f"Home {i}"}


def bookmaker(players):
    pairs=[]
    for player in players:
        pairs.extend([
            {"description":player,"name":"Over","point":20.5,"price":-110},
            {"description":player,"name":"Under","point":20.5,"price":-110}])
    return {"title":"TestBook","markets":[{"key":"player_points","outcomes":pairs}]}


class FetchPropsTests(unittest.TestCase):
    def test_round_robin_preserves_distinct_players_under_cap(self):
        event=fixture_event(0)
        book=bookmaker([f"Player {i}" for i in range(14)])
        got=fetch_props.balanced_bookmaker_rows([book],event,20)
        self.assertEqual(len(got),20)
        self.assertEqual(len({r["player"] for r in got}),10)
        self.assertTrue(all(sum(row["direction"]==side for row in got)==10
                            for side in ("More","Less")))

    def test_no_one_sided_markets_are_fabricated(self):
        event=fixture_event(0)
        book=bookmaker(["Player 1","Player 2"])
        book["markets"][0]["outcomes"]=[x for x in book["markets"][0]["outcomes"]
                                         if x["name"]=="Over"]
        self.assertEqual(fetch_props.balanced_bookmaker_rows([book],event,30),[])

    def test_all_provider_events_checked_when_credits_allow(self):
        events=[fixture_event(i) for i in range(6)]
        def fake(path,key,**kwargs):
            if path=="/events":return events,None
            i=int(path.split("/")[-2])
            return {"bookmakers":[bookmaker([f"Player {i}"])]},500
        with tempfile.TemporaryDirectory() as temp,\
                patch.object(fetch_props,"OUT",Path(temp)/"out.json"),\
                patch.object(fetch_props,"MAX_EVENTS",15),\
                patch.dict(fetch_props.os.environ,{"ODDS_API_KEY":"dummy"}),\
                patch.object(fetch_props,"request",side_effect=fake):
            fetch_props.main()
            report=json.loads((Path(temp)/"out.json").read_text())
        self.assertEqual(report["slate_events_available"],6)
        self.assertEqual(report["slate_events_checked"],6)
        self.assertEqual(report["slate_events_not_checked"],0)
        self.assertEqual(len(report["events_covered"]),6)
        self.assertEqual(len(report["picks"]),12)

    def test_credit_budget_reports_partial_slate_truthfully(self):
        events=[fixture_event(i) for i in range(6)]
        def fake(path,key,**kwargs):
            if path=="/events":return events,None
            return {"bookmakers":[bookmaker(["Player"])]},10
        with tempfile.TemporaryDirectory() as temp,\
                patch.object(fetch_props,"OUT",Path(temp)/"out.json"),\
                patch.dict(fetch_props.os.environ,{"ODDS_API_KEY":"dummy"}),\
                patch.object(fetch_props,"request",side_effect=fake):
            fetch_props.main()
            report=json.loads((Path(temp)/"out.json").read_text())
        self.assertEqual(report["slate_events_checked"],1)
        self.assertEqual(report["slate_events_not_checked"],5)
        self.assertEqual(report["coverage_warning"],"PARTIAL_PROVIDER_EVENT_OR_CREDIT_COVERAGE")


if __name__=="__main__":
    unittest.main()
