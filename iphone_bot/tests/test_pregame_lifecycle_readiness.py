import datetime as dt
import unittest
from pathlib import Path
from iphone_bot.pregame_lifecycle_readiness import audit

NOW=dt.datetime(2026,11,9,22,tzinfo=dt.timezone.utc)
def game(name,day,start):
    return {"game":name,"date_eastern":day,"start":start}
SCHEDULE={"status":"THIRD_PARTY_NBA_SCHEDULE_ONLY","coverage_complete":True,
 "games":[game("A @ B","2026-11-09","2026-11-10T00:00:00Z"),
          game("C @ D","2026-11-10","2026-11-11T00:00:00Z"),
          game("E @ F","2026-11-10","2026-11-11T01:00:00Z")]}
def quote(g="C @ D",s="2026-11-11T00:00:00Z"):
 return {"id":"p1","player":"Test Player","team":"C","game":g,
         "stat":"PTS","line":15.5,"starts_at":s,
         "observed_at":"2026-11-10T23:52:00Z",
         "source_generated_at":"2026-11-10T23:55:00Z",
         "more_tier":"standard","less_tier":"standard",
         "tier":"standard","source":"independent_prizepicksapi_com","is_demo":False}
def predict(g="C @ D",s="2026-11-11T00:00:00Z"):
 return {"player":"Test Player","team":"C","game":g,"stat":"PTS",
         "projection":16,"line":None,"start":s,
         "captured_at":"2026-11-10T23:50:00Z",
         "is_pregame_prediction":True}
def archive(rows):
 return {"status":"VERIFIED_PRETIP_PRIZEPICKS_QUOTES_ARCHIVE","quotes":rows}
def predictions(rows):
 return {"status":"IMMUTABLE_OBSERVED_PRETIP_NOLINE_AI_ARCHIVE","predictions":rows}
class PregameLifecycleReadinessTests(unittest.TestCase):
 def test_future_slate_not_tonights_partial_remaining_games(self):
    result=audit(SCHEDULE,archive([]),predictions([]),now=NOW)
    self.assertEqual(result["target_date_eastern"],"2026-11-10")
    self.assertEqual(result["counts"]["scheduled"],2)
    self.assertEqual(result["status"],"NOT_READY")
 def test_partial_slate_cannot_be_called_ready(self):
    result=audit(SCHEDULE,archive([quote()]),predictions([predict()]),now=NOW)
    self.assertEqual(result["counts"]["games_with_saved_quotes"],1)
    self.assertEqual(result["counts"]["games_with_saved_ai"],1)
    self.assertIn("SOME_SCHEDULED_GAMES_WITHOUT_SAVED_VERIFIED_LINES",result["issues"])
 def test_all_matches_require_source_captures_and_models(self):
    q=[quote(),quote("E @ F","2026-11-11T01:00:00Z")]
    q[1]["id"]="p2";q[1]["observed_at"]="2026-11-11T00:52:00Z"
    q[1]["source_generated_at"]="2026-11-11T00:55:00Z"
    p=[predict(),predict("E @ F","2026-11-11T01:00:00Z")]
    p[1]["captured_at"]="2026-11-11T00:50:00Z"
    result=audit(SCHEDULE,archive(q),predictions(p),now=NOW)
    self.assertEqual(result["status"],"READY")
    self.assertEqual(result["counts"]["saved_line_markets"],2)
 def test_posttip_quote_rejected_and_missing_not_guessed(self):
    q=quote()
    q["source_generated_at"]="2026-11-11T00:01:00Z"
    result=audit(SCHEDULE,archive([q]),predictions([predict()]),now=NOW)
    self.assertEqual(result["counts"]["games_with_saved_quotes"],0)
    self.assertEqual(result["status"],"NOT_READY")
 def test_workflow_rechecks_sources_and_does_not_republish_stale_receipt(self):
    workflow=(Path(__file__).resolve().parents[2]/'.github/workflows/nba-full-game-lifecycle.yml').read_text()
    self.assertIn('workflow_run:',workflow)
    self.assertIn('Publish lightweight PrizePicks site data and per-game coverage',workflow)
    self.assertIn('Guarded new NBA AI all markets PTS REB AST PRA',workflow)
    publish=workflow.split('Publish truthful readiness status',1)[1]
    self.assertLess(publish.index('git reset --hard origin/main'),publish.index('python -m iphone_bot.pregame_lifecycle_readiness'))
    self.assertNotIn('$RUNNER_TEMP/pregame_lifecycle_readiness.json',publish)
    self.assertNotIn("steps.preflight.outcome == 'failure'",publish)
 def test_bad_schedule_fails_closed(self):
    s={**SCHEDULE,"coverage_complete":False}
    result=audit(s,archive([]),predictions([]),now=NOW)
    self.assertIn("OFFICIAL_SCHEDULE_NOT_CONFIRMED_COMPLETE",result["issues"])
if __name__=="__main__":unittest.main()
