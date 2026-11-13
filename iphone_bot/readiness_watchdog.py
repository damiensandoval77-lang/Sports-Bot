"""Wake the existing bounded readiness controller when its cron is late.

This watchdog never dispatches a collector directly. The readiness controller
retains its existing paid-collection cooldown, data checks, and active-run gate.
Inventory failure is fail-closed; a failed readiness report is still a recent
controller execution and must not cause a retry storm.
"""
import datetime as dt
import json
from pathlib import Path
from iphone_bot.heartbeat_recovery import gh, ACTIVE

WORKFLOW = 'production_readiness.yml'
MAX_IDLE_SECONDS = 20 * 60


def evaluate(*, now=None, command=gh):
    now = now or dt.datetime.now(dt.timezone.utc)
    result = {'checked_at': now.isoformat(), 'workflow': WORKFLOW}
    try:
        runs = json.loads(command(['run', 'list', '--workflow', WORKFLOW,
                                  '--limit', '30', '--json',
                                  'updatedAt,status,headBranch,event']))
        if not isinstance(runs, list):
            raise ValueError('INVALID_INVENTORY')
        for run in runs:
            if run.get('headBranch') != 'main' or run.get('event') == 'pull_request':
                continue
            if run.get('status') in ACTIVE:
                return dict(result, status='SKIPPED', reason='CONTROLLER_ACTIVE')
            if run.get('status') != 'completed':
                raise ValueError('UNKNOWN_RUN_STATUS')
            updated = dt.datetime.fromisoformat(run['updatedAt'].replace('Z', '+00:00'))
            if updated.tzinfo is None or updated > now:
                raise ValueError('INVALID_RUN_TIMESTAMP')
            if (now - updated).total_seconds() <= MAX_IDLE_SECONDS:
                return dict(result, status='SKIPPED', reason='CONTROLLER_RECENT')
    except Exception as exc:
        return dict(result, status='BLOCKED', reason='INVENTORY_UNAVAILABLE', error_type=type(exc).__name__)
    try:
        command(['workflow', 'run', WORKFLOW, '--ref', 'main'])
    except Exception as exc:
        return dict(result, status='BLOCKED', reason='DISPATCH_FAILED', error_type=type(exc).__name__)
    return dict(result, status='DISPATCHED', reason='CONTROLLER_IDLE_OVER_20_MINUTES')


if __name__ == '__main__':
    result = evaluate()
    Path('readiness_watchdog.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
    raise SystemExit(int(result['status'] == 'BLOCKED'))
