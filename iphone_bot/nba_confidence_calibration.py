"""Authorized conservative confidence correction; never rewrite frozen picks.

Fit only the declared residual model, half-integer genuine standard lines.
Apply now before each event, preserve original direction, retain raw input and
versioned mapping provenance. An after-tip call cannot create a new correction.
"""
from pathlib import Path
from copy import deepcopy
from datetime import datetime,timezone
from collections import Counter
import json,hashlib,math
ROOT=Path(__file__).resolve().parents[1]
SPEC=Path(__file__).with_name('nba_confidence_calibration_spec.json')
MODEL='NBA_POOLED_LOGIT_CONFIDENCE_V1'
STATUS='FROZEN_PRETIP_NBA_CONFIDENCE_CORRECTIONS'

def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def stamp(s):
    if not isinstance(s,str):raise ValueError('INVALID_TIMESTAMP')
    t=datetime.fromisoformat(s.replace('Z','+00:00'))
    if t.tzinfo is None:raise ValueError('NAIVE_TIMESTAMP')
    return t

def corrected_more(raw,spec):
    if type(raw) not in (int,float) or not math.isfinite(raw) or not 0<=raw<=1:raise ValueError('INVALID_RAW_PROBABILITY')
    p=max(1e-5,min(1-1e-5,raw));z=spec['intercept']+spec['slope']*math.log(p/(1-p))
    return 1/(1+math.exp(-z))

def source_key(r):return tuple(str(r[k]) for k in ('player_id','team','opponent','game','start','stat','line','captured_at'))

def build(ledger,previous=None,now=None):
    now=now or datetime.now(timezone.utc)
    if now.tzinfo is None:raise ValueError('NAIVE_NOW')
    spec=json.loads(SPEC.read_text());spec_hash=hashlib.sha256(SPEC.read_bytes()).hexdigest()
    if spec['model']!=MODEL or spec['preserve_original_direction'] is not True:raise ValueError('UNSUPPORTED_MAPPING')
    previous=previous or dict(status=STATUS,records=[])
    if previous.get('status')!=STATUS:raise ValueError('WRONG_ARCHIVE')
    out=deepcopy(previous);seen={r['receipt_key']:r for r in out['records']}
    if len(seen)!=len(out['records']):raise ValueError('DUPLICATE_ARCHIVE')
    excluded=Counter();groups={};conflicts=set()
    if ledger.get('status')!='FROZEN_NEW_AI_ALL_MARKET':raise ValueError('WRONG_SOURCE_LEDGER')
    for r in ledger['records']:
        try:
            key=source_key(r)
            if key in groups and groups[key]!=r:conflicts.add(key)
            groups[key]=r
        except (KeyError,TypeError):excluded['INVALID_IDENTITY']+=1
    for key,r in groups.items():
        try:
            if key in conflicts:raise ValueError('CONFLICTING_SOURCE')
            tip=stamp(r['start']);captured=stamp(r['captured_at']);quote=stamp(r['market_updated'])
            if not quote<=captured<=now<tip:raise ValueError('NOT_PRETIP')
            if r['start'][:10]<='2026-11-13':raise ValueError('BEFORE_VALIDATION_END')
            if r.get('pickem_tier')!='standard' or r.get('standard_line_two_sided_verified') is not True:raise ValueError('NOT_STANDARD')
            line=r['line']
            if type(line) not in (int,float) or not math.isfinite(line) or line%1!=.5:raise ValueError('UNSUPPORTED_INTEGER_OR_LINE')
            if r['stat'] not in ('PTS','REB','AST','PRA') or r.get('grade')!='PENDING':raise ValueError('NOT_PENDING_SUPPORTED_MARKET')
            if any(r.get(k) is not False for k in ('opponent_context_unavailable','single_source_history','injury_uncertainty_unresolved')) or r.get('opponent_adjustment_verified') is not True:raise ValueError('UNVERIFIED_MODEL_CONTEXT')
            c=r['estimated_hit_chance']
            if c.get('method')!=spec['base_method'] or c.get('draws')!=spec['base_draws'] or c.get('calibrated') is not False or c.get('market')!=r['stat']:raise ValueError('BASE_MODEL_MISMATCH')
            raw=[c['modeled_'+s+'_probability'] for s in ('more','less','push')]
            if any(type(p) not in (int,float) or not math.isfinite(p) or not 0<=p<=1 for p in raw) or abs(sum(raw)-1)>.0002 or raw[2]!=0:raise ValueError('INVALID_RAW_DISTRIBUTION')
            side=c['modeled_direction']
            if side not in ('More','Less'):raise ValueError('NO_ORIGINAL_DIRECTION')
            selected=raw[0] if side=='More' else raw[1]
            if abs(selected-c['modeled_selected_probability'])>.0001:raise ValueError('SOURCE_SIDE_MISMATCH')
            source_hash=digest(c);receipt=digest([MODEL,spec_hash,*key,source_hash])
            if receipt in seen:continue
            more=corrected_more(raw[0],spec);rate=more if side=='More' else 1-more
            item=dict(receipt_key=receipt,model=MODEL,calibration_spec_sha256=spec_hash,player_id=r['player_id'],player=r['player'],team=r['team'],opponent=r['opponent'],game=r['game'],start=r['start'],stat=r['stat'],line=line,
                source_captured_at=r['captured_at'],source_market_updated=r['market_updated'],applied_at=now.isoformat(),original_side=side.upper(),source_method=c['method'],source_estimate_sha256=source_hash,raw_estimated_hit_chance=deepcopy(c),original_projection=r['projection'],
                probability_more=more,probability_less=1-more,probability_push=0.,corrected_original_side_probability=rate,raw_original_side_probability=selected,
                historical_forecast_modified=False,original_direction_preserved=True,grade_modified=False,prospective_accuracy_improvement_verified=False,validation_notice=spec['validation_notice'])
            out['records'].append(item);seen[receipt]=item
        except (KeyError,ValueError,TypeError) as exc:excluded[str(exc)]+=1
    out.update(model=MODEL,count=len(out['records']),generated_at=now.isoformat(),calibration_spec_sha256=spec_hash,validation_notice=spec['validation_notice'],excluded=dict(excluded),historical_forecasts_modified=False)
    return out

def main():
    path=ROOT/'docs/nba_confidence_calibration.json';previous=json.loads(path.read_text()) if path.exists() else None
    ledger=json.loads((ROOT/'docs/lagged_matchup_all_market_ledger.json').read_text());out=build(ledger,previous);path.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(dict(count=out['count'],excluded=out['excluded'])))
if __name__=='__main__':main()
