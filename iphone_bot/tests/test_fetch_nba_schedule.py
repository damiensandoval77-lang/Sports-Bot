"""Third-party NBA schedule parses Eastern calendar and live/finished games."""
import datetime as dt
import unittest
from iphone_bot.fetch_nba_schedule import collect,parse_event,EASTERN


def event(id="1",start="2026-11-07T00:30:00Z",state="pre"):
    return {"id":id,"date":start,
            "competitions":[{"competitors":[
                {"homeAway":"away","team":{"displayName":"Boston Celtics","abbreviation":"BOS"}},
                {"homeAway":"home","team":{"displayName":"Charlotte Hornets","abbreviation":"CHA"}}]}],
            "status":{"type":{"state":state}}}


class ScheduleTests(unittest.TestCase):
    def test_eastern_date_and_complete_status(self):
        day=dt.date(2026,11,6)
        row=parse_event(event(state="in"),day)
        self.assertEqual(row["date_eastern"],"2026-11-06")
        self.assertEqual(row["game_state"],"in")
        self.assertEqual(row["game"],"Boston Celtics @ Charlotte Hornets")
        self.assertIsNone(parse_event(event(),day+dt.timedelta(days=1)))

    def test_completed_events_are_not_dropped(self):
        day=dt.date(2026,11,6)
        rows=collect([day],lambda _: [event("1",state="post"),
                                     event("2",state="in"),
                                     event("3",state="pre")])
        self.assertEqual(rows["total_games"],3)
        self.assertEqual({g["game_state"] for g in rows["games"]},{"post","in","pre"})
        self.assertFalse(rows["has_sportsbook_props"])
        self.assertFalse(rows["has_verified_player_availability"])

    def test_invalid_events_are_not_invented(self):
        day=dt.date(2026,11,6)
        result=collect([day],lambda _: [event(),{"id":"bad"}])
        self.assertEqual(result["total_games"],1)
        self.assertEqual(result["source_records_rejected"],1)

    def test_next_day_is_separate(self):
        today=dt.date(2026,11,6)
        tomorrow=today+dt.timedelta(days=1)
        a=event("A",start="2026-11-07T00:30:00Z")
        b=event("B",start="2026-11-08T00:30:00Z")
        result=collect([today,tomorrow],lambda _: [a,b])
        self.assertEqual(result["total_games"],2)
        self.assertEqual({g["date_eastern"] for g in result["games"]},
                         {"2026-11-06","2026-11-07"})


if __name__=="__main__":unittest.main()
