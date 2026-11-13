import copy
import datetime as dt
import unittest
from iphone_bot.current_primary_coverage import evaluate
NOW=dt.datetime(2026,11,12,23,tzinfo=dt.timezone.utc)
TIP='2026-11-13T01:00:00Z'
GAME={'game':'A @ B','start':TIP}
P={'player':'Player','player_id':'1','team':'A','game':'A @ B','start':TIP,'stat':'Points',
   'line':10.5,'market_updated':'2026-11-12T22:50:00Z','pickem_tier':'standard','source':'independent_prizepicksapi_com'}
def inputs():
    feed={'source':'AUTHENTIC_PRIZEPICKS_PICKEM_NO_ODDS','status':'FRESH_AUTHENTIC_PRIZEPICKS_LINES','is_live':True,
          'source_generated_at':'2026-11-12T22:55:00Z','updated_at':'2026-11-12T22:55:00Z',
          'picks':[{**P,'direction':side} for side in ('More','Less')]}
    row={**P,'stat':'PTS','projection':11.,'captured_at':'2026-11-12T22:54:00Z',
         'standard_line_two_sided_verified':True,'research_only':True,'calibrated_probability':None}
    return feed,{'status':'FROZEN_NEW_AI_ALL_MARKET','records':[row]}
class CurrentCoverageTests(unittest.TestCase):
    def test_exact_valid_current_primary_is_complete(self):
        f,l=inputs();r=evaluate(f,l,[GAME],NOW)
        self.assertEqual((r['status'],r['matched_primary_offers']),('COMPLETE',1))
    def test_moved_current_line_is_not_satisfied_by_original(self):
        f,l=inputs();l['records'][0]['line']=9.5
        self.assertEqual(evaluate(f,l,[GAME],NOW)['missing_primary_offers'],1)
    def test_new_version_covers_current_without_repricing_history(self):
        f,l=inputs();l['records'].append({**l['records'][0],'line':9.5});before=copy.deepcopy(l)
        self.assertEqual(evaluate(f,l,[GAME],NOW)['status'],'COMPLETE');self.assertEqual(l,before)
    def test_research_baseline_cannot_count_as_primary(self):
        f,l=inputs();l['records'][0].pop('standard_line_two_sided_verified')
        self.assertEqual(evaluate(f,l,[GAME],NOW)['missing_primary_offers'],1)
    def test_started_game_is_not_current_pregame(self):
        f,l=inputs();r=evaluate(f,l,[GAME],NOW+dt.timedelta(hours=3))
        self.assertEqual(r['games'],[])
    def test_one_sided_conflicting_or_goblin_offers_are_not_verified(self):
        for change in ('one','conflict','goblin'):
            f,l=inputs()
            if change=='one':f['picks'].pop()
            if change=='conflict':f['picks'][0]['line']=9.5
            if change=='goblin':f['picks'][0]['pickem_tier']='goblin'
            r=evaluate(f,l,[GAME],NOW)
            self.assertEqual(r['verified_current_offers'],0);self.assertEqual(r['status'],'INCOMPLETE')
    def test_bad_source_is_unverified(self):
        for stamp in ('bad','2026-11-11T23:00:00Z','2026-11-13T00:00:00Z'):
            f,l=inputs();f['source_generated_at']=stamp
            self.assertEqual(evaluate(f,l,[GAME],NOW)['status'],'UNVERIFIED')
    def test_invalid_late_frozen_prediction_does_not_count(self):
        f,l=inputs();l['records'][0]['captured_at']=TIP
        self.assertEqual(evaluate(f,l,[GAME],NOW)['missing_primary_offers'],1)
    def test_current_checks_do_not_modify_archive_status(self):
        from iphone_bot.tonight_capture_gradeability import reconcile
        f,l=inputs();r=reconcile({'games':[]},{},{},l,{},now=NOW,current=f)
        self.assertEqual(r['status'],'CAPTURE_INCOMPLETE')
    def test_completed_capture_refreshes_both_readiness_reports(self):
        from pathlib import Path
        for name in ('production_readiness.yml','unified-dames-picks-readiness.yml'):
            text=(Path('.github/workflows')/name).read_text()
            block=text.split('  workflow_run:',1)[1].split('  schedule:',1)[0]
            self.assertIn('Verify tonight NBA frozen lines predictions and grades',block)
            self.assertIn('types: [completed]',block)
        text=Path('.github/workflows/nba-tonight-capture-gradeability.yml').read_text()
        block=text.split('  workflow_run:',1)[1].split('  schedule:',1)[0]
        self.assertIn('Guarded new NBA AI all markets PTS REB AST PRA',block)
        self.assertIn('types: [completed]',block)
if __name__=='__main__':unittest.main()
