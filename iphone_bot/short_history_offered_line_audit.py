"""Read-only prospective offered-line diagnostics. Never a release authorization.

Select earliest receipt per candidate version and exact offer before inspecting
outcomes. Missing outcomes stay pending; repeated captures cannot inflate N.
"""
from collections import Counter, defaultdict
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
from zoneinfo import ZoneInfo
import numpy as np


def timestamp(value):
    t = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if t.tzinfo is None:
        raise ValueError('NAIVE_TIME')
    return t


def audit(archive):
    selected = {}; rejected = Counter()
    for r in archive.get('records', []):
        try:
            captured, tip = timestamp(r['captured_at']), timestamp(r['start'])
            if not timestamp(r['market_updated']) <= captured < tip:
                raise ValueError('NOT_PRETIP')
            if (r.get('pickem_tier') != 'standard' or
                r.get('standard_line_two_sided_verified') is not True or
                r.get('primary_model_eligible') is not False):
                raise ValueError('INVALID_RESEARCH_OFFER')
            if not r.get('history_dates') or any(d >= tip.astimezone(ZoneInfo('America/New_York')).date().isoformat() for d in r['history_dates']):
                raise ValueError('NONPRIOR_HISTORY')
            line = r['line']
            if type(line) not in (int, float) or not math.isfinite(line) or line < 0:
                raise ValueError('INVALID_LINE')
            version = tuple(r[k] for k in ('candidate_model', 'spec_sha256', 'artifact_sha256'))
            identity = tuple(r[k] for k in ('player_id', 'team', 'opponent', 'game', 'start', 'stat'))
            key = (*version, *identity, line)
            if key not in selected or captured < timestamp(selected[key]['captured_at']):
                selected[key] = r
        except (ValueError, KeyError, TypeError) as exc:
            rejected[str(exc)] += 1
    cohorts = defaultdict(list); pending = 0; voids = 0
    for key, r in selected.items():
        outcome = archive.get('outcomes', {}).get(r['receipt_key'])
        if not outcome:
            pending += 1; continue
        if outcome.get('result') == 'VOID_DNP':
            voids += 1; continue
        try:
            actual = outcome['actual']
            if (type(actual) not in (int, float) or not math.isfinite(actual) or actual < 0 or
                outcome.get('source') not in ('NBA_CDN_FINAL', 'ESPN_FINAL') or
                not outcome.get('source_game_id') or
                timestamp(outcome['observed_at']) <= timestamp(r['start'])):
                raise ValueError('INVALID_FINAL')
            expected = 'OVER' if actual > r['line'] else 'UNDER' if actual < r['line'] else 'PUSH'
            if outcome.get('result') != expected:
                raise ValueError('OUTCOME_CONFLICT')
            mode = 'half_integer_mapped' if r['line'] % 1 == .5 else 'raw_three_way'
            ps = []
            for prefix in ('research', 'baseline'):
                triple = [r[prefix + '_probability_' + side] for side in ('over','under','push')]
                if any(type(v) not in (int,float) or not math.isfinite(v) or not 0 <= v <= 1 for v in triple) or abs(sum(triple)-1) > 1e-8:
                    raise ValueError('INVALID_PROBABILITIES')
                if mode == 'half_integer_mapped':
                    p = r[prefix + '_half_integer_calibrated_map_over']
                    if type(p) not in (int,float) or not math.isfinite(p) or not 0 <= p <= 1 or triple[2] != 0:
                        raise ValueError('INVALID_HALF_INTEGER_MAP')
                    triple = [p, 1-p, 0.]
                ps.append(triple)
            y = [float(expected == side) for side in ('OVER','UNDER','PUSH')]
            # Three-way Brier includes pushes; half-line binary Brier is half this.
            errors = [sum((p-v)**2 for p,v in zip(triple,y)) for triple in ps]
            cohort = (*key[:3], r['stat'], mode)
            cohorts[cohort].append(dict(date=timestamp(r['start']).astimezone(ZoneInfo('America/New_York')).date().isoformat(),
                game=outcome['source_game_id'], player=r['player_id'], errors=errors))
        except (ValueError, KeyError, TypeError) as exc:
            rejected[str(exc)] += 1
    results=[]
    for cohort, rows in sorted(cohorts.items()):
        dates=sorted({r['date'] for r in rows}); errors=np.array([r['errors'] for r in rows]); delta=errors[:,0]-errors[:,1]
        ci=None
        # Do not manufacture a confidence interval from one evening.
        if len(dates)>=30:
            sums=np.array([sum(delta[i] for i,r in enumerate(rows) if r['date']==d) for d in dates])
            counts=np.array([sum(r['date']==d for r in rows) for d in dates])
            ix=np.random.default_rng(20261114).integers(0,len(dates),size=(2000,len(dates)))
            ci=np.quantile(sums[ix].sum(axis=1)/counts[ix].sum(axis=1),[.025,.975]).tolist()
        results.append(dict(model=cohort[0],spec_sha256=cohort[1],artifact_sha256=cohort[2],stat=cohort[3],scoring=cohort[4],
            offers=len(rows),player_games=len({(r['player'],r['game']) for r in rows}),games=len({r['game'] for r in rows}),dates=len(dates),
            three_way_brier=float(errors[:,0].mean()),baseline_three_way_brier=float(errors[:,1].mean()),difference=float(delta.mean()),date_cluster_ci95=ci))
    return dict(status='PROSPECTIVE_ACTUAL_OFFER_RESEARCH_DIAGNOSTIC',selected_offers=len(selected),pending=pending,voids=voids,rejected=dict(rejected),cohorts=results,
        primary_release_eligible=False,limitation='Descriptive research only. Distinct thresholds and players within games are correlated. No tuning or release authorization from this audit.')


def main():
    import argparse
    p=argparse.ArgumentParser();p.add_argument('archive',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
    raw=a.archive.read_bytes();report=audit(json.loads(raw));report['input_sha256']=hashlib.sha256(raw).hexdigest()
    a.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))

if __name__=='__main__':main()
