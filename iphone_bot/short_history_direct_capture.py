"""Frozen direct-exceedance candidate: distinct prospective RESEARCH archive only.

No primary consumer or probability release. Half-lines strictly inside the
reviewed grid; real observed pretip features and injury evidence only.
"""
from copy import deepcopy
from datetime import datetime,timezone,timedelta
from pathlib import Path
from collections import Counter
from io import BytesIO
import hashlib,json,math,sys
import numpy as np
from .short_history_candidate import FEATURES,features
from .expanded_matchup_research import build_team_games
from .provisional_short_history import estimates as eligible
from .short_history_probability_research import capture_context,settle_pending
from .live_lagged_matchup_sidecar import stamp,current_games

ROOT=Path(__file__).resolve().parents[1]
MODEL='SHORT_HISTORY_DIRECT_MONOTONE_EXCEEDANCE_V1'
STATUS='FROZEN_DIRECT_EXCEEDANCE_PROSPECTIVE_RESEARCH'
NOTICE='Exploratory direct-exceedance probabilities. Not validated betting probabilities, primary picks, or official grades.'
DEPENDENCIES=('short_history_direct_capture.py','short_history_candidate.py','expanded_matchup_research.py','provisional_short_history.py','short_history_probability_research.py','live_lagged_matchup_sidecar.py','live_multimarket_matchup.py')
SPEC=Path(__file__).with_name('short_history_direct_spec.json')
BUNDLE=ROOT/'research/short-history-direct-v1'

def digest(raw):return hashlib.sha256(raw).hexdigest()
def code_hashes():return {name:digest(Path(__file__).with_name(name).read_bytes()) for name in DEPENDENCIES}
def versions():
    import sklearn,joblib
    return dict(numpy=np.__version__,sklearn=sklearn.__version__,joblib=joblib.__version__,python='.'.join(map(str,sys.version_info[:2])))
def load_bundle(directory=BUNDLE):
    import joblib
    manifest=json.loads((directory/'manifest.json').read_text())
    if manifest['model']!=MODEL or manifest['spec_sha256']!=digest(SPEC.read_bytes()) or manifest['code_sha256']!=code_hashes() or manifest['versions']!=versions():raise ValueError('FROZEN_BUNDLE_PROVENANCE_MISMATCH')
    raw=(directory/'model.joblib').read_bytes()
    if digest(raw)!=manifest['artifact_sha256']:raise ValueError('FROZEN_ARTIFACT_HASH_MISMATCH')
    pack=joblib.load(BytesIO(raw))
    if pack['model']!=MODEL or tuple(pack['features'])!=FEATURES or set(pack['models'])!={'PTS','REB','AST','PRA'}:raise ValueError('INVALID_FROZEN_MODEL')
    return pack,manifest

def predict(pack,stat,line,f):
    grid=pack['threshold_grid'][stat]
    if type(line) not in (int,float) or not math.isfinite(line) or line%1!=.5 or not min(grid)<=line<=max(grid):raise ValueError('UNSUPPORTED_HALF_LINE')
    x=np.array([[f[k] for k in FEATURES]+[line]],dtype=float)
    if not np.isfinite(x).all():raise ValueError('INVALID_FEATURES')
    raw=float(pack['models'][stat].predict_proba(x)[0,1]);p=float(pack['maps'][stat].predict([raw])[0])
    ix=('PTS','REB','AST','PRA').index(stat)
    base=np.array([f[s+'_mean'] for s in ('PTS','REB','AST')]);draws=np.maximum(0,np.floor(base+pack['baseline_residuals']+.5))
    values=draws.sum(axis=1) if ix==3 else draws[:,ix]
    bp=float(pack['baseline_maps'][stat].predict([(values>line).mean()])[0])
    if any(not math.isfinite(v) or not 0<=v<=1 for v in (raw,p,bp)):raise ValueError('INVALID_PROBABILITY')
    return raw,p,bp

