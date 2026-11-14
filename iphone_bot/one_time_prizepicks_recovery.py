"""One manually authorized NBA provider read, never an automatic fallback.

The workflow commits a durable claim BEFORE requesting paid data. A cancelled
or failed attempt consumes this authorization too. No pagination or retries.
"""
import argparse
import datetime as dt
import json
import os
import re
import subprocess
from pathlib import Path
import urllib.request
import urllib.parse
from iphone_bot import fetch_prizepicks as provider

AUTHORIZATION = 'nba-2026-11-14-2228-single-compact'
START = provider.timeparse('2026-11-14T22:28:00Z')
END = provider.timeparse('2026-11-15T00:00:00Z')
LAST_PAID = '2026-11-14T19:12:37Z'
MAX_PAGES = 1
MAX_TARGETED_READS = 0
MAX_CREDITS = 10  # Documented compact limit1000 cost; below authorized40 ceiling.
RECEIPT = 'prizepicks_one_time_recovery.json'


def window(now):
    if not START <= now < END:
        raise ValueError('outside the single authorized pretip window')


def claim(prior, now, run_id, run_attempt='1'):
    window(now)
    if not run_id or run_attempt != '1':
        raise ValueError('reruns are not authorized')
    if prior.get('authorization_id') != AUTHORIZATION or prior.get('status') != 'UNUSED':
        raise ValueError('authorization already consumed or receipt missing')
    last = provider.timeparse(prior.get('last_paid_read_at'))
    if not last or last >= START:
        raise ValueError('paid receipt cooldown blocks this window')
    return {**prior, 'status': 'CLAIMED_NO_RETRY', 'claimed_at': now.isoformat(),
            'run_id': str(run_id), 'max_requests': 1, 'max_pages': MAX_PAGES,
            'max_targeted_reads': MAX_TARGETED_READS, 'max_documented_credits': MAX_CREDITS,
            'fresh_quotes_published': False, 'ongoing_polling_enabled': False}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('provider redirect rejected; authorization consumed')


def read_once(key):
    query = urllib.parse.urlencode(provider.standard_query(limit=1000))
    req = urllib.request.Request(provider.BASE+'?'+query, headers={
        'Authorization': 'Bearer '+key, 'Accept': 'application/json'})
    # urllib has no automatic retry. Reject redirects: exactly one HTTP request.
    with urllib.request.build_opener(NoRedirect()).open(req, timeout=30) as reply:
        data = json.load(reply)
        usage = {field: reply.headers.get(header) for header, field in (
            ('X-Credits-Cost','charged_credits'),
            ('X-Credits-Remaining','remaining_credits_header'),('X-Usage-Unit','usage_unit'))}
        return data, usage


def validate_board(page, schedule, now):
    if not isinstance(page, dict) or not isinstance(page.get('meta'), dict):
        raise ValueError('invalid provider envelope')
    if page['meta'].get('mode') != 'live' or page['meta'].get('source_status') != 'fresh':
        raise ValueError('provider is not live and fresh')
    rows = page.get('data')
    if not isinstance(rows, list) or not rows or len(rows) > 1000:
        raise ValueError('empty or oversized provider page')
    fresh = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        observed = provider.timeparse(row.get('observed_at'))
        # Keep authentic source timestamp, never restamp old quotes as current.
        if observed and dt.timedelta(0) <= now-observed <= dt.timedelta(minutes=60):
            fresh.append(row)
    board = provider.publish([{**page, 'data': fresh}], [], now=now, schedule=schedule)
    board['board_offers'] = [row for row in board['board_offers']
        if row['more_tier'] == row['less_tier'] == 'standard']
    if not board['board_offers']:
        raise ValueError('no fresh schedule-verified standard board')
    board['independent_board_count'] = len(board['board_offers'])
    board['games_with_independent_lines'] = len({r['game'] for r in board['board_offers']})
    board['complete_provider_board'] = False
    board['partial_board'] = True  # One page never proves complete slate coverage.
    board['one_time_recovery_authorization'] = AUTHORIZATION
    return board


def execute(receipt, schedule, now, run_id, key, reader=read_once, clock=None):
    window(now)
    if (receipt.get('status') != 'CLAIMED_NO_RETRY' or
        receipt.get('authorization_id') != AUTHORIZATION or receipt.get('run_id') != str(run_id)):
        raise ValueError('no durable matching one-shot claim')
    clock = clock or (lambda: dt.datetime.now(dt.timezone.utc))
    result = {**receipt, 'status': 'FAILED_PRIOR_SNAPSHOT_PRESERVED',
              'attempted_at': now.isoformat(), 'fresh_quotes_published': False, 'api_requests_made': 0}
    board = None
    try:
        if not key:
            raise ValueError('existing provider secret missing')
        result['api_requests_made'] = 1
        page, usage = reader(key)
        # Only explicitly allowlisted bounded accounting headers, never bodies/errors.
        for name in ('charged_credits','remaining_credits_header','usage_unit'):
            value = usage.get(name)
            if value is not None:
                result[name] = str(value)[:45]
        cost = result.get('charged_credits')
        if cost is not None and (not cost.isdigit() or int(cost) > MAX_CREDITS):
            raise ValueError('provider reported unexpected credit cost')
        received = clock()
        result['response_received_at'] = received.isoformat()
        window(received)
        board = validate_board(page, schedule, received)
        result.update(status='FRESH_PARTIAL_BOARD_PUBLISHED', fresh_quotes_published=True,
                      published_offer_count=len(board['board_offers']))
    except Exception as exc:
        # Error messages and HTTP bodies may contain sensitive provider details.
        result['error_type'] = type(exc).__name__
        code = getattr(exc, 'code', None)
        if isinstance(code, int):
            result['http_status'] = code
    result['completed_at'] = clock().isoformat()
    return result, board


