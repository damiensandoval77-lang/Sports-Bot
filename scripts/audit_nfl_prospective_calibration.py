"""Measure genuine frozen real-line probabilities. Never fit/rewrite forecasts.

Pushes are non-wins for unconditional Brier scoring; the separate settled hit
rate excludes them. Observations are correlated within games and players.
"""
import argparse
import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


def number(x):
    try:
        v = float(x)
        return v if math.isfinite(v) else None
    except (TypeError, ValueError):
        return None


def timestamp(x):
    try:
        v = datetime.fromisoformat(str(x).replace('Z', '+00:00'))
        return v if v.tzinfo else None
    except ValueError:
        return None


def observation(row, games):
    if row.get('odds_type') != 'standard': return None, 'not_standard'
    if row.get('grade_status') != 'graded': return None, 'not_graded'
    game = games.get(row.get('game_id'), {})
    if game.get('status') != 'final': return None, 'not_verified_final'
    try: e = json.loads(row.get('matchup_evidence') or '')
    except (ValueError, TypeError): return None, 'no_probability_evidence'
    if not isinstance(e, dict): return None, 'invalid_evidence'
    start, capture, observed = map(timestamp, (game.get('kickoff_utc'), e.get('captured_at'), e.get('observed_at')))
    if not all((start, capture, observed)) or not observed <= capture < start: return None, 'not_pregame'
    if timestamp(row.get('captured_at')) != capture: return None, 'capture_mismatch'
    for k in ('game_id', 'player_id', 'team', 'opponent', 'target'):
        if not row.get(k) or row[k] != e.get(k): return None, 'identity_mismatch'
    if {row['team'], row['opponent']} != {game.get('home'), game.get('away')}: return None, 'team_mismatch'
    line, actual = number(row.get('line')), number(row.get('actual'))
    if line is None or actual is None or line != number(e.get('original_line')): return None, 'line_or_actual_invalid'
    direction = str(row.get('pick', '')).upper()
    if direction not in ('MORE', 'LESS') or direction != e.get('direction'): return None, 'direction_mismatch'
    artifact = e.get('artifact_sha256', '')
    if len(artifact) != 64 or any(c not in '0123456789abcdef' for c in artifact): return None, 'artifact_missing'
    more, less, push = [number(e.get(k)) for k in ('modeled_more_probability', 'modeled_less_probability', 'modeled_push_probability')]
    if e.get('schema') == 'NFL_OPPONENT_FEATURES_V1':
        if line.is_integer(): return None, 'legacy_integer_push_unknown'
        less, push = (1-more if more is not None else None), 0.
    elif e.get('schema') != 'NFL_OPPONENT_FEATURES_V2': return None, 'unknown_schema'
    if any(x is None or not 0 <= x <= 1 for x in (more, less, push)) or abs(more+less+push-1) > 1e-8: return None, 'invalid_distribution'
    p = more if direction == 'MORE' else less
    if number(e.get('selected_probability')) is None or abs(p-number(e['selected_probability'])) > 1e-8: return None, 'selected_probability_mismatch'
    result = 'Push' if actual == line else ('More' if actual > line else 'Less')
    if result != row.get('result'): return None, 'outcome_mismatch'
    win = result.upper() == direction
    if (result == 'Push' and row.get('won') not in ('', None)) or (result != 'Push' and number(row.get('won')) != int(win)): return None, 'grade_mismatch'
    support = e.get('training_support') or {}
    context = e.get('eligibility_context') or {}
    event_attested = (bool(e.get('provider_game_id')) and e.get('provider_team') == row['team']
                      and timestamp(e.get('provider_start_time')) == start)
    support_attested = (support.get('verified') is True and support.get('target') == row['target']
                        and support.get('position') == row.get('position') and support.get('source') == 'NFL_TRAINING_RULES_V1')
    return dict(game=row['game_id'], player=row['player_id'], market=row['target'], position=row.get('position') or 'unknown',
                direction=direction, line=line, capture=capture.isoformat(), model=e.get('model_id', 'unknown'), artifact=artifact,
                p=p, push_probability=push, win=int(win), push=int(result=='Push'),
                evidence_cohort=('event_attested' if event_attested else 'legacy_event_unattested') + '/' +
                                ('training_support_attested' if support_attested else 'legacy_training_support_unknown'),
                role='returner_uncertain' if context.get('playing_time_uncertain') else ('training_supported' if support.get('verified') is True else 'legacy_support_unknown')), None


def summarize(items):
    if not items: return dict(rows=0, games=0, players=0)
    n = len(items); pushes = sum(x['push'] for x in items); wins = sum(x['win'] for x in items)
    return dict(rows=n, games=len({x['game'] for x in items}), players=len({(x['game'],x['player']) for x in items}),
                wins=wins, losses=n-pushes-wins, pushes=pushes,
                settled_hit_rate=wins/(n-pushes) if n>pushes else None,
                predicted_unconditional_win=sum(x['p'] for x in items)/n,
                observed_unconditional_win=wins/n,
                brier_unconditional=sum((x['p']-x['win'])**2 for x in items)/n)


def build(rows, schedule):
    games = {g['game_id']:g for g in schedule['games']}
    accepted, excluded, identities = [], Counter(), set()
    for row in rows:
        item, why = observation(row, games)
        if why: excluded[why] += 1; continue
        key = (item['game'],item['player'],item['market'],item['line'])
        if key in identities: raise ValueError('Duplicate frozen standard line; refuse biased calibration')
        identities.add(key); accepted.append(item)
    groups = {}
    for dim in ('game','market','direction','position','role','artifact','evidence_cohort'):
        d=defaultdict(list)
        for item in accepted: d[item[dim]].append(item)
        groups[dim]={k:summarize(v) for k,v in sorted(d.items())}
    bins=[]
    for lo,hi in ((0,.5),(.5,.6),(.6,.7),(.7,.8),(.8,.9),(.9,1.000001)):
        bins.append(dict(lower=lo,upper=min(hi,1),**summarize([x for x in accepted if lo<=x['p']<hi])))
    return dict(schema='NFL_REAL_FROZEN_CALIBRATION_V1', calibrated=False,
                claim='DESCRIPTIVE_ONLY_NOT_A_CALIBRATED_MODEL_OR_INDEPENDENT_WAGER_SAMPLE',
                probability_definition='Selected-side unconditional win; pushes are non-wins in Brier, excluded only from settled hit rate.',
                limitations=['Correlated player markets within games; do not interpret row count as independent trials.',
                            'Legacy captures without complete pregame probability evidence are excluded.',
                            'No weights, thresholds, or probabilities are fitted from these results.',
                            'Role slices reflect only context captured before kickoff, never retrospective role assignments.',
                            'Legacy event/training support was not attested; cohorts remain separate from later repaired captures.'],
                summary=summarize(accepted),excluded=dict(sorted(excluded.items())),by=groups,bins=bins)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--data-dir',default='docs/nfl/data');args=parser.parse_args()
    base=Path(args.data_dir); source=base/'pp_graded_2026.csv';schedule=base/'schedule_2026.json'
    report=build(list(csv.DictReader(source.open())),json.loads(schedule.read_text()))
    report['source_sha256']=hashlib.sha256(source.read_bytes()).hexdigest()
    report['schedule_sha256']=hashlib.sha256(schedule.read_bytes()).hexdigest()
    (base/'prospective_calibration_2026.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps(report['summary']))

if __name__=='__main__': main()
