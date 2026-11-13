import datetime as dt
import unittest
from iphone_bot.fetch_prizepicks import clean,match,publish,quota_guard,standard_query

NOW=dt.datetime(2026,11,6,19,0,tzinfo=dt.timezone.utc)
START="2026-11-07T00:30:00Z"

def fixture():
    return {"id":"pp_123","source":"prizepicks","is_demo":False,"league":"NBA","status":"active",
            "player":{"name":"Sample Player","team":"BOS"},
            "event":{"opponent":"MIA","starts_at":START},
            "market":{"stat":"Points","period":"Full game"},
            "line":23.5,"observed_at":"2026-11-06T18:30:00Z",
            "selections":[{"side":"more","available":True,"tier":"standard"},
                          {"side":"less","available":True,"tier":"standard"}]}

COMP={"player":"Sample Player","team":"BOS","game":"Boston Celtics @ Miami Heat",
      "start":START,"stat":"PTS","projection":22.8,"combined_projection":24.0}

class PrizePicksTests(unittest.TestCase):
    def test_standard_provider_server_filter_limits_all_paid_page_scopes(self):
        page=standard_query()
        self.assertEqual(page["tier"],"standard")
        self.assertEqual(page["league"],"NBA")
        self.assertEqual(page["status"],"active")
        self.assertEqual(page["view"],"compact")
        self.assertEqual(page["limit"],1000)
        cursor=standard_query(cursor="pp_next")
        self.assertEqual(cursor["tier"],"standard")
        self.assertEqual(cursor["cursor"],"pp_next")
        targeted=standard_query(search="OKC",limit=200)
        self.assertEqual(targeted["tier"],"standard")
        self.assertEqual(targeted["search"],"OKC")
        with self.assertRaises(ValueError):standard_query(limit=1001)

    def test_zero_balance_blocks_scheduled_paid_call(self):
        old={"status":"LIVE_THIRD_PARTY_PRIZEPICKS_LINES",
             "generated_at":"2026-11-08T01:37:00Z",
             "remaining_provider_credits":0,"board_offers":[fixture()]}
        health={"status":"API_ACCESS_CONFIRMED","checked_at":"2026-11-08T01:22:00Z"}
        self.assertEqual(quota_guard(old,health,dt.datetime(2026,11,8,2,tzinfo=dt.timezone.utc)),
                         "ZERO_PROVIDER_CREDITS_PRESERVE")

    def test_verified_topup_purchased_access_allows_one_bounded_refresh(self):
        old={"status":"LIVE_THIRD_PARTY_PRIZEPICKS_LINES",
             "generated_at":"2026-11-08T08:37:00Z",
             "remaining_provider_credits":0}
        after={"status":"LIVE_READ_SUCCEEDED","checked_at":"2026-11-08T10:02:00Z",
          "http_status":200,"provider_mode":"live",
          "provider_source_status":"fresh","returned_rows":100,"request_cost":1}
        when=dt.datetime(2026,11,8,10,10,tzinfo=dt.timezone.utc)
        self.assertEqual(quota_guard(old,{},when,topup=after),"TOPUP_REFRESH_COOLDOWN_PRESERVE")
        day_later=when+dt.timedelta(hours=24)
        self.assertEqual(quota_guard(old,{},day_later,topup=after),"TOPUP_PAID_READ_CONFIRMED")
        self.assertEqual(quota_guard(old,{},when,topup={**after,"status":"HTTP_ERROR"}),
                         "ZERO_PROVIDER_CREDITS_PRESERVE")
        self.assertEqual(quota_guard(old,{},when,topup={**after,"provider_mode":"demo"}),
                         "ZERO_PROVIDER_CREDITS_PRESERVE")
        self.assertEqual(quota_guard(old,{},when+dt.timedelta(hours=3),topup=after),
                         "TOPUP_REFRESH_COOLDOWN_PRESERVE")
        self.assertEqual(quota_guard(old,{},when+dt.timedelta(hours=7),topup=after),
                         "TOPUP_PAID_READ_CONFIRMED")
        updated={**old,"generated_at":"2026-11-08T10:30:00Z"}
        self.assertEqual(quota_guard(updated,{},when+dt.timedelta(hours=1),topup=after),
                         "TOPUP_REFRESH_COOLDOWN_PRESERVE")

    def test_topup_proof_expires_and_never_authorizes_unlimited_spending(self):
        old={"status":"LIVE_THIRD_PARTY_PRIZEPICKS_LINES",
            "generated_at":"2026-11-08T01:37:00Z",
            "remaining_provider_credits":0}
        probe={"status":"LIVE_READ_SUCCEEDED","checked_at":"2026-11-08T10:02:00Z",
               "http_status":200,"provider_mode":"live",
               "provider_source_status":"fresh","returned_rows":100,"request_cost":1}
        expired=dt.datetime(2026,12,10,12,tzinfo=dt.timezone.utc)
        self.assertEqual(quota_guard(old,{},expired,topup=probe),
                         "MONTH_ROLLOVER_RECHECK_ALLOWED")

    def test_newer_confirmed_replenishment_unlocks(self):
        old={"status":"LIVE_THIRD_PARTY_PRIZEPICKS_LINES",
             "generated_at":"2026-11-08T01:37:00Z",
             "remaining_provider_credits":0}
        health={"status":"API_ACCESS_CONFIRMED","checked_at":"2026-11-08T03:15:00Z"}
        self.assertEqual(quota_guard(old,health,dt.datetime(2026,11,8,4,tzinfo=dt.timezone.utc)),
                         "REPLENISHED_ACCESS_CONFIRMED")

    def test_month_change_allows_one_new_credit_check(self):
        old={"status":"LIVE_THIRD_PARTY_PRIZEPICKS_LINES",
             "generated_at":"2026-11-08T01:37:00Z",
             "remaining_provider_credits":0}
        self.assertEqual(quota_guard(old,{},dt.datetime(2026,12,1,2,tzinfo=dt.timezone.utc)),
                         "MONTH_ROLLOVER_RECHECK_ALLOWED")

    def test_previous_429_fails_closed_without_new_health(self):
        old={"status":"PROVIDER_RATE_LIMITED",
             "provider_error_code":"MONTHLY_QUOTA_EXCEEDED",
             "generated_at":"2026-11-06T23:29:58Z"}
        self.assertEqual(quota_guard(old,{"status":"API_ACCESS_CONFIRMED",
             "checked_at":"2026-11-05T01:22:00Z"},
             dt.datetime(2026,11,8,2,tzinfo=dt.timezone.utc)),
             "QUOTA_LOCKED_PRESERVE")

    def test_real_board_match(self):
        offer=clean(fixture(),NOW)
        self.assertTrue(match(offer,COMP,NOW))
        p=publish([{"data":[fixture()],"meta":{"mode":"live","source_status":"fresh","next_cursor":None}}],[COMP],NOW)
        self.assertEqual(p["matched_count"],1)
        self.assertEqual(p["offers"][0]["ai_direction"],"MORE")
        self.assertEqual(p["offers"][0]["more_tier"],"standard")

    def test_reject_demo_and_bad_period(self):
        demo=fixture();demo["is_demo"]=True
        self.assertIsNone(clean(demo,NOW))
        wrong=fixture();wrong["market"]["period"]="First Half"
        self.assertIsNone(clean(wrong,NOW))

    def test_unknown_opponent_uses_exact_tipoff(self):
        data=fixture();data["event"].pop("opponent")
        offer=clean(data,NOW)
        self.assertTrue(match(offer,COMP,NOW))
        later=dict(COMP,start="2026-11-07T01:10:00Z")
        self.assertFalse(match(offer,later,NOW))

    def test_demon_one_way(self):
        data=fixture();data["selections"]=[{"side":"more","available":True,"tier":"demon"}]
        offer=clean(data,NOW)
        self.assertEqual(offer["more_tier"],"demon")
        self.assertIsNone(offer["less_tier"])

    def test_actual_compact_schema_uses_starts_at_and_sides_not_selections(self):
        flat={"id":"pp_compact_1","league":"NBA","status":"active",
            "player":"Sample Player","team":"BOS","opponent":"MIA",
            "stat":"Points","period":"Full game","line":23.5,
            "starts_at":START,"observed_at":"2026-11-06T18:30:00Z",
            "tier":"standard","sides":["more","less"]}
        offer=clean(flat,NOW,verified_live=True)
        self.assertIsNotNone(offer)
        self.assertEqual(offer["starts_at"],"2026-11-07T00:30:00+00:00")
        self.assertEqual((offer["more_tier"],offer["less_tier"]),("standard","standard"))
        p=publish([{"data":[flat],"meta":{"mode":"live","source_status":"fresh",
            "next_cursor":None}}],[],NOW,schedule={"games":[{"game":
            "Boston Celtics @ Miami Heat","start":START}]})
        self.assertEqual(p["independent_board_count"],1)

    def test_compact_demon_one_side_only_not_fake_under(self):
        data={"id":"pp_compact_2","league":"NBA","status":"active",
              "player":"Sample Player","team":"BOS","opponent":"MIA",
              "stat":"Assists","period":"Full game","line":6.5,
              "starts_at":START,"observed_at":"2026-11-06T18:30:00Z",
              "tier":"demon","sides":["more"]}
        offer=clean(data,NOW,verified_live=True)
        self.assertEqual(offer["more_tier"],"demon")
        self.assertIsNone(offer["less_tier"])
        data["sides"]=[]
        self.assertIsNone(clean(data,NOW,verified_live=True))

    def test_compact_flat_row_with_verified_live_provenance(self):
        compact={"id":"pp_flat_1","league":"NBA","status":"active",
            "player":"Sample Player","team":"BOS","opponent":"MIA",
            "stat":"Points","period":"Full game","line":23.5,
            "event_starts_at":START,"observed_at":"2026-11-06T18:30:00Z",
            "more_available":True,"more_tier":"standard",
            "less_available":True,"less_tier":"standard"}
        self.assertIsNone(clean(compact,NOW,verified_live=False))
        offer=clean(compact,NOW,verified_live=True)
        self.assertEqual(offer["stat"],"PTS")
        self.assertEqual(offer["more_tier"],"standard")
        slate={"games":[{"game":"Boston Celtics @ Miami Heat","start":START}]}
        out=publish([{"data":[compact],"meta":{
            "mode":"live","source_status":"fresh","next_cursor":None}}],
            [],NOW,schedule=slate)
        self.assertEqual(out["independent_board_count"],1)
        self.assertEqual(out["board_offers"][0]["line"],23.5)

    def test_independent_full_slate_without_odds_api_ai_board(self):
        slate={"games":[{"game":"Boston Celtics @ Miami Heat","start":START,
                         "game_state":"pre"}]}
        out=publish([{"data":[fixture()],"meta":{
            "mode":"live","source_status":"fresh","next_cursor":None}}],
            [],NOW,schedule=slate)
        self.assertEqual(out["status"],"LIVE_THIRD_PARTY_PRIZEPICKS_LINES")
        self.assertEqual(out["matched_count"],0)
        self.assertEqual(out["independent_board_count"],1)
        self.assertEqual(out["games_with_independent_lines"],1)
        self.assertEqual(out["board_offers"][0]["game"],"Boston Celtics @ Miami Heat")
        self.assertFalse(out["partial_board"])

    def test_other_team_or_started_game_does_not_show_false_line(self):
        bad={"games":[{"game":"Boston Celtics @ Los Angeles Lakers","start":START}]}
        out=publish([{"data":[fixture()],"meta":{
            "mode":"live","source_status":"fresh","next_cursor":None}}],[],
            NOW,schedule=bad)
        self.assertEqual(out["independent_board_count"],0)
        past={"games":[{"game":"Boston Celtics @ Miami Heat",
             "start":"2026-11-06T18:00:00Z"}]}
        self.assertEqual(publish([{"data":[fixture()],"meta":{
            "mode":"live","source_status":"fresh","next_cursor":None}}],[],
            NOW,schedule=past)["independent_board_count"],0)

    def test_source_cursor_indicates_partial_coverage(self):
        out=publish([{"data":[fixture()],"meta":{
            "mode":"live","source_status":"fresh","next_cursor":"pp_next"}}],
            [],NOW,schedule={"games":[{"game":"Boston Celtics @ Miami Heat","start":START}]})
        self.assertTrue(out["partial_board"])

    def test_bad_feed_refused(self):
        with self.assertRaises(ValueError):
            publish([{"data":[fixture()],"meta":{"mode":"demo","source_status":"fresh"}}],[COMP],NOW)

if __name__=="__main__":unittest.main()
