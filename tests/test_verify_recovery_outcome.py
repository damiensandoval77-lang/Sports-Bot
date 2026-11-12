import copy
import datetime as dt
import unittest
from unittest.mock import patch
from scripts.verify_recovery_outcome import FILES, evaluate, observe, verify

NOW = dt.datetime(2026, 11, 12, 22, tzinfo=dt.timezone.utc)

def healthy():
    return dict(zip(FILES, [
        {'status': 'READY', 'checked_at': NOW.isoformat()},
        {'status': 'AI_PRETIP_FORECASTS_GRADED', 'ungraded': 0, 'generated_at': NOW.isoformat(), 'recorded_pregame_forecasts': 10, 'graded': 8, 'verified_dnp_exclusions': 2, 'verified_pretip_transfer_exclusions': 0},
        {'status': 'NO_OVERDUE_PENDING', 'checked_at': NOW.isoformat()},
        {'status': 'CAPTURE_VERIFIED', 'checked_at': NOW.isoformat(), 'game_date_eastern': '2026-11-12', 'summary': {'total_standard_markets_without_frozen_model': 0}},
    ]))

class RecoveryOutcomeTests(unittest.TestCase):
    def test_complete_data_passes(self):
        self.assertTrue(evaluate(healthy(), NOW)['healthy'])

    def test_stale_zero_backlog_and_inconsistent_totals_fail(self):
        for index, field in [(1, 'generated_at'), (2, 'checked_at')]:
            for stamp in (None, 'bad', '2026-11-10T22:00:00Z', '2026-11-13T22:00:00Z'):
                docs=healthy()
                docs[FILES[index]][field]=stamp
                self.assertFalse(evaluate(docs,NOW)['healthy'])
        for value in (None, False, -1, 11):
            docs=healthy()
            docs[FILES[1]]['recorded_pregame_forecasts']=value
            self.assertIn('FROZEN_FORECAST_COUNTS_DO_NOT_RECONCILE',evaluate(docs,NOW)['reasons'])

    def test_missing_inputs_and_missing_zero_counts_fail_closed(self):
        for name in FILES:
            with self.subTest(name=name):
                docs = healthy()
                del docs[name]
                self.assertFalse(evaluate(docs, NOW)['healthy'])
        docs = healthy()
        del docs[FILES[1]]['ungraded']
        self.assertFalse(evaluate(docs, NOW)['healthy'])

    def test_non_object_json_and_summary_fail_closed(self):
        for name in FILES:
            docs = healthy()
            docs[name] = ['malformed']
            self.assertFalse(evaluate(docs, NOW)['healthy'])
        docs = healthy()
        docs[FILES[3]]['summary'] = ['malformed']
        self.assertFalse(evaluate(docs, NOW)['healthy'])

    def test_ready_does_not_hide_unmodeled_standard_quotes(self):
        docs = healthy()
        docs[FILES[3]]['summary']['total_standard_markets_without_frozen_model'] = 25
        result = evaluate(docs, NOW)
        self.assertFalse(result['healthy'])
        self.assertIn('PRIMARY_FROZEN_MODEL_COVERAGE_INCOMPLETE', result['reasons'])

    def test_capture_status_date_and_timestamp_must_be_current(self):
        for field, value in [('status', None), ('status', 'UNKNOWN'), ('game_date_eastern', '2026-11-11'), ('checked_at', None), ('checked_at', '2026-11-11T22:00:00Z')]:
            docs = healthy()
            docs[FILES[3]][field] = value
            self.assertFalse(evaluate(docs, NOW)['healthy'])

    def test_malformed_counts_and_unknown_overdue_status_do_not_pass(self):
        for count in (None, False, '0', -1):
            docs = healthy()
            docs[FILES[1]]['ungraded'] = count
            self.assertFalse(evaluate(docs, NOW)['healthy'])
        docs = healthy()
        docs[FILES[2]]['status'] = 'UNKNOWN'
        self.assertFalse(evaluate(docs, NOW)['healthy'])

    def test_old_readiness_cannot_prove_recovery(self):
        result = evaluate(healthy(), NOW, not_before=NOW + dt.timedelta(seconds=1))
        self.assertIn('NO_POST_RECOVERY_READINESS_EVIDENCE', result['reasons'])
        for stamp in ('bad', '2026-11-12T22:00:00', '2026-11-12T20:00:00Z', '2026-11-13T22:00:00Z'):
            docs = healthy()
            docs[FILES[0]]['checked_at'] = stamp
            self.assertFalse(evaluate(docs, NOW)['healthy'])

    def test_polling_waits_and_then_proves_recovery(self):
        seconds = [0]
        calls = [False, False, True]
        def observer(**kwargs):
            ok = calls.pop(0)
            return {'healthy': ok, 'reasons': [] if ok else ['NOT_READY']}
        report = verify(60, 10, observer=observer, clock=lambda: seconds[0],
                        sleep=lambda n: seconds.__setitem__(0, seconds[0] + n))
        self.assertEqual(report['status'], 'PUBLIC_DATA_VERIFIED')
        self.assertEqual(len(report['attempts']), 3)
        self.assertEqual(seconds[0], 20)

    def test_unresolved_timeout_is_blocked_with_evidence(self):
        seconds = [0]
        report = verify(25, 10, observer=lambda **kwargs: {'healthy': False, 'reasons': ['MISSING_MODELS']},
                        clock=lambda: seconds[0], sleep=lambda n: seconds.__setitem__(0, seconds[0]+n))
        self.assertEqual(report['status'], 'BLOCKED')
        self.assertEqual(report['final']['reasons'], ['MISSING_MODELS'])
        self.assertEqual(seconds[0], 25)
        self.assertEqual(len(report['attempts']), 4)

    def test_fetch_failure_is_blocked_not_success(self):
        def observer(**kwargs):
            raise OSError('network unavailable')
        report = verify(observer=observer)
        self.assertEqual(report['status'], 'BLOCKED')
        self.assertIn('VERIFICATION_FETCH_FAILED', report['final']['reasons'])

    @patch('scripts.verify_recovery_outcome.subprocess.check_output', return_value='a'*40)
    @patch('scripts.verify_recovery_outcome.fetch_json')
    def test_public_snapshot_must_match_pinned_main(self, fetch, _):
        docs = healthy()
        current = dt.datetime.now(dt.timezone.utc)
        docs[FILES[0]]['checked_at'] = current.isoformat()
        docs[FILES[3]]['checked_at'] = current.isoformat()
        from zoneinfo import ZoneInfo
        docs[FILES[3]]['game_date_eastern'] = current.astimezone(ZoneInfo('America/New_York')).date().isoformat()
        values = [docs[x] for x in FILES]
        stale = copy.deepcopy(values)
        stale[0]['status'] = 'NOT_READY'
        fetch.side_effect = values + stale
        result = observe()
        self.assertFalse(result['healthy'])
        self.assertIn('PUBLIC_DATA_NOT_YET_MATCHING_PINNED_MAIN', result['reasons'])
        self.assertTrue(all('a'*40 in call.args[0] for call in fetch.call_args_list[:4]))

    def test_workflow_keeps_receipt_and_terminal_failure_gate(self):
        import yaml
        from pathlib import Path
        text = Path('.github/workflows/full-repository-audit.yml').read_text()
        workflow = yaml.safe_load(text)
        steps = workflow['jobs']['production-health']['steps']
        initial = next(s for s in steps if s.get('id') == 'health')
        self.assertTrue(initial['continue-on-error'])
        check = next(s for s in steps if s.get('name', '').startswith('Wait for same-run'))
        self.assertNotIn('continue-on-error', check)
        self.assertIn('--wait-seconds 480', check['run'])
        self.assertIn('--not-before', check['run'])
        artifact = next(s for s in steps if s.get('uses', '').startswith('actions/upload-artifact'))
        self.assertEqual(artifact['if'], 'always()')
        self.assertIn('recovery-verification.json', artifact['with']['path'])
        self.assertIn("needs.production-health.result != 'success'", workflow['jobs']['publish-report']['steps'][-1]['if'])

if __name__ == '__main__':
    unittest.main()