REQUEST_PATH = 'docs/prizepicks_one_time_recovery_request.json'


def authorize_trigger(event_name, ref, force, now, request=None, event=None, changed_paths=()):
    """Allow manual dispatch or the exact one-off request-file push only."""
    window(now)
    if ref != 'refs/heads/main' or force != '1':
        raise ValueError('main-only explicit recovery trigger required')
    if event_name == 'workflow_dispatch':
        return
    if event_name != 'push' or not isinstance(request, dict) or not isinstance(event, dict):
        raise ValueError('invalid one-off request trigger')
    if event.get('ref') != ref or event.get('deleted') is True:
        raise ValueError('invalid push ref')
    if REQUEST_PATH not in changed_paths:
        raise ValueError('push did not add or modify the one-off request')
    requested = provider.timeparse(request.get('requested_at'))
    if (request.get('authorization_id') != AUTHORIZATION or
        request.get('action') != 'EXECUTE_SINGLE_AUTHORIZED_COMPACT_READ' or
        requested is None or not START <= requested <= now < END):
        raise ValueError('mismatched or expired one-off request')


def changed_request_paths(event, github_sha):
    # Actions push payloads may omit per-commit added/modified arrays. Verify
    # the actual pushed Git diff instead, never trust a stale request's presence.
    before, after = event.get('before'), event.get('after')
    if (not all(isinstance(v,str) and re.fullmatch(r'[0-9a-f]{40}',v)
                for v in (before,after)) or after != github_sha or before == '0'*40):
        raise ValueError('unverified push commit range')
    output = subprocess.check_output(['git','diff','--name-only','--diff-filter=AM',
                                     before, after, '--', REQUEST_PATH], text=True)
    return output.splitlines()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['claim','fetch'])
    args = parser.parse_args()
    docs = Path(__file__).resolve().parents[1]/'docs'
    path = docs/RECEIPT
    prior = json.loads(path.read_text())
    now = dt.datetime.now(dt.timezone.utc)
    event_name = os.environ.get('GITHUB_EVENT_NAME', '')
    request = event = None
    changed_paths = ()
    if event_name == 'push':
        request = json.loads((docs/Path(REQUEST_PATH).name).read_text())
        event = json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text())
        changed_paths = changed_request_paths(event, os.environ.get('GITHUB_SHA'))
    authorize_trigger(event_name, os.environ.get('GITHUB_REF'),
                      os.environ.get('PRIZEPICKS_FORCE_REFRESH'), now, request, event, changed_paths)
    run = os.environ.get('GITHUB_RUN_ID', '')
    if args.mode == 'claim':
        output = claim(prior, now, run, os.environ.get('GITHUB_RUN_ATTEMPT',''))
        path.write_text(json.dumps(output, indent=2)+'\n')
        return
    output, board = execute(prior, json.loads((docs/'nba_schedule.json').read_text()), now,
                            run, os.environ.get('PRIZEPICKS_API_KEY',''))
    path.write_text(json.dumps(output, indent=2)+'\n')
    if board is not None:
        target = docs/'prizepicks.json'
        tmp = target.with_suffix('.tmp')
        tmp.write_text(json.dumps(board, indent=2)+'\n')
        tmp.replace(target)
    health = {'checked_at': output.get('completed_at'),
        'status': 'FRESH_LINES_PUBLISHED' if board is not None else 'PAID_READ_FAILED_PRIOR_SNAPSHOT_PRESERVED',
        'source': 'independent_prizepicksapi_com', 'source_url': provider.BASE,
        'authorization_id': AUTHORIZATION, 'api_requests_made': output['api_requests_made'],
        'prior_snapshot_preserved': board is None, 'fresh_quotes_published': board is not None,
        'credits_reported_charged': output.get('charged_credits'),
        'monthly_credits_header': output.get('remaining_credits_header'),
        'topup_balance_not_exposed_by_monthly_header': True,
        'billing_scope': 'SINGLE_AUTHORIZED_COMPACT_READ_NO_RETRY',
        'matched_upcoming_offers': len(board['board_offers']) if board else 0,
        'source_board_remains_partial': True,
        'error_type': output.get('error_type'), 'http_status': output.get('http_status')}
    (docs/'prizepicks_refresh_health.json').write_text(json.dumps(health, indent=2)+'\n')
    print(json.dumps({'status':output['status'], 'fresh_quotes_published':board is not None}))


if __name__ == '__main__':
    main()
