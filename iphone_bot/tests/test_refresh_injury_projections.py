"""Fast injury board refresh uses official future matchup and fixed prior games."""
import copy
import unittest
from iphone_bot.refresh_injury_projections import refresh

NOW="2026-11-07T18:30:00+00:00"
START="2026-11-07T23:00:00+00:00"

def board():
    return {"status":"EXPERIMENTAL_NON_CALIBRATED",
            "verified_current_matchups":True,
            "generated_at":"2026-11-07T18:00:00+00:00",
            "comparisons":[{"player":"Target Player","player_id":"100",
                "team":"BOS","game":"Boston Celtics @ Miami Heat",
                "stat":"PTS","start":START,"line":20.5,
                "projection":20.0,"shadow_projection":24.0,
                "combined_projection":22.0,
                "book_quotes":[{"name":"TestBook","line":20.5,
                                "over":-110,"under":-110,
                                "hypothetical_over_ev_pct":10.0}],
                "estimated_over_probability":0.65}]}

def report(pid="900",status="Out"):
    return {"status":"OFFICIAL_NBA_REPORT_VERIFIED",
            "injury_data_verified":True,
            "report_issued_at":"2026-11-07T18:15:00+00:00",
            "players":[{"player_id":pid,"team":"BOS",
                        "player":"Verified Out Teammate",
                        "game_date":"2026-11-07","status":status}]}

def games():
    out=[]
    for day in range(1,9):
        date=f"2026-10-{day:02d}"
        out.append({"id":"100","team":"BOS","date":date,
                    "MIN":26 if day<=4 else 32,
                    "PTS":18,"REB":5,"AST":4})
        for k in range(7):
            out.append({"id":str(300+k),"team":"BOS","date":date,
                        "MIN":20,"PTS":5,"REB":3,"AST":1})
        if day<=4:
            out.append({"id":"900","team":"BOS","date":date,
                        "MIN":28,"PTS":15,"REB":6,"AST":4})
    return out

class FastInjuryRefreshTests(unittest.TestCase):
    def test_confirmed_out_updates_main_projection_not_only_warning(self):
        original=board()
        old=copy.deepcopy(original)
        changed,info=refresh(original,report(),games(),NOW)
        self.assertEqual(info["reprojected"],1)
        row=changed["comparisons"][0]
        self.assertGreater(row["combined_projection"],22.0)
        self.assertEqual(row["preinjury_combined_projection"],22.0)
        self.assertEqual(row["injury_reprojection_status"],
                         "REPROJECTED_FROM_VERIFIED_OFFICIAL_OUT")
        self.assertIsNone(row["estimated_over_probability"])
        self.assertFalse(row["experimental_ev_available"])
        self.assertNotIn("hypothetical_over_ev_pct",row["book_quotes"][0])
        self.assertEqual(original,old)
        again,_=refresh(changed,report(),games(),NOW)
        self.assertEqual(again["comparisons"][0]["combined_projection"],
                         row["combined_projection"])

    def test_official_out_player_removed_from_new_board(self):
        d=report(pid="100")
        changed,counters=refresh(board(),d,games(),NOW)
        self.assertEqual(changed["comparisons"],[])
        self.assertEqual(counters["ruled_out_player_removed"],1)

    def test_unsupported_injury_never_keeps_old_pick_masquerading_as_new(self):
        changed,counters=refresh(board(),report(),[g for g in games() if g["date"]<"2026-10-05"],NOW)
        self.assertEqual(changed["comparisons"],[])
        self.assertEqual(counters["unsupported_injury_pick_removed"],1)

    def test_updated_official_available_status_restores_suppressed_pretip_market(self):
        hidden,_=refresh(board(),report(pid="100"),games(),NOW)
        self.assertEqual(len(hidden["injury_excluded_comparisons"]),1)
        recovered_report=report(pid="100",status="Available")
        recovered_report["report_issued_at"]="2026-11-07T18:25:00+00:00"
        recovered,info=refresh(hidden,recovered_report,games(),NOW)
        self.assertEqual(len(recovered["comparisons"]),1)
        self.assertEqual(recovered["injury_excluded_comparisons"],[])
        self.assertEqual(recovered["comparisons"][0]["combined_projection"],22.0)
        self.assertEqual(info["baseline_or_restored"],1)

    def test_stale_or_nonofficial_injury_report_is_ignored(self):
        d=report()
        d["report_issued_at"]="2026-11-05T18:00:00+00:00"
        unchanged,status=refresh(board(),d,games(),NOW)
        self.assertEqual(unchanged,board())
        self.assertEqual(status["status"],"STALE_OR_FUTURE_REPORT_NO_CHANGES")
        d["report_issued_at"]="2026-11-07T18:15:00+00:00"
        d["status"]="THIRD_PARTY_ESPN_INJURY_CONTEXT"
        unchanged,status=refresh(board(),d,games(),NOW)
        self.assertEqual(status["status"],"NO_OFFICIAL_REPORT_NO_CHANGES")

    def test_wrong_game_date_cannot_move_projection(self):
        d=report()
        d["players"][0]["game_date"]="2026-11-08"
        changed,info=refresh(board(),d,games(),NOW)
        row=changed["comparisons"][0]
        self.assertEqual(row["combined_projection"],22.0)
        self.assertEqual(row["injury_reprojection_status"],"NO_OFFICIAL_OUT_IN_MATCHUP")

if __name__=="__main__":
    unittest.main()
