"""Provisional means separate descriptive estimates, never official model picks."""
import copy
import json
import unittest
import tempfile
from unittest.mock import patch
from datetime import datetime, timezone
from pathlib import Path

from iphone_bot.provisional_short_history import estimates, STATUS, COHORT
from iphone_bot.multimarket_forecast_ledger import merge

NOW = datetime(2026,11,12,20,tzinfo=timezone.utc)
START = '2026-11-13T02:00:00+00:00'
GAME = 'Charlotte Hornets @ Phoenix Suns'


def history(n=4):
    return [{'id':'123','player':'Example','team':'CHA','opponent':'BOS',
             'date':f'2026-11-{day:02d}','PTS':10+day,'REB':3.,'AST':2.,'MIN':20.}
            for day in range(1,n+1)]


def feed():
    return {'source':'AUTHENTIC_PRIZEPICKS_PICKEM_NO_ODDS',
            'status':'FRESH_AUTHENTIC_PRIZEPICKS_LINES','is_live':True,
            'updated_at':NOW.isoformat(),
            'picks':[{'player':'Example','team':'CHA','game':GAME,'start':START,
                      'market_updated':NOW.isoformat(),'stat':stat,'line':line,
                      'direction':side,'pickem_tier':'standard'}
                     for stat,line in [('Points',12.5),('Rebounds',3.5),('Assists',2.5),('Points Rebounds Assists',17.5)]
                     for side in ['More','Less']]}


def injury(**extra):
    return {'status':'OFFICIAL_NBA_REPORT_VERIFIED','injury_data_verified':True,
            'report_issued_at':NOW.isoformat(),'players':[],**extra}


def run(rows=None, offers=None, injuries=None, **kwargs):
    primary=kwargs.pop('primary', {'status':'FROZEN_NEW_AI_ALL_MARKET','records':[]})
    return estimates(history() if rows is None else rows, feed() if offers is None else offers,
                     primary=primary, now=NOW, injuries=injury() if injuries is None else injuries, **kwargs)


