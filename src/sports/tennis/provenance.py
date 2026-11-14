"""Local-only immutable quote receipts and unverified supplied-result research.

No network, production writer, schedule, probability, pick or model-hit-rate path.
A caller's verification assertion is NOT independently verified evidence. There is
no validated result adapter; all settlement output remains unverified research.
"""
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
from urllib.parse import urlparse

SOURCE = 'independent_prizepicksapi_com'
TIERS = ('standard', 'demon', 'goblin', 'unknown', None)


def _stamp(value):
    if not isinstance(value, str):
        raise ValueError('Timestamp string required')
    stamp = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
    if stamp.tzinfo is None:
        raise ValueError('Explicit timezone required')
    return stamp.astimezone(dt.timezone.utc)


def _text(value):
    if not isinstance(value, str) or not value.strip() or len(value) > 200:
        raise ValueError('Bounded nonempty text required')
    return value


def _url(value):
    parsed = urlparse(value if isinstance(value, str) else '')
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError('HTTPS source URL required')
    return value


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                      allow_nan=False).encode('utf-8')


def _hash(value):
    return hashlib.sha256(_canonical(value)).hexdigest()


def capture_quote(board, quote, *, source_url, as_of):
    """Return hash-bound minimal receipt; caller must persist it before kickoff.

    Optional opponent_player_id must already be exact same-provider evidence.
    Names cannot establish it. Missing opponent ID permits capture but not grading.
    """
    now = _stamp(as_of)
    if (board.get('schema_version') != 'tennis_board_v1' or board.get('source') != SOURCE
            or board.get('provider_mode') != 'live' or board.get('source_status') != 'fresh'
            or board.get('is_demo') is not False or quote not in board.get('quotes', [])):
        raise ValueError('Normalized live quote required')
    generated = _stamp(board['generated_at'])
    observed, captured, start = (_stamp(quote[k]) for k in ('observed_at', 'captured_at', 'starts_at'))
    if not observed <= captured <= generated <= now < start or now-observed > dt.timedelta(minutes=30):
        raise ValueError('Fresh pregame capture required')
    if (quote.get('status') != 'active' or quote.get('is_demo') is not False
            or quote.get('is_combo') is not False or quote.get('period') != 'full_match'
            or quote.get('tier') != 'standard'):
        raise ValueError('Active standard full-match singles quote required')
    line = quote.get('line')
    if isinstance(line, bool) or not isinstance(line, (float, int)) or not math.isfinite(line) or line < 0:
        raise ValueError('Finite nonnegative line required')
    sides = {}
    for side in ('more', 'less'):
        available, tier = quote.get(side+'_available'), quote.get(side+'_tier')
        if available is not None and not isinstance(available, bool) or tier not in TIERS:
            raise ValueError('Explicit side evidence required')
        sides[side] = {'available': available, 'tier': tier}
    if not any(s['available'] is True and s['tier'] == 'standard' for s in sides.values()):
        raise ValueError('No available standard side')
    fields = {k: _text(quote[k]) for k in ('id', 'player_id', 'fixture_id', 'player', 'opponent', 'stat')}
    if fields['player'].strip().casefold() == fields['opponent'].strip().casefold():
        raise ValueError('Self opponent')
    opponent_id = quote.get('opponent_player_id')
    if opponent_id is not None:
        opponent_id = _text(opponent_id)
        if opponent_id == fields['player_id']:
            raise ValueError('Self opponent ID')
    receipt = dict(schema='tennis_quote_receipt_v1', mode='offline_research_only', live_ready=False,
                   source=SOURCE, source_url=_url(source_url), **fields,
                   opponent_player_id=opponent_id, period='full_match', line=line,
                   observed_at=observed.isoformat(), captured_at=captured.isoformat(),
                   recorded_at=now.isoformat(), starts_at=start.isoformat(), sides=sides)
    return {'receipt': receipt, 'receipt_sha256': _hash(receipt)}


def write_receipt(envelope, directory):
    """Append-only content-addressed local file; never overwrite or add an index."""
    receipt = envelope['receipt']
    digest = _hash(receipt)
    if envelope.get('receipt_sha256') != digest or receipt.get('schema') != 'tennis_quote_receipt_v1':
        raise ValueError('Invalid receipt hash or schema')
    path = Path(directory) / (digest + '.json')
    path.parent.mkdir(parents=True, exist_ok=True)
    data = _canonical(envelope)
    try:
        with path.open('xb') as stream:
            stream.write(data)
    except FileExistsError:
        if path.read_bytes() != data:
            raise ValueError('Existing receipt conflict')
    return path


def supplied_result_outcome(envelope, result, *, as_of):
    """Describe Total Games line outcome, NEVER a model win/hit-rate.

    verified_result=True is a caller assertion, not an external verification.
    Matching IDs must share receipt source namespace; mappings by name forbidden.
    """
    receipt = envelope['receipt']
    if envelope.get('receipt_sha256') != _hash(receipt) or receipt.get('schema') != 'tennis_quote_receipt_v1':
        raise ValueError('Invalid receipt hash or schema')
    if receipt.get('stat') != 'Total Games':
        raise ValueError('Only symmetric Total Games supported')
    opponent = receipt.get('opponent_player_id')
    if not opponent:
        raise ValueError('Exact opponent ID missing from capture')
    participants = result.get('player_ids')
    if (result.get('source') != receipt['source'] or result.get('fixture_id') != receipt['fixture_id']
            or not isinstance(participants, list) or len(participants) != 2
            or not all(isinstance(p, str) for p in participants)
            or set(participants) != {receipt['player_id'], opponent}):
        raise ValueError('Exact same-provider fixture and participant IDs required')
    source_url = _url(result.get('source_url'))
    if result.get('verified_result') is not True or result.get('status') != 'completed':
        raise ValueError('Completed supplied-result assertion required')
    if result.get('retired') is not False or result.get('walkover') is not False:
        raise ValueError('Retirement/walkover status must be explicitly false')
    completed, observed, now = (_stamp(v) for v in (result['completed_at'], result['observed_at'], as_of))
    if not _stamp(receipt['recorded_at']) < _stamp(receipt['starts_at']) < completed <= observed <= now:
        raise ValueError('Result chronology invalid')
    from src.sports.tennis.valuebetennis import symmetric_score_targets
    total = symmetric_score_targets(result.get('score'))['total_games']
    outcome = 'OVER' if total > receipt['line'] else 'UNDER' if total < receipt['line'] else 'PUSH'
    return dict(mode='offline_research_only', live_ready=False,
                evidence_status='unverified_supplied_result', result_adapter_validated=False,
                verification_note='Caller assertion is not independent external verification',
                receipt_sha256=envelope['receipt_sha256'], source=receipt['source'],
                source_url=source_url, fixture_id=receipt['fixture_id'], stat='Total Games',
                line=receipt['line'], actual_total_games=total, line_outcome=outcome,
                completed_at=completed.isoformat(), result_observed_at=observed.isoformat(),
                model_pick_issued=False, model_win=None, model_hit_rate=None)
