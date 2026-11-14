"""Refuse publishing a model built from an older verified provider snapshot."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def stamp(value):
    dt = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    if dt.tzinfo is None:
        raise ValueError('Timestamp must be timezone aware')
    return dt.astimezone(timezone.utc)


def check(source, model, now=None):
    now = now or datetime.now(timezone.utc)
    if source.get('status') != 'LIVE_THIRD_PARTY_PRIZEPICKS_LINES' or source.get('provider_status') not in ('fresh', 'partial'):
        return {'safe': True, 'reason': 'NO_NEW_VERIFIED_PROVIDER_SNAPSHOT'}
    try:
        issued = stamp(source['generated_at'])
        consumed = stamp(model['source_provider_generated_at'])
        if issued > now or consumed > now:
            raise ValueError('Future timestamp')
    except (KeyError, ValueError, TypeError):
        return {'safe': False, 'reason': 'INVALID_PROVIDER_SNAPSHOT_PROVENANCE'}
    return {'safe': issued <= consumed,
            'reason': 'CURRENT_PROVIDER_SNAPSHOT' if issued <= consumed else 'NEWER_PROVIDER_SNAPSHOT_REQUIRES_REGENERATION'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--provider', required=True)
    parser.add_argument('--model', required=True)
    args = parser.parse_args()
    result = check(json.loads(Path(args.provider).read_text()), json.loads(Path(args.model).read_text()))
    print(json.dumps(result))
    raise SystemExit(0 if result['safe'] else 1)


if __name__ == '__main__':
    main()
