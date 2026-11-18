"""Resolve outcome-only evidence for frozen picks absent from the no-line archive.

Never create retrospective forecasts or mutate the independent AI-only ledger.
Only exact NBA player ID, team, opponent and Eastern game date matches qualify.
"""
import json
import re
from pathlib import Path
from zoneinfo import ZoneInfo
from iphone_bot.verified_final_cache import verified_row
from iphone_bot.paper_pick_pipeline import expected_opponents

CACHE = Path(__file__).resolve().parents[1]/'docs/verified_final_player_cache.json'


def augment_final_evidence(finals, frozen, rows=None):
    from iphone_bot.multimarket_forecast_ledger import valid, outcome_key, utc
    records = list((finals or {}).get('records', []))
    if frozen.get('status') != 'FROZEN_NEW_AI_ALL_MARKET':
        return {**(finals or {}), 'records': records}
    if rows is None:
        try:
            cache = json.loads(CACHE.read_text())
            rows = cache.get('rows', []) if cache.get('version') == 1 else []
        except (OSError, ValueError, TypeError):
            rows = []
    existing = {outcome_key(x) for x in records if isinstance(x, dict)}
    for pick in frozen.get('records', []):
        if not valid(pick) or outcome_key(pick) in existing:
            continue
        opponents = expected_opponents(pick['game'], pick['team'])
        if len(opponents) != 1:
            continue
        day = utc(pick['start']).astimezone(ZoneInfo('America/New_York')).date().isoformat()
        matches = [r for r in rows if isinstance(r, dict)
                   and str(r.get('nba_person_id', '')) == str(pick['player_id'])
                   and r.get('team') == pick['team'] and r.get('opponent') == opponents[0]
                   and r.get('date') == day]
        # Reject disagreements rather than using a convenient cache observation.
        if not matches or any(not verified_row(r) or r.get('source') != 'NBA_CDN_FINAL'
                              or r.get('dnp_final_verified') is True
                              or not re.fullmatch(r'00\d{8}', str(r.get('source_game_id', '')))
                              for r in matches):
            continue
        evidence = {(r['source_game_id'], float(r['PTS']), float(r['REB']),
                     float(r['AST']), float(r['PRA']), float(r['MIN'])) for r in matches}
        if len(evidence) != 1:
            continue
        row = matches[0]
        records.append({**{k: pick[k] for k in ('player_id', 'team', 'game', 'start', 'stat')},
                        'status': 'GRADED', 'actual': float(row[pick['stat']]),
                        'final_source': row['source'], 'source_game_id': row['source_game_id'],
                        'final_nba_person_id': str(row['nba_person_id']),
                        'final_player_name': row['player'],
                        'evidence_origin': 'VERIFIED_FINAL_CACHE_EXACT_FROZEN_PICK'})
        existing.add(outcome_key(pick))
    return {**(finals or {}), 'records': records}
