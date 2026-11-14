"""Free public NBA quotes. No credentials, paid fallback, or post-tip backfill."""
import datetime as dt
import json
import math
from collections import Counter
from pathlib import Path
from urllib.request import Request, urlopen
from .fetch_prizepicks import timeparse, STAT
from .paper_pick_pipeline import expected_opponents
from .prizepicks_provenance import NATIVE

ROOT = Path(__file__).resolve().parents[1]
URL = 'https://api.prizepicks.com/projections?league_id=7&per_page=250&single_stat=true'

def build(payload, schedule, observed_at):
    now = timeparse(observed_at)
    if now is None: raise ValueError('Missing actual retrieval timestamp')
    if not isinstance(payload, dict) or not isinstance(payload.get('data'), list):
        raise ValueError('Invalid native response')
    meta = payload.get('meta') or {}
    # A changed pagination contract must not silently truncate production.
    if meta.get('current_page') != 1 or meta.get('total_pages') != 1:
        raise ValueError('Incomplete native pagination; preserve prior snapshot')
    included = {(x.get('type'), str(x.get('id'))): x.get('attributes', {})
                for x in payload.get('included', []) if isinstance(x, dict)}
    rejected = Counter(); offers = []
    def related(row, key):
        ref = row.get('relationships', {}).get(key, {}).get('data') or {}
        return included.get((ref.get('type'), str(ref.get('id'))), {})
    for row in payload['data']:
        if not isinstance(row, dict): rejected['invalid_row'] += 1; continue
        a = row.get('attributes') or {}; p = related(row, 'new_player')
        if (a.get('odds_type') != 'standard' or a.get('allowed_wager_types') != 'under_or_over'):
            rejected['not_explicit_two_sided_standard'] += 1; continue
        if (row.get('type') != 'projection' or a.get('status') != 'pre_game'
                or a.get('is_live') is not False or a.get('in_game') is not False
                or a.get('is_promo') is not False):
            rejected['not_explicit_pregame_nonpromo'] += 1; continue
        if (p.get('league') != 'NBA' or p.get('combo') is not False
                or related(row, 'duration').get('name') != 'Full'):
            rejected['not_single_player_nba_full_game'] += 1; continue
        stat = STAT.get(str(a.get('stat_type', '')).lower())
        if not stat: rejected['unsupported_stat'] += 1; continue
        start = timeparse(a.get('start_time')); updated = timeparse(a.get('updated_at'))
        if not start or not now < start <= now + dt.timedelta(hours=72):
            rejected['not_upcoming'] += 1; continue
        if updated and updated > now + dt.timedelta(minutes=10):
            rejected['future_provider_timestamp'] += 1; continue
        line = a.get('line_score'); team = str(p.get('team', '')).upper()
        opponent = str(a.get('description', '')).upper()
        if (type(line) not in (float, int) or not math.isfinite(line) or not 0 <= line < 200
                or not p.get('name') or not row.get('id') or len(team) != 3 or len(opponent) != 3):
            rejected['invalid_identity_or_line'] += 1; continue
        games = [g for g in schedule.get('games', [])
                 if opponent in expected_opponents(g.get('game'), team)
                 and timeparse(g.get('start'))
                 and abs((timeparse(g['start']) - start).total_seconds()) <= 1800]
        if len(games) != 1: rejected['no_unique_scheduled_game'] += 1; continue
        offers.append({'id': 'native:' + str(row['id']), 'player': p['name'], 'team': team,
            'opponent': opponent, 'game': games[0]['game'], 'stat': stat, 'line': line,
            'starts_at': start.isoformat(), 'observed_at': now.isoformat(),
            'provider_updated_at': a.get('updated_at'),
            'more_tier': 'standard', 'less_tier': 'standard', 'source': NATIVE,
            'is_demo': False, 'event_start_source': 'provider'})
    groups = {}
    for q in offers:
        key = tuple(q[k] for k in ('player', 'team', 'game', 'stat', 'starts_at'))
        groups.setdefault(key, []).append(q)
    board = []
    for rows in groups.values():
        if len({q['line'] for q in rows}) != 1:
            rejected['conflicting_simultaneous_lines'] += len(rows); continue
        board.append(rows[0])
    if not board: raise ValueError('No verified upcoming native quotes; preserve prior snapshot')
    return {'status': 'LIVE_NATIVE_PRIZEPICKS_LINES', 'source': NATIVE, 'source_url': URL,
        'generated_at': now.isoformat(), 'provider_status': 'fresh', 'pages_read': 1,
        # Only supported, explicitly two-sided full-game markets are exported.
        # Do not claim complete unrestricted provider coverage.
        'partial_board': True, 'complete_provider_board': False,
        'board_coverage_scope': 'NBA_NATIVE_TWO_SIDED_STANDARD_SUPPORTED_MARKETS',
        'raw_rows_read': len(payload['data']), 'eligible_upcoming_offers': len(board),
        'filtered_out_reasons': dict(rejected), 'independent_board_count': len(board),
        'games_with_independent_lines': len({q['game'] for q in board}),
        'matched_count': 0, 'offers': [], 'board_offers': board,
        'unassigned_or_ambiguous_events': rejected['no_unique_scheduled_game'],
        'unassigned_reason_counts': {'no_unique_scheduled_game': rejected['no_unique_scheduled_game']},
        'total_provider_charged_credits': 0,
        'notice': 'Observed public standard pickem quotes, not sportsbook odds. Unsupported markets excluded.'}

def main():
    # One public request. A denial or schema change fails closed; no paid retry.
    request = Request(URL, headers={'User-Agent': 'DamesPicks-Audit/1.0', 'Accept': 'application/json'})
    with urlopen(request, timeout=30) as response:
        payload = json.load(response)
    observed = dt.datetime.now(dt.timezone.utc).isoformat()
    board = build(payload, json.loads((ROOT/'docs/nba_schedule.json').read_text()), observed)
    target = ROOT/'docs/prizepicks.json'
    if target.exists():
        previous = timeparse(json.loads(target.read_text()).get('generated_at'))
        if previous and previous >= timeparse(observed): raise ValueError('Newer snapshot already saved')
    target.write_text(json.dumps(board, ensure_ascii=False, separators=(',', ':'))+'\n')
    print(json.dumps({'status': board['status'], 'generated_at': observed,
                      'markets': len(board['board_offers']), 'games': board['games_with_independent_lines']}))

if __name__ == '__main__': main()
