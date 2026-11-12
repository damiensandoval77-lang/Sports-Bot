"""Bounded same-run verification of credit-free recovery and public data.

A dispatched workflow is not a repair. Never writes source data or invents
missing forecasts. This verifies published data, not browser interaction.
"""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import subprocess
import time
import urllib.request
from zoneinfo import ZoneInfo

FILES = ('production_readiness.json', 'ai_forecast_grade_status.json',
         'grading_overdue_health.json', 'tonight_capture_gradeability.json')
BASE = 'https://damiensandoval77-lang.github.io/Sports-Bot/'
REPO = 'damiensandoval77-lang/Sports-Bot'
UTC = dt.timezone.utc


def moment(value):
    try:
        value = dt.datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        return value if value.tzinfo else None
    except (ValueError, TypeError):
        return None


def evaluate(documents, now=None, not_before=None):
    now = now or dt.datetime.now(UTC)
    reasons = []
    for name in FILES:
        if not isinstance(documents.get(name), dict) or not documents[name]:
            reasons.append('MISSING_OR_INVALID:' + name)
    documents = {name: value if isinstance(value, dict) else {} for name, value in documents.items()}
    ready = documents.get(FILES[0]) or {}
    grades = documents.get(FILES[1]) or {}
    overdue = documents.get(FILES[2]) or {}
    capture = documents.get(FILES[3]) or {}
    stamp = moment(ready.get('checked_at'))
    if ready.get('status') != 'READY' or not stamp or not 0 <= (now-stamp).total_seconds() <= 3600:
        reasons.append('READINESS_NOT_FRESH_AND_READY')
    if not_before and (not stamp or stamp < not_before):
        reasons.append('NO_POST_RECOVERY_READINESS_EVIDENCE')
    # Missing counts must never become zero and unknown health must not pass.
    if type(grades.get('ungraded')) is not int or grades['ungraded'] != 0:
        reasons.append('FROZEN_FORECASTS_NOT_FULLY_ACCOUNTED')
    if overdue.get('status') != 'NO_OVERDUE_PENDING':
        reasons.append('OVERDUE_GRADE_HEALTH_NOT_VERIFIED')
    summary = capture.get('summary')
    summary = summary if isinstance(summary, dict) else {}
    missing = summary.get('total_standard_markets_without_frozen_model')
    if type(missing) is not int or missing != 0 or capture.get('status') != 'CAPTURE_VERIFIED':
        reasons.append('PRIMARY_FROZEN_MODEL_COVERAGE_INCOMPLETE')
    capture_time = moment(capture.get('checked_at'))
    if (capture.get('game_date_eastern') != now.astimezone(ZoneInfo('America/New_York')).date().isoformat()
            or not capture_time or not 0 <= (now-capture_time).total_seconds() <= 10800):
        reasons.append('CAPTURE_EVIDENCE_NOT_CURRENT')
    return {'healthy': not reasons, 'reasons': reasons,
            'readiness_status': ready.get('status'),
            'readiness_checked_at': ready.get('checked_at'),
            'ungraded_frozen_forecasts': grades.get('ungraded'),
            'missing_primary_frozen_models': missing}


def fetch_json(url):
    req = urllib.request.Request(url, headers={'Cache-Control': 'no-cache',
                                'User-Agent': 'SportsBot-RecoveryVerifier'})
    with urllib.request.urlopen(req, timeout=15) as response:
        value = json.load(response)
    if not isinstance(value, dict):
        raise ValueError('Expected JSON object at ' + url)
    return value


def observe(not_before=None):
    sha = subprocess.check_output(['gh', 'api', f'repos/{REPO}/commits/main',
                                   '--jq', '.sha'], text=True, timeout=20).strip()
    if len(sha) != 40 or any(c not in '0123456789abcdef' for c in sha):
        raise ValueError('Invalid pinned main SHA')
    stamp = str(time.time_ns())
    source = {name: fetch_json(f'https://raw.githubusercontent.com/{REPO}/{sha}/docs/{name}')
              for name in FILES}
    served = {name: fetch_json(BASE + name + '?recovery_audit=' + stamp) for name in FILES}
    result = evaluate(source, not_before=not_before)
    result['main_sha'] = sha
    result['public_base'] = BASE
    result['public_data_matches_main'] = all(source[name] == served[name] for name in FILES)
    if not result['public_data_matches_main']:
        result['healthy'] = False
        result['reasons'].append('PUBLIC_DATA_NOT_YET_MATCHING_PINNED_MAIN')
    result['verification_scope'] = 'PUBLIC_DATA_ONLY_NOT_BROWSER_UI'
    return result


def verify(wait_seconds=0, interval=30, not_before=None, observer=observe,
           clock=time.monotonic, sleep=time.sleep):
    deadline = clock() + wait_seconds
    attempts = []
    while True:
        try:
            result = observer(not_before=not_before)
        except Exception as error:
            result = {'healthy': False, 'reasons': ['VERIFICATION_FETCH_FAILED'],
                      'error': type(error).__name__ + ': ' + str(error)[:300]}
        result['checked_at'] = dt.datetime.now(UTC).isoformat()
        attempts.append(result)
        if result['healthy'] or clock() >= deadline:
            break
        sleep(min(interval, max(0, deadline-clock())))
    return {'status': 'PUBLIC_DATA_VERIFIED' if result['healthy'] else 'BLOCKED',
            'attempts': attempts, 'final': result,
            'note': 'Dispatch/green CI alone is not a repair; browser UI remains a separate gate.'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--local', action='store_true')
    parser.add_argument('--wait-seconds', type=int, default=0)
    parser.add_argument('--not-before')
    parser.add_argument('--output', default='out/repo-audit/recovery-verification.json')
    args = parser.parse_args()
    if args.not_before and not moment(args.not_before):
        parser.error('--not-before requires timezone-aware ISO timestamp')
    if not 0 <= args.wait_seconds <= 480:
        parser.error('--wait-seconds must be between 0 and 480')
    if args.local:
        documents = {}
        for name in FILES:
            try:
                documents[name] = json.loads((Path('docs') / name).read_text())
            except (OSError, ValueError):
                documents[name] = {}
        final = evaluate(documents)
        report = {'status': 'LOCAL_DATA_HEALTHY' if final['healthy'] else 'BLOCKED', 'final': final}
    else:
        report = verify(args.wait_seconds, not_before=moment(args.not_before))
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as stream:
            stream.write('\n## Recovery outcome: ' + report['status'] + '\n\n')
            stream.write('Public data is not a browser UI verification. See the recovery receipt artifact.\n')
            stream.write('\nReasons: ' + ', '.join(report['final']['reasons']) + '\n')
    return 0 if report['final']['healthy'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
