"""Offline full-slate final-boxscore/immutable grade acceptance test."""
import datetime as dt
import unittest
from iphone_bot.grade_frozen_ai_forecasts import eligible_predictions,settle_predictions,report

NOW=dt.datetime(2026,11,10,15,tzinfo=dt.timezone.utc)
GAMES=[
 ("Cleveland Cavaliers @ Charlotte Hornets","CLE","CHA"),
 ("Los Angeles Lakers @ Atlanta Hawks","LAL","ATL"),
 ("Washington Wizards @ Detroit Pistons","WAS","DET"),
 ("Memphis Grizzlies @ Toronto Raptors","MEM","TOR"),
 ("Indiana Pacers @ Dallas Mavericks","IND","DAL"),
 ("Denver Nuggets @ Houston Rockets","DEN","HOU"),
 ("San Antonio Spurs @ Phoenix Suns","SAS","PHX"),
 ("New Orleans Pelicans @ Golden State Warriors","NOP","GSW"),
]
START="2026-11-10T00:00:00Z"
CAPTURED="2026-11-09T23:40:00Z"
def prediction(i,stat="PTS"):
    game,team,opp=GAMES[i]
    return {"player_id":str(800000+i),"player":"Player "+str(i),
        "team":team,"game":game,"start":START,
        "stat":stat,"projection":15.0+i,"line":None,
        "is_pregame_prediction":True,"captured_at":CAPTURED}
def final(i,verified=True):
    _,team,opp=GAMES[i]
    return {"player":"Player "+str(i),"team":team,"opponent":opp,
        "date":"2026-11-09","source":"NBA_CDN_FINAL",
        "source_game_id":"002260030"+str(i),
        "final_confirmed":verified,"PTS":20+i,"REB":5,"AST":3,
        "PRA":28+i,"MIN":28.0}
class EightGameNightlyGrading(unittest.TestCase):
    def test_all_eight_games_end_to_end_and_idempotent(self):
        candidates=[prediction(i) for i in range(8)]
        selected=eligible_predictions(candidates,NOW)
        self.assertEqual(len(selected),8)
        actuals=[final(i) for i in range(8)]
        settled=settle_predictions(selected,actuals)
        self.assertEqual(settled["new_grades"],8)
        audit=report("2026-11-09",selected,settled,now=NOW,final_rows=actuals)
        self.assertEqual(audit["graded"],8)
        self.assertEqual(audit["ungraded"],0)
        self.assertEqual(audit["accounted_for"],8)
        again=settle_predictions(selected,[{**x,"PTS":42} for x in actuals],settled["records"])
        self.assertEqual(again["new_grades"],0)
        self.assertEqual([r["actual"] for r in again["records"]],
                         [r["actual"] for r in settled["records"]])
        self.assertTrue(all(r["line"] is None and r["betting_grade"] is None
                            for r in again["records"]))
    def test_failed_source_leaves_explicit_pending_not_zero(self):
        selected=eligible_predictions([prediction(i) for i in range(8)],NOW)
        actuals=[final(i) for i in range(7)]
        settled=settle_predictions(selected,actuals)
        audit=report("2026-11-09",selected,settled,now=NOW,final_rows=actuals)
        self.assertEqual(audit["ungraded"],1)
        self.assertEqual(audit["accounted_for"],7)
        self.assertEqual(audit["ungraded_by_game"],{GAMES[7][0]:1})
        self.assertNotEqual(audit["status"],"AI_PRETIP_FORECASTS_GRADED")
    def test_unverified_final_and_posttip_forecasts_never_grade(self):
        p=prediction(0)
        self.assertEqual(eligible_predictions([{**p,"captured_at":"2026-11-10T00:01:00Z"}],NOW),[])
        selected=eligible_predictions([p],NOW)
        self.assertEqual(settle_predictions(selected,[final(0,verified=False)])["new_grades"],0)
if __name__=="__main__":unittest.main()
