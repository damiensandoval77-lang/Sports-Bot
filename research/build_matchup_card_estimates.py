"""Compact, lossless research-preview projection for frozen card identities.

No forecasts are computed here. Exact prospective archived observations survive
rotation of the current market feed. All row capture/provenance times are retained.
"""
import argparse
import json
from datetime import datetime, timedelta, timezone
from math import isfinite
from pathlib import Path
from research.publish_matchup_shadow_guard import EXPECTED, METHOD, stamp
from research.archive_matchup_forecasts import STATUS

POLICY = "EXPERIMENTAL_MATCHUP_PREVIEW_NOT_CERTIFIED_HIT_EST"
PROVENANCE = ("position_observed_at", "player_observed_at", "rating_observed_at", "minutes_snapshot_at")

def number(x):
    return type(x) in (int, float) and isfinite(x)

def identity(row, side):
    # Team/opponent + exact scheduled start are the common game identity in both
    # schemas. Neither source consistently contains a separate game ID.
    return (str(row['player_id']), row['team'], row['opponent'], row['stat'],
            stamp(row['start']), float(row['line']), side)

def build(ledger, archive, current, now=None):
    now = now or datetime.now(timezone.utc)
    if ledger.get('status') != 'FROZEN_NEW_AI_ALL_MARKET':
        raise ValueError('invalid frozen ledger')
    if archive.get('status') != STATUS or archive.get('version') != 1 or not isinstance(archive.get('forecasts'), list):
        raise ValueError('invalid prospective archive')
    if current.get('status') != EXPECTED or current.get('production_approved') is not False or current.get('calibrated') is not False or current.get('presentation_policy') != POLICY:
        raise ValueError('invalid current research feed')
    if not isinstance(current.get('records'), list):
        raise ValueError('invalid current research records')
    current_at = stamp(current['captured_at'])
    if current_at > now + timedelta(seconds=120):
        raise ValueError('current research snapshot is in the future')
    primary = {}
    for p in ledger.get('records', []):
        if not isinstance(p, dict):
            continue
        try:
            start, captured = stamp(p['start']), stamp(p['captured_at'])
            side = p['estimated_hit_chance']['modeled_direction'].upper()
            if not (now-timedelta(hours=48) <= start <= now+timedelta(days=7)):
                continue
            if (p.get('pickem_tier') != 'standard' or p.get('standard_line_two_sided_verified') is not True or
                p.get('research_only') is not True or p.get('production_replaced') is not False or
                side not in ('MORE', 'LESS') or not number(p.get('line')) or
                not number(p.get('projection')) or p['line'] <= 0 or p['projection'] < 0 or not stamp(p['market_updated']) <= captured < start):
                continue
            key = identity(p, side)
            primary[key] = min(primary.get(key, captured), captured)
        except (KeyError, TypeError, ValueError, AttributeError):
            continue
    candidates = list(archive['forecasts'])
    for row in current.get('records', []):
        if not isinstance(row, dict):
            continue
        candidates.append({**row, 'research_snapshot_captured_at': current.get('captured_at'),
                           'source_run_id': current.get('model_id'), 'observed_as_prospective': True})
    unique, conflicts = {}, set()
    for row in candidates:
        if not isinstance(row, dict):
            continue
        try:
            captured, start = stamp(row['captured_at']), stamp(row['start'])
            snapshot = stamp(row['research_snapshot_captured_at'])
            key = identity(row, row['original_side'])
            chance = row['estimated_hit_chance']
            if not isinstance(chance, dict):
                continue
            provenance = chance.get('source_provenance')
            if not isinstance(provenance, dict):
                continue
            if (key not in primary or row.get('observed_as_prospective') is not True or
                not primary[key] <= captured <= snapshot < start or snapshot > now+timedelta(seconds=120) or
                row['stat'] not in ('PTS','REB','AST','PRA') or row['original_side'] not in ('MORE','LESS') or
                not all(row.get(k) for k in ('player_id','team','opponent')) or
                not all(number(row.get(k)) for k in ('line','original_projection','matchup_projection')) or
                row['line'] <= 0 or row['original_projection'] < 0 or row['matchup_projection'] < 0 or
                chance.get('method') != METHOD or chance.get('calibrated') is not False or
                chance.get('research_only') is not True or chance.get('verified_betting_edge') is not False or
                chance.get('opponent_aware_inputs_sourced') is not True or chance.get('opponent_adjustment_validated') is not False or
                not number(chance.get('modeled_selected_probability')) or
                not 0 <= chance['modeled_selected_probability'] <= 1 or
                not all(stamp(provenance[k]) <= captured for k in PROVENANCE)):
                continue
            observation = (key, captured)
            # Current snapshots can carry a different run/snapshot wrapper for an
            # identical original forecast. Compare scientific contents, not wrapper.
            core = {k:v for k,v in row.items() if k not in ('research_snapshot_captured_at','source_run_id','observed_as_prospective')}
            if observation in unique and unique[observation][1] != core:
                conflicts.add(observation)
            elif observation not in unique:
                unique[observation] = (row, core)
        except (KeyError, TypeError, ValueError):
            continue
    selected = {}
    for (key, captured), (row, _) in unique.items():
        if (key, captured) in conflicts:
            continue
        if key not in selected or captured > stamp(selected[key]['captured_at']):
            selected[key] = row
    records = sorted(selected.values(), key=lambda r: (r['start'], str(r['player_id']), r['stat'], r['line'], r['original_side']))
    # This is source observation time, NOT build time; no false freshness signal.
    source_at = max((stamp(r['research_snapshot_captured_at']) for r in records), default=stamp(current['captured_at']))
    return {'status': EXPECTED, 'production_approved': False, 'calibrated': False,
            'published_to_cards': False, 'presentation_policy': POLICY,
            'captured_at': source_at.isoformat(), 'eligible_opponent_conditioned_estimates': len(records),
            'derivation': 'Exact prospective archived/current research observations for frozen cards; no probabilities recalculated. Original row timestamps retained.',
            'conflicting_observations_excluded': len(conflicts), 'records': records}

def main():
    parser = argparse.ArgumentParser()
    for arg in ('ledger','archive','current','output'):
        parser.add_argument('--'+arg, required=True)
    args = parser.parse_args()
    result = build(*(json.loads(Path(getattr(args,k)).read_text()) for k in ('ledger','archive','current')))
    Path(args.output).write_text(json.dumps(result, separators=(',',':'), sort_keys=True)+'\n')
    print(json.dumps({'records': len(result['records']), 'conflicts': result['conflicting_observations_excluded']}))
if __name__ == '__main__':
    main()
