"""Coalesce credit-free model runs without losing a newer quote snapshot.

An older active run cannot promise to have consumed a newly published source.
Queue one successor; an already queued successor for that source suppresses
further dispatches. This module never fetches provider data or dispatches itself.
"""
import argparse
import datetime as dt
import json
import sys
from pathlib import Path

ACTIVE = {'queued', 'pending', 'waiting', 'requested', 'in_progress'}

def stamp(value):
    try:
        result = dt.datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        if result.tzinfo is None:
            raise ValueError('timezone required')
        return result.astimezone(dt.timezone.utc)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError('Valid timezone-aware provider/run timestamp required') from exc

def covering_runs(runs, source_generated_at, now=None):
    now = now or dt.datetime.now(dt.timezone.utc)
    source = stamp(source_generated_at)
    if source > now + dt.timedelta(seconds=120):
        raise ValueError('Provider snapshot is in the future')
    covered = []
    for run in runs:
        if run.get('headBranch') != 'main':
            continue
        try:
            created = stamp(run.get('createdAt'))
        except ValueError:
            continue
        if created < source or created > now + dt.timedelta(seconds=120):
            continue
        active = run.get('status') in ACTIVE
        recent_success = (run.get('status') == 'completed' and
                          run.get('conclusion') == 'success' and
                          created >= now - dt.timedelta(seconds=60*60))
        if active or recent_success:
            covered.append(run)
    return covered

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    args = parser.parse_args()
    source = json.loads(args.source.read_text())
    runs = json.load(sys.stdin)
    print(len(covering_runs(runs, source.get('source_generated_at'))))

if __name__ == '__main__':
    main()
