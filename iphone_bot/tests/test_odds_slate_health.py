import unittest
from datetime import datetime,timezone,timedelta
from iphone_bot.odds_slate_health import report

NOW=datetime(2026,11,7,19,0,tzinfo=timezone.utc)
GAME1="Denver Nuggets @ Indiana Pacers"
GAME2="Brooklyn Nets @ Atlanta Hawks"
GAME3="New York Knicks @ Cleveland Cavaliers"
START="2026-11-08T01:00:00Z"

def schedule():
    return {"source":"Independent NBA schedule","coverage_complete":False,
            "games":[{"game":game,"date_eastern":"2026-11-07",
                      "start":START,"game_state":"pre"}
                     for game in (GAME1,GAME2,GAME3)]}

def odds():
    return {"updated_at":"2026-11-07T18:45:00Z","events_covered":[{"game":GAME1},{"game":GAME2}],
       "picks":[{"game":GAME1,"start":START,"player":"Player",
                 "stat":"Points","line":20.5,"source":"FanDuel","direction":d}
                 for d in ("More","Less")]}

class CoverageTests(unittest.TestCase):
    def test_real_pairs_only_and_partial_independent_slate(self):
        r=report(schedule(),odds(),{"status":"FETCHED","details":{"available_events":2,"checked_events":2}},now=NOW)
        self.assertEqual(r["scheduled_today"],3)
        self.assertEqual(r["upcoming_with_fresh_props"],1)
        self.assertEqual(r["upcoming_missing_fresh_props"],2)
        self.assertEqual([g["coverage"] for g in r["games"]],
                         ["FRESH_VERIFIED_PAIRED_PROPS",
                          "NO_PAIRED_PROPS_IN_LAST_PROVIDER_SNAPSHOT",
                          "NOT_CHECKED_OR_ABSENT_FROM_PROVIDER_FEED"])
        self.assertFalse(r["schedule_coverage_complete"])

    def test_low_credits_are_cause_not_zero_real_world_games(self):
        s={"status":"CREDITS_BELOW_RESERVE_PRESERVED","details":{
           "available_events":12,"checked_events":0,"remaining_credits":11,
           "minimum_reserved_credits":12}}
        r=report(schedule(),{"updated_at":"2026-11-07T17:00:00Z","picks":[]},s,now=NOW)
        self.assertEqual(r["upcoming_missing_fresh_props"],3)
        self.assertEqual(r["by_coverage"]["ODDS_CREDIT_RESERVE_BLOCKED"],3)
        self.assertEqual(r["remaining_provider_credits"],11)
        self.assertEqual(r["provider_events_reported"],12)
        self.assertTrue(r["no_new_provider_requests_made"])

    def test_legacy_fetched_zero_events_with_low_credits_corrected(self):
        # Published metadata from a historical run: 12 upcoming games,
        # no event detail requests, 11 remaining vs a 12-credit reserve.
        legacy={"status":"FETCHED","details":{
            "available_events":12,"checked_events":0,"remaining_credits":"11"}}
        r=report(schedule(),{"updated_at":"2026-11-07T18:45:00Z",
                  "events_covered":[],"picks":[]},legacy,now=NOW)
        self.assertEqual(r["provider_status"],"LEGACY_ZERO_EVENT_FETCH_CREDIT_RESERVE")
        self.assertEqual(r["reserved_credits"],12)
        self.assertEqual(r["by_coverage"]["ODDS_CREDIT_RESERVE_BLOCKED"],3)
        self.assertEqual(r["upcoming_with_fresh_props"],0)

    def test_stale_feed_does_not_claim_verified_live(self):
        expired=odds()
        expired["updated_at"]="2026-11-06T18:45:00Z"
        r=report(schedule(),expired,{"status":"FETCHED"},now=NOW)
        self.assertEqual(r["upcoming_with_fresh_props"],0)
        self.assertFalse(r["paired_quotes_fresh"])
        self.assertEqual(r["by_coverage"]["STALE_OR_MISSING_ODDS_SNAPSHOT"],3)

    def test_one_sided_is_not_live_and_started_does_not_need_new_prop(self):
        partial=odds()
        partial["picks"]=partial["picks"][:1]
        sample=schedule()
        sample["games"][0]["start"]="2026-11-07T18:00:00Z"
        r=report(sample,partial,{"status":"FETCHED"},now=NOW)
        self.assertEqual(r["upcoming_scheduled"],2)
        self.assertEqual(r["games"][0]["coverage"],"STARTED_OR_FINISHED_NO_NEW_PREGAME_MARKET")
        self.assertEqual(r["upcoming_with_fresh_props"],0)

    def test_archived_projections_not_misrepresented_as_fresh_lines(self):
        archive={"status":"FROZEN_PREGAME_HISTORICAL_ARCHIVE_NOT_LIVE",
                 "date_eastern":"2026-11-07","comparisons":[{"game":GAME2}]}
        r=report(schedule(),{},{"status":"MISSING_ODDS_API_KEY"},
                 archive=archive,now=NOW)
        self.assertTrue(r["games"][1]["has_historical_pregame_ai"])
        self.assertFalse(r["games"][1]["live_betting_lines_verified"])

if __name__=="__main__":unittest.main()