class ProvisionalTests(unittest.TestCase):
    def test_three_to_seven_games_only(self):
        for n in (0,1,2,3,7,8,10):
            with self.subTest(n=n):
                report=run(history(n))
                self.assertEqual(report['count'],4 if 3<=n<8 else 0)

    def test_descriptive_average_and_pra_are_not_trained_probabilities(self):
        report=run()
        self.assertEqual(report['status'],STATUS)
        self.assertEqual(report['cohort'],COHORT)
        self.assertIsNone(report['performance_metrics'])
        self.assertFalse(report['trained_model'])
        values={r['stat']:r['projection'] for r in report['estimates']}
        self.assertEqual(values,{'PTS':12.5,'REB':3.,'AST':2.,'PRA':17.5})
        for row in report['estimates']:
            self.assertEqual(row['prior_games'],4)
            self.assertEqual(row['history_dates'],[f'2026-11-0{i}' for i in range(1,5)])
            for key in ('estimated_hit_chance','calibrated_probability','hit_probability'):
                self.assertIsNone(row[key])
            for key in ('primary_model_eligible','official_grade_eligible','trained_model'):
                self.assertIs(row[key],False)
            self.assertNotIn('direction',row)
            self.assertNotIn('grade',row)

    def test_primary_ledger_cannot_ingest_provisional_cohort(self):
        report=run()
        primary=merge({},report,{})
        self.assertEqual(primary['records'],[])
        self.assertEqual(primary['new_pregame_frozen'],0)
        self.assertNotIn('predictions',report)
        self.assertNotIn('records',report)

    def test_existing_valid_primary_exact_identity_is_excluded_read_only(self):
        row={'player_id':'123','team':'CHA','game':GAME,'start':START,'stat':'PTS','line':12.5,
             'pickem_tier':'standard','standard_line_two_sided_verified':True,'research_only':True,
             'calibrated_probability':None,'captured_at':NOW.isoformat(),'market_updated':NOW.isoformat(),
             'projection':14.}
        primary={'status':'FROZEN_NEW_AI_ALL_MARKET','records':[row]}
        before=copy.deepcopy(primary)
        result=run(primary=primary)
        self.assertEqual(result['count'],3)
        self.assertNotIn('PTS',{r['stat'] for r in result['estimates']})
        self.assertEqual(result['excluded']['ALREADY_PRIMARY_EXACT_IDENTITY'],1)
        self.assertEqual(primary,before)
        # Similar players, games, timestamps or thresholds cannot suppress a
        # genuinely different provisional identity.
        for change in ({'player_id':'999'},{'team':'PHX'},{'game':'Other @ Game'},
                       {'start':'2026-11-14T02:00:00+00:00'},{'line':13.5}):
            with self.subTest(change=change):
                changed={'status':'FROZEN_NEW_AI_ALL_MARKET','records':[{**row,**change}]}
                self.assertEqual(run(primary=changed)['count'],4)

    def test_missing_primary_ledger_fails_closed(self):
        for primary in (None,{}, {'status':'FROZEN_NEW_AI_ALL_MARKET'},
                        {'status':'OTHER','records':[]}):
            result=run(primary=primary)
            self.assertEqual(result['count'],0)
            self.assertEqual(result['blocker'],'PRIMARY_LEDGER_UNAVAILABLE_OR_INVALID')

    def test_inputs_are_not_mutated(self):
        data=history();offers=feed();health=injury()
        before=copy.deepcopy((data,offers,health))
        run(data,offers,health)
        self.assertEqual((data,offers,health),before)

    def test_same_day_and_future_cannot_change_estimate_or_roster(self):
        rows=history()
        baseline=run(rows)
        for day in ('2026-11-12','2026-11-13','2027-01-01'):
            rows.append({**rows[-1],'date':day,'PTS':100,'team':'PHX'})
        report=run(rows)
        self.assertEqual(report['estimates'],baseline['estimates'])

    def test_duplicate_date_and_cross_team_id_conflict_fail_closed(self):
        for changed in ({},{'PTS':99},{'team':'PHX'}):
            with self.subTest(changed=changed):
                rows=history();rows.append({**rows[-1],**changed})
                self.assertEqual(run(rows)['count'],0)

    def test_invalid_numbers_and_dates_fail_closed(self):
        for change in ({'PTS':float('nan')},{'PTS':True},{'REB':-1},{'MIN':0.5},
                       {'MIN':61},{'date':'bad-date'}):
            with self.subTest(change=change):
                rows=history();rows[0].update(change)
                self.assertEqual(run(rows)['count'],0)

    def test_single_source_rows_do_not_count_towards_eligibility(self):
        rows=history(3);rows[0]['history_source_confidence']='SINGLE_SOURCE_PUBLIC_CSV_ARITHMETIC_VALIDATED'
        self.assertEqual(run(rows)['count'],0)

    def test_same_name_distinct_id_fails_closed(self):
        rows=history()+[{**history()[0],'id':'999'}]
        self.assertEqual(run(rows)['count'],0)

    def test_one_id_assigned_multiple_player_names_is_rejected(self):
        rows=history();rows[0]['player']='Different Person'
        self.assertEqual(run(rows)['count'],0)

    def test_blocked_publication_replaces_stale_estimates_with_empty_artifact(self):
        from iphone_bot import provisional_short_history as module
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)/'provisional.json'
            output.write_text(json.dumps(run()))
            with patch.object(module,'OUTPUT',output), patch('sys.argv',['provisional','--blocked','SOURCE_REFRESH_FAILED']):
                code=module.main()
            report=json.loads(output.read_text())
            self.assertEqual(code,1)
            self.assertEqual(report['count'],0)
            self.assertEqual(report['estimates'],[])
            self.assertEqual(report['blocker'],'SOURCE_REFRESH_FAILED')
            self.assertIsNone(report['performance_metrics'])

    def test_only_same_team_history_counts(self):
        rows=history(7)
        for row in rows[:5]:row['team']='DAL'
        self.assertEqual(run(rows)['count'],0)

    def test_quote_team_must_match_verified_identity(self):
        offers=feed()
        for row in offers['picks']:row['team']='PHX'
        self.assertEqual(run(offers=offers)['count'],0)

    def test_nonstandard_one_sided_or_conflicting_thresholds_withheld(self):
        for kind in ('goblin','demon','one-side','conflicting'):
            offers=feed()
            if kind in ('goblin','demon'):
                for row in offers['picks']:row['pickem_tier']=kind
            elif kind=='one-side':offers['picks']=[r for r in offers['picks'] if r['direction']=='More']
            else:
                offers['picks'] += [{**r,'line':r['line']+1} for r in offers['picks']]
            self.assertEqual(run(offers=offers)['count'],0)

    def test_quote_at_tip_future_naive_or_old_is_withheld(self):
        for field,value in [('start',NOW.isoformat()),('market_updated','2026-11-12T20:01:00+00:00'),
                            ('market_updated','2026-11-12T12:00:00+00:00'),('market_updated','2026-11-12T20:00:00')]:
            offers=feed()
            for row in offers['picks']:row[field]=value
            self.assertEqual(run(offers=offers)['count'],0)

    def test_future_eastern_slate_is_not_shown_early(self):
        offers=feed()
        for row in offers['picks']:row['start']='2026-11-14T02:00:00+00:00'
        report=run(offers=offers)
        self.assertEqual(report['count'],0)
        self.assertEqual(report['excluded']['OUTSIDE_TODAY_EASTERN_SLATE'],4)

    def test_invalid_feed_clears_estimates_with_explicit_blocker(self):
        for change in ({'status':'STALE'},{'is_live':False},{'updated_at':'bad'},
                       {'updated_at':'2026-11-12T10:00:00+00:00'},
                       {'updated_at':'2026-11-12T21:00:00+00:00'}):
            offers=feed();offers.update(change)
            report=run(offers=offers)
            self.assertEqual(report['estimates'],[])
            self.assertTrue(report['blocker'])

    def test_unverified_stale_or_future_injury_report_blocks(self):
        for data in ({},injury(injury_data_verified=False),injury(report_issued_at='2026-11-12T10:00:00+00:00'),
                     injury(report_issued_at='2026-11-12T21:00:00+00:00')):
            report=run(injuries=data)
            self.assertEqual(report['estimates'],[])
            self.assertEqual(report['blocker'],'INJURY_CONTEXT_UNVERIFIED_OR_STALE')

    def test_self_out_and_questionable_are_withheld(self):
        for status in ('Out','Questionable','Doubtful','Probable'):
            health=injury(players=[{'player_id':'123','team':'CHA','game_date':'2026-11-12','status':status}])
            self.assertEqual(run(injuries=health)['count'],0)
        health=injury(players=[{'player_id':'123','team':'CHA','game_date':'2026-11-12','status':'Available'}])
        self.assertEqual(run(injuries=health)['count'],4)

    def test_new_opponent_or_teammate_out_does_not_silently_keep_baseline(self):
        for team in ('CHA','PHX'):
            row={'player_id':'999','player':'Teammate','team':team,'game_date':'2026-11-12','status':'Out'}
            health=injury(players=[row])
            watch={'status':'FREE_OFFICIAL_NBA_INJURY_MONITOR','official_confirmed':True,
                   'events':[{**row,'status':'OUT','source':'OFFICIAL_NBA_REPORT','official':True,
                              'reported_at':NOW.isoformat()}]}
            self.assertEqual(run(injuries=health,free_watch=watch)['count'],0)

    def test_output_and_workflow_publication_are_isolated(self):
        root=Path(__file__).resolve().parents[2]
        module=(root/'iphone_bot/provisional_short_history.py').read_text()
        self.assertIn("OUTPUT = ROOT / 'docs/provisional_short_history.json'",module)
        self.assertNotIn('joblib.load',module)
        self.assertNotIn('simulate(',module)
        self.assertIn("primary=read('docs/lagged_matchup_all_market_ledger.json')",module)
        self.assertEqual(module.count('write_text('),1)
        workflow=(root/'.github/workflows/nba-new-ai-all-markets.yml').read_text()
        job=workflow.split('  provisional-baseline:',1)[1].split('\n  short-history-research:',1)[0]
        self.assertIn('needs: [multi-market]',job)
        self.assertIn('if: always() && !cancelled()',job)
        self.assertIn('git add docs/provisional_short_history.json',job)
        self.assertNotIn('git add docs/',job.replace('git add docs/provisional_short_history.json',''))
        self.assertIn('--blocked SOURCE_REFRESH_FAILED',job)
        self.assertIn('git reset --hard origin/main',job)
        self.assertIn('python -m iphone_bot.provisional_short_history',job)
        self.assertNotIn('lagged_matchup_all_market_ledger.json',job)
        self.assertNotIn('continue-on-error',job)


if __name__=='__main__':unittest.main()
