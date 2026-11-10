import datetime as dt
import unittest
from iphone_bot.season_schedule_baseline import (
    build,validate,reconcile_window,STATUS,START,END,ET
)

NOW=dt.datetime(2026,11,10,18,tzinfo=dt.timezone.utc)
def game(id,date="2026-11-11T01:00:00+00:00",home="BOS",away="PHI"):
    names={"BOS":"Boston Celtics","PHI":"Philadelphia 76ers",
           "OKC":"Oklahoma City Thunder","POR":"Portland Trail Blazers"}
    return {"id":str(id),"game":names[away]+" @ "+names[home],
      "home":names[home],"away":names[away],
      "home_abbreviation":home,"away_abbreviation":away,
      "start":date,"date_eastern":dt.datetime.fromisoformat(date).astimezone(ET).date().isoformat(),
      "game_state":"pre"}

def baseline():
    # Build a realistic-sized published snapshot with 30 NBA team identities.
    from iphone_bot.season_schedule_baseline import TEAMS
    codes=sorted(TEAMS);games=[]
    for n in range(1050):
        away=codes[n%30];home=codes[(n+1+(n//30)%28)%30]
        if home==away:home=codes[(n+1)%30]
        day=START+dt.timedelta(days=n%160)
        stamp=dt.datetime.combine(day,dt.time(21),tzinfo=dt.timezone.utc)
        name=lambda t:{"BOS":"Boston Celtics","PHI":"Philadelphia 76ers"}.get(t,t+" Basketball")
        games.append({"id":str(300000+n),"game":name(away)+" @ "+name(home),
            "home":name(home),"away":name(away),
            "home_abbreviation":home,"away_abbreviation":away,
            "start":stamp.isoformat(),
            "date_eastern":stamp.astimezone(ET).date().isoformat(),
            "game_state":"pre"})
    return build(games,now=NOW,source="published public season",source_url="https://example.test/fixtures")

class SeasonBaselineTests(unittest.TestCase):
    def test_full_calendar_persists_days_far_beyond_daily_window(self):
        src=baseline()
        self.assertEqual(src["status"],STATUS)
        self.assertEqual(src["total_games"],1050)
        self.assertEqual(src["teams"],30)
        self.assertEqual(validate(src),src)
        self.assertTrue(any(x["date_eastern"]=="2027-02-01" for x in src["games"]))

    def test_outage_recovers_verified_games_without_props_or_scores(self):
        src=baseline()
        day=src["games"][100]["date_eastern"]
        out=reconcile_window(src,[day],observed=[])
        self.assertEqual(out["total_games"],src["daily_counts"][day])
        self.assertEqual(out["baseline_recovered"],out["total_games"])
        self.assertTrue(all(x["home_score"] is None and x["game_state"]=="pre" for x in out["games"]))

    def test_consecutive_matchups_same_name_different_date_not_collapsed(self):
        same1=game(1,"2026-11-11T04:00:00+00:00",home="POR",away="OKC")
        same2=game(2,"2026-11-12T03:00:00+00:00",home="POR",away="OKC")
        src=build([same1,same2],now=NOW,source="fixture",source_url="https://example.test",minimum=2)
        # The private helper deliberately validates full-size cached archives
        # before use. Two synthetic rows are only for explicit build testing.
        self.assertNotEqual(src["games"][0]["id"],src["games"][1]["id"])
        self.assertNotEqual(src["games"][0]["date_eastern"],src["games"][1]["date_eastern"])

    def test_corrupt_and_truncated_archives_fail_closed(self):
        src=baseline()
        bad={**src,"total_games":20}
        with self.assertRaises(ValueError):validate(bad)
        duplicate={**src,"games":[*src["games"][:-1],src["games"][0]]}
        with self.assertRaises(ValueError):validate(duplicate)
        bad_team={**src,"games":[{**src["games"][0],"home_abbreviation":"XXX"},*src["games"][1:]]}
        with self.assertRaises(ValueError):validate(bad_team)

    def test_legitimate_daily_update_preserves_verified_score_and_id(self):
        src=baseline()
        original=src["games"][100]
        day=original["date_eastern"]
        latest={**original,"id":"updated-"+original["id"],"game_state":"in",
                "away_score":81,"home_score":85}
        out=reconcile_window(src,[day],observed=[latest])
        self.assertIn("updated-"+original["id"],{x["id"] for x in out["games"]})
        self.assertNotIn(original["id"],{x["id"] for x in out["games"]})
        self.assertEqual(next(x for x in out["games"] if x["id"]==latest["id"])["home_score"],85)

    def test_offseason_and_cup_placeholder_are_never_fabricated(self):
        src=baseline()
        empty=reconcile_window(src,["2027-04-20"])
        self.assertEqual(empty["games"],[])
        self.assertEqual(empty["total_games"],0)

if __name__=="__main__":
    unittest.main()
