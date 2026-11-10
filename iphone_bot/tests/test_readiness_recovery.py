import unittest
from iphone_bot.readiness_recovery import recovery_targets

class RecoveryRoutingTests(unittest.TestCase):
    def test_ready_does_not_trigger_spend(self):
        self.assertEqual(recovery_targets({"status":"READY","components":{}}), [])
    def test_stale_lines_triggers_collector(self):
        report={"status":"DEGRADED","upcoming_games":6,"components":{
            "prizepicks_lines":{"required":True,"state":"DEGRADED"}}}
        self.assertEqual(recovery_targets(report),["nba-prizepicks-full-slate.yml"])
    def test_non_required_card_issue_does_not_trigger_paid_refresh(self):
        report={"status":"DEGRADED","upcoming_games":6,"components":{
            "published_pick_cards":{"required":False,"state":"DEGRADED"}}}
        self.assertEqual(recovery_targets(report),[])
    def test_capture_triggers_model_generation_not_another_audit(self):
        report={"status":"DEGRADED","upcoming_games":6,"components":{
            "pregame_capture":{"required":True,"state":"DEGRADED"},
            "public_browser":{"required":True,"state":"DEGRADED"}}}
        self.assertEqual(recovery_targets(report),[
            "nba-prizepicks-site-publish.yml","nba-new-ai-all-markets.yml"])
    def test_capture_does_not_attempt_to_recreate_models_after_tipoff(self):
        report={"status":"DEGRADED","upcoming_games":0,"components":{
            "pregame_capture":{"required":True,"state":"DEGRADED"}}}
        self.assertEqual(recovery_targets(report),[])

    def test_no_paid_refresh_after_tipoff_without_upcoming_games(self):
        report={"status":"DEGRADED","upcoming_games":0,"components":{
            "prizepicks_lines":{"required":True,"state":"DEGRADED"}}}
        self.assertEqual(recovery_targets(report),[])
if __name__=="__main__": unittest.main()