def capture(records,feed,pack,manifest,*,primary,injuries,news,free_watch,now=None):
    now=stamp(now or datetime.now(timezone.utc));base=eligible(records,feed,primary=primary,injuries=injuries,news=news,free_watch=free_watch,now=now)
    out=dict(status=STATUS,model=MODEL,generated_at=now.isoformat(),records=[],excluded=dict(base['excluded']),notice=NOTICE,primary_model_eligible=False,official_grade_eligible=False,calibrated=False)
    if base.get('blocker'):out['blocker']=base['blocker'];return out
    context=build_team_games(records,season='2026-27')
    for row in base['estimates']:
        stat=row['stat'];line=row['line']
        if stat not in pack['threshold_grid'] or line%1!=.5 or not min(pack['threshold_grid'][stat])<=line<=max(pack['threshold_grid'][stat]):
            out['excluded']['UNSUPPORTED_HALF_LINE']=out['excluded'].get('UNSUPPORTED_HALF_LINE',0)+1;continue
        if now-stamp(row['market_updated'])>timedelta(minutes=30):continue
        observed=capture_context(row,injuries,news,free_watch,feed,records,now)
        if not observed['official_report']['verified_at_capture']:continue
        day=stamp(row['start']).astimezone(__import__('zoneinfo').ZoneInfo('America/New_York')).date().isoformat()
        prior=[r for r in records if str(r['id'])==row['player_id']]
        f,reason=features(prior,row['team'],row['opponent'],day,context)
        if reason:continue
        raw,p,bp=predict(pack,stat,line,f)
        identity=[MODEL,manifest['spec_sha256'],manifest['artifact_sha256'],row['player_id'],row['team'],row['game'],row['start'],stat,line]
        receipt=digest(json.dumps(identity,separators=(',',':')).encode())
        out['records'].append({**row,'candidate_model':MODEL,'receipt_key':receipt,'method':MODEL,'cohort':'DIRECT_EXCEEDANCE_RESEARCH_ONLY','features':f,
            'projection':None,'descriptive_baseline_projection':row['projection'],'trained_model':True,'calibrated':False,'historical_improvement_gate_passed':True,'diagnostic_previously_inspected':True,
            'spec_sha256':manifest['spec_sha256'],'artifact_sha256':manifest['artifact_sha256'],'code_sha256':manifest['code_sha256'],'library_versions':manifest['versions'],'source_hashes':manifest['source_hashes'],
            'research_probability_over':p,'research_probability_under':1-p,'research_probability_push':0.,'research_half_integer_calibrated_map_over':p,'raw_direct_exceedance_probability':raw,
            'baseline_probability_over':bp,'baseline_probability_under':1-bp,'baseline_probability_push':0.,'baseline_half_integer_calibrated_map_over':bp,
            'baseline_model':'PRIOR_MEAN_TRAIN2022_2023_RESIDUAL_CAL2024','observed_context':observed,'archived_at':now.isoformat(),'notice':NOTICE})
    return out

def merge(previous,feed,now=None):
    now=stamp(now or datetime.now(timezone.utc));previous=previous or dict(status=STATUS,records=[],outcomes={})
    if previous.get('status')!=STATUS:raise ValueError('WRONG_ARCHIVE')
    out=deepcopy(previous);seen={r['receipt_key']:r for r in out['records']}
    if len(seen)!=len(out['records']):raise ValueError('DUPLICATE_ARCHIVE_KEYS')
    for r in feed['records']:
        if not stamp(r['market_updated'])<=stamp(r['captured_at'])<=stamp(r['archived_at'])<=now<stamp(r['start']):raise ValueError('NOT_PROSPECTIVE')
        if now-stamp(r['captured_at'])>timedelta(minutes=30) or now-stamp(r['market_updated'])>timedelta(minutes=30):raise ValueError('STALE_RECEIPT')
        if r.get('candidate_model')!=MODEL or any(r.get(k) is not False for k in ('primary_model_eligible','official_grade_eligible','calibrated')):raise ValueError('INVALID_RESEARCH_LABEL')
        if r['line']%1!=.5 or r['research_probability_push']!=0:raise ValueError('UNSUPPORTED_HALF_LINE')
        for prefix in ('research','baseline'):
            ps=[r[prefix+'_probability_'+s] for s in ('over','under','push')]
            if any(type(v) not in (int,float) or not math.isfinite(v) or not 0<=v<=1 for v in ps) or abs(sum(ps)-1)>1e-9:raise ValueError('INVALID_PROBABILITY')
        old=seen.get(r['receipt_key'])
        if old:
            if old['captured_at']==r['captured_at'] and old!=r:raise ValueError('CONFLICTING_EARLIEST_RECEIPT')
            continue
        out['records'].append(deepcopy(r));seen[r['receipt_key']]=r
    out.update(count=len(out['records']),notice=NOTICE,primary_model_eligible=False,official_grade_eligible=False,calibrated=False)
    if out['records']!=previous['records']:out['updated_at']=now.isoformat()
    return out

def main():
    import argparse,pandas as pd,requests
    parser=argparse.ArgumentParser();parser.add_argument('--settle-only',action='store_true');args=parser.parse_args()
    path=ROOT/'docs/short_history_direct_probability_research.json'
    previous=json.loads(path.read_text()) if path.exists() else dict(status=STATUS,records=[],outcomes={})
    if args.settle_only:output=settle_pending(previous)
    else:
        pack,manifest=load_bundle()
        read=lambda p:json.loads((ROOT/p).read_text())
        response=requests.get('https://huggingface.co/datasets/cbratkovics/nba-game-logs/resolve/main/game_logs/game_logs_2026-27.parquet',timeout=(12,45));response.raise_for_status()
        if len(response.content)>12_000_000:raise ValueError('SOURCE_TOO_LARGE')
        df=pd.read_parquet(BytesIO(response.content)).rename(columns={'player_id':'id','game_date':'date'});df['date']=pd.to_datetime(df['date'],errors='raise').dt.strftime('%Y-%m-%d')
        records,_=current_games(read('data/nba/current/current_games.json'),df.to_dict(orient='records'))
        feed=capture(records,read('docs/prizepicks_model_input.json'),pack,manifest,primary=read('docs/lagged_matchup_all_market_ledger.json'),injuries=read('docs/injury_context.json'),news=read('docs/underdog_nba_injury_alerts.json'),free_watch=read('docs/free_nba_injury_watch.json'))
        output=settle_pending(merge(previous,feed));output['last_capture_blocker']=feed.get('blocker');output['last_capture_count']=len(feed['records'])
    path.write_text(json.dumps(output,indent=2)+'\n');print(json.dumps(dict(records=len(output['records']),outcomes=len(output['outcomes']),primary_eligible=False)))

if __name__=='__main__':main()
