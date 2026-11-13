"""Full slate availability, per-player balance and provider budget protections."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from iphone_bot import fetch_props


def fixture_event(i):
    # This is an UPCOMING-event fixture. A hardcoded Nov 8 timestamp made
    # the credit-budget test silently select zero events after that date,
    # giving a misleading failed pipeline even with the correct publisher.
    kickoff=fetch_props.dt.datetime.now(fetch_props.dt.timezone.utc)+fetch_props.dt.timedelta(hours=3)
    return {"id":str(i),"commence_time":kickoff.isoformat(),
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

    def test_compact_feed_keeps_verified_pairs_from_all_games(self):
        events=[fixture_event(i) for i in range(5)]
        picks=[]
        covered=[]
        for event in events:
            rows=fetch_props.balanced_bookmaker_rows(
                [bookmaker([f"Player {event['id']}",f"Bench {event['id']}"])],
                event,100)
            picks.extend(rows)
            covered.append({"game":event["away_team"]+" @ "+event["home_team"],
                            "start":event["commence_time"],
                            "two_sided_outcomes":len(rows)})
        report={"is_live":True,"updated_at":"2026-11-07T00:00+00:00",
                "slate_events_available":5,"slate_events_checked":5,
                "slate_events_not_checked":0,"events_covered":covered,"picks":picks}
        compact=fetch_props.compact_for_dashboard(report,max_pairs_per_event=1)
        self.assertEqual(len(compact["events_covered"]),5)
        self.assertEqual(len(compact["picks"]),10)
        self.assertEqual({x["game"] for x in compact["picks"]},
                         {x["game"] for x in covered})
        self.assertTrue(all(x["published_two_sided_pairs"]==1
                            for x in compact["events_covered"]))
        self.assertTrue(all(compact["picks"][i]["direction"]=="More" and
                            compact["picks"][i+1]["direction"]=="Less"
                            for i in range(0,len(compact["picks"]),2)))

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
                patch.dict(fetch_props.os.environ,{"ODDS_API_KEY":"dummy","SPORTS_BOT_ENABLE_PAID_ODDS":"1"}),\
                patch.object(fetch_props,"request",side_effect=fake):
            fetch_props.main()
            report=json.loads((Path(temp)/"out.json").read_text())
        self.assertEqual(report["slate_events_available"],6)
        self.assertEqual(report["slate_events_checked"],6)
        self.assertEqual(report["slate_events_not_checked"],0)
        self.assertEqual(len(report["events_covered"]),6)
        self.assertEqual(len(report["picks"]),12)

    def test_below_credit_reserve_never_requests_paid_event_props(self):
        now=fetch_props.dt.datetime.now(fetch_props.dt.timezone.utc)
        event=fixture_event(1)
        event["commence_time"]=(now+fetch_props.dt.timedelta(hours=3)).isoformat()
        calls=[]
        def fake(path,key,**kwargs):
            calls.append(path)
            return [event],11
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            original='{"picks":[{"player":"Real"}]}'
            (root/"out.json").write_text(original)
            (root/"compact.json").write_text(original)
            with patch.object(fetch_props,"OUT",root/"out.json"),\
                 patch.object(fetch_props,"COMPACT",root/"compact.json"),\
                 patch.object(fetch_props,"STATUS",root/"status.json"),\
                 patch.dict(fetch_props.os.environ,{"ODDS_API_KEY":"dummy","SPORTS_BOT_ENABLE_PAID_ODDS":"1"}),\
                 patch.object(fetch_props,"request",side_effect=fake):
                fetch_props.main()
            self.assertEqual(calls,["/events"])
            self.assertEqual((root/"out.json").read_text(),original)
            self.assertEqual((root/"compact.json").read_text(),original)
            status=json.loads((root/"status.json").read_text())
            self.assertEqual(status["status"],"CREDITS_BELOW_RESERVE_PRESERVED")
            self.assertEqual(status["details"]["available_events"],1)
            self.assertEqual(status["details"]["remaining_credits"],11)

    def test_no_upcoming_event_does_not_erase_prior_real_quotes(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            prior='{"picks":[{"player":"Real pregame quote"}]}\\n'
            (root/"out.json").write_text(prior)
            (root/"compact.json").write_text('{"picks":[{"player":"Real"}]}')
            with patch.object(fetch_props,"OUT",root/"out.json"),\
                 patch.object(fetch_props,"COMPACT",root/"compact.json"),\
                 patch.object(fetch_props,"STATUS",root/"status.json"),\
                 patch.dict(fetch_props.os.environ,{"ODDS_API_KEY":"dummy","SPORTS_BOT_ENABLE_PAID_ODDS":"1"}),\
                 patch.object(fetch_props,"request",return_value=([],500)):
                fetch_props.main()
            self.assertEqual((root/"out.json").read_text(),prior)
            self.assertIn('"Real"',(root/"compact.json").read_text())
            self.assertEqual(json.loads((root/"status.json").read_text())["status"],
                             "NO_UPCOMING_EVENTS_PRESERVED")

    def test_no_two_sided_prices_does_not_erase_prior_real_quotes(self):
        now=fetch_props.dt.datetime.now(fetch_props.dt.timezone.utc)
        event=fixture_event(1)
        event["commence_time"]=(now+fetch_props.dt.timedelta(hours=3)).isoformat()
        def fake(path,key,**kwargs):
            if path=="/events":return [event],100
            return {"bookmakers":[]},90
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            (root/"out.json").write_text('{"picks":[{"player":"Real"}]}')
            (root/"compact.json").write_text('{"picks":[{"player":"Real"}]}')
            with patch.object(fetch_props,"OUT",root/"out.json"),\
                 patch.object(fetch_props,"COMPACT",root/"compact.json"),\
                 patch.object(fetch_props,"STATUS",root/"status.json"),\
                 patch.dict(fetch_props.os.environ,{"ODDS_API_KEY":"dummy","SPORTS_BOT_ENABLE_PAID_ODDS":"1"}),\
                 patch.object(fetch_props,"request",side_effect=fake):
                fetch_props.main()
            self.assertIn('"Real"',(root/"out.json").read_text())
            self.assertIn('"Real"',(root/"compact.json").read_text())
            self.assertEqual(json.loads((root/"status.json").read_text())["status"],
                             "NO_TWO_SIDED_PLAYER_PROPS_PRESERVED")

    def test_credit_budget_reports_partial_slate_truthfully(self):
        events=[fixture_event(i) for i in range(6)]
        def fake(path,key,**kwargs):
            if path=="/events":return events,None
            return {"bookmakers":[bookmaker(["Player"])]},10
        with tempfile.TemporaryDirectory() as temp,\
                patch.object(fetch_props,"OUT",Path(temp)/"out.json"),\
                patch.dict(fetch_props.os.environ,{"ODDS_API_KEY":"dummy","SPORTS_BOT_ENABLE_PAID_ODDS":"1"}),\
                patch.object(fetch_props,"request",side_effect=fake):
            fetch_props.main()
            report=json.loads((Path(temp)/"out.json").read_text())
        self.assertEqual(report["slate_events_checked"],1)
        self.assertEqual(report["slate_events_not_checked"],5)
        self.assertEqual(report["coverage_warning"],"PARTIAL_PROVIDER_EVENT_OR_CREDIT_COVERAGE")


if __name__=="__main__":
    unittest.main()
