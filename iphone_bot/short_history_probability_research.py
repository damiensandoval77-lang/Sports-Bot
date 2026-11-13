"""Failed-gate probability candidate, prospective RESEARCH ONLY.

No UI consumer, primary picks, grades, probabilities or history are overwritten.
The fixed diagnostic failed; receipts are data for future research, not validation.
"""
from copy import deepcopy
from datetime import datetime,timezone,timedelta
from pathlib import Path
import hashlib,json,math
from io import BytesIO
import numpy as np
from .short_history_candidate import load,prepare,download,FEATURES,features
from .live_lagged_matchup_sidecar import stamp,current_games
from .expanded_matchup_research import build_team_games
from .provisional_short_history import estimates as eligibility

MODEL='SHORT_HISTORY_DISTRIBUTION_V1_FAILED_GATE_RESEARCH'
STATUS='UNVALIDATED_SHORT_HISTORY_PROBABILITY_RESEARCH'
ROOT=Path(__file__).resolve().parents[1]
SPEC=Path(__file__).with_name('short_history_probability_spec.json')
NOTICE='Failed retrospective improvement gate. Unvalidated research probabilities, not primary picks, calibrated betting probabilities or official grades.'

def probability(prediction,residuals,line,index):
    p=np.asarray(prediction,dtype=float);r=np.asarray(residuals,dtype=float)
    if p.shape!=(3,) or r.ndim!=2 or r.shape[1]!=3 or len(r)<1000 or not np.isfinite(p).all() or not np.isfinite(r).all():
        raise ValueError('INVALID_DISTRIBUTION')
    if not math.isfinite(line) or line<0 or index not in range(4):raise ValueError('INVALID_MARKET')
    draws=np.maximum(0,np.floor(p+r+.5))
    v=draws.sum(axis=1) if index==3 else draws[:,index]
    return np.array([(v>line).mean(),(v<line).mean(),(v==line).mean()])

def train(directory):
    from sklearn.ensemble import HistGradientBoostingRegressor
    from sklearn.isotonic import IsotonicRegression
    download(directory);rows,sources=load(directory);samples,_=prepare(rows)
    split={s:[r for r in samples if r['season']==s] for s in ('2022-23','2023-24','2024-25')}
    X=lambda rs:np.array([[r['features'][k] for k in FEATURES] for r in rs])
    y=lambda rs:np.array([r['actual'] for r in rs])
    if min(map(len,split.values()))<1000:raise ValueError('INSUFFICIENT_TRAINING_ROWS')
    models=[]
    for i in range(3):
        m=HistGradientBoostingRegressor(loss='absolute_error',max_iter=100,max_leaf_nodes=7,max_depth=3,min_samples_leaf=100,learning_rate=.05,l2_regularization=10,early_stopping=False,random_state=20261112)
        m.fit(X(split['2022-23']),y(split['2022-23'])[:,i]);models.append(m)
    predict=lambda rs:np.maximum(0,np.column_stack([m.predict(X(rs)) for m in models]))
    residuals=y(split['2023-24'])-predict(split['2023-24'])
    baseline=lambda rs:np.array([r['baseline'] for r in rs])
    baseline_residuals=y(split['2023-24'])-baseline(split['2023-24'])
    cal=split['2024-25'];cp=predict(cal);actual=y(cal);maps={};baseline_maps={}
    spec=json.loads(SPEC.read_text())
    for i,(stat,lines) in enumerate(spec['threshold_grid'].items()):
        p=np.array([[probability(v,residuals,line,i)[0] for line in lines] for v in cp])
        a=actual.sum(axis=1) if i==3 else actual[:,i]
        observed=(a[:,None]>np.array(lines)).astype(float)
        maps[stat]=IsotonicRegression(out_of_bounds='clip',y_min=0,y_max=1).fit(p.ravel(),observed.ravel())
        bp=np.array([[probability(v,baseline_residuals,line,i)[0] for line in lines] for v in baseline(cal)])
        baseline_maps[stat]=IsotonicRegression(out_of_bounds='clip',y_min=0,y_max=1).fit(bp.ravel(),observed.ravel())
    import joblib,sklearn
    payload=BytesIO();joblib.dump({'models':models,'residuals':residuals,'maps':maps,'baseline_residuals':baseline_residuals,'baseline_maps':baseline_maps},payload)
    return {'models':models,'residuals':residuals,'maps':maps,
            'baseline_residuals':baseline_residuals,'baseline_maps':baseline_maps,
            'artifact_sha256':hashlib.sha256(payload.getvalue()).hexdigest(),
            'library_versions':{'sklearn':sklearn.__version__,'numpy':np.__version__,'joblib':joblib.__version__},
            'spec_sha256':hashlib.sha256(SPEC.read_bytes()).hexdigest(),'source_hashes':sources}

def capture(records,feed,pack,*,primary,injuries,news,free_watch,now=None):
    now=stamp(now or datetime.now(timezone.utc))
    allowed=eligibility(records,feed,primary=primary,injuries=injuries,news=news,free_watch=free_watch,now=now)
    result={'status':STATUS,'model':MODEL,'generated_at':now.isoformat(),'records':[],
            'notice':NOTICE,'primary_model_eligible':False,'official_grade_eligible':False,'calibrated':False,
            'historical_improvement_gate_passed':False,'excluded':allowed.get('excluded',{})}
    if allowed.get('blocker'):result['blocker']=allowed['blocker'];return result
    context=build_team_games(records,season='2026-27')
    for row in allowed['estimates']:
        if now-stamp(row['market_updated'])>timedelta(minutes=30):continue
        prior=[r for r in records if str(r['id'])==row['player_id']]
        day=stamp(row['start']).astimezone(__import__('zoneinfo').ZoneInfo('America/New_York')).date().isoformat()
        f,reason=features(prior,row['team'],row['opponent'],day,context)
        if reason:continue
        x=np.array([[f[k] for k in FEATURES]])
        pred=np.maximum(0,np.array([m.predict(x)[0] for m in pack['models']]))
        stat=row['stat'];ix=('PTS','REB','AST','PRA').index(stat)
        raw=probability(pred,pack['residuals'],row['line'],ix)
        baseline_components=np.array([f[s+'_mean'] for s in ('PTS','REB','AST')])
        baseline_raw=probability(baseline_components,pack['baseline_residuals'],row['line'],ix)
        baseline_mapped=float(pack['baseline_maps'][stat].predict([baseline_raw[0]])[0]) if row['line']%1==.5 else None
        # Half-integer calibration is never silently extended to integer pushes.
        mapped=float(pack['maps'][stat].predict([raw[0]])[0]) if row['line']%1==.5 else None
        identity=[MODEL,pack['spec_sha256'],pack['artifact_sha256'],row['player_id'],row['team'],row['game'],row['start'],stat,row['line']]
        key=hashlib.sha256(json.dumps(identity,separators=(',',':')).encode()).hexdigest()
        result['records'].append({**row,'candidate_model':MODEL,'receipt_key':key,
            'spec_sha256':pack['spec_sha256'],'source_hashes':pack['source_hashes'],
            'artifact_sha256':pack['artifact_sha256'],'library_versions':pack['library_versions'],
            'descriptive_baseline_projection':row['projection'],
            'candidate_component_projections':dict(zip(('PTS','REB','AST'),pred.tolist())),
            'candidate_projection':float(pred.sum() if ix==3 else pred[ix]),
            'projection':float(pred.sum() if ix==3 else pred[ix]),'method':MODEL,'trained_model':True,
            'cohort':'SHORT_HISTORY_FAILED_GATE_PROBABILITY_RESEARCH',
            'baseline_model':'PRIOR_MEAN_EMPIRICAL_RESIDUAL_2023_ISOTONIC_2024',
            'baseline_probability_over':float(baseline_raw[0]),'baseline_probability_under':float(baseline_raw[1]),
            'baseline_probability_push':float(baseline_raw[2]),'baseline_half_integer_calibrated_map_over':baseline_mapped,
            'features':f,'research_probability_over':float(raw[0]),'research_probability_under':float(raw[1]),
            'research_probability_push':float(raw[2]),'research_half_integer_calibrated_map_over':mapped,
            'probability_mapping_note':'Retrospective isotonic map only; NOT validated betting calibration',
            'historical_improvement_gate_passed':False,'archived_at':now.isoformat(),
            'primary_model_eligible':False,'official_grade_eligible':False,'calibrated':False})
    return result

def merge(previous,feed,now=None):
    now=stamp(now or datetime.now(timezone.utc))
    previous=previous or {'status':STATUS,'records':[],'outcomes':{}}
    if previous.get('status')!=STATUS:raise ValueError('INVALID_PRIOR_ARCHIVE')
    output=deepcopy(previous);keys={r['receipt_key'] for r in output['records']}
    if len(keys)!=len(output['records']):raise ValueError('DUPLICATE_PRIOR_KEYS')
    for row in feed.get('records',[]):
        tip=stamp(row['start']);captured=stamp(row['captured_at']);archived=stamp(row['archived_at'])
        if not stamp(row['market_updated'])<=captured<=archived<=now<tip:raise ValueError('NOT_PROSPECTIVE')
        if now-captured>timedelta(minutes=30) or now-stamp(row['market_updated'])>timedelta(minutes=30):raise ValueError('STALE_CAPTURE_OR_QUOTE')
        p=[row[k] for k in ('research_probability_over','research_probability_under','research_probability_push')]
        if any(type(v) not in (int,float) or not math.isfinite(v) or not 0<=v<=1 for v in p) or abs(sum(p)-1)>1e-9:raise ValueError('INVALID_PROBABILITIES')
        if row.get('candidate_model')!=MODEL or row.get('primary_model_eligible') is not False or row.get('official_grade_eligible') is not False or row.get('calibrated') is not False or row.get('historical_improvement_gate_passed') is not False:raise ValueError('INVALID_RESEARCH_LABEL')
        if row['receipt_key'] not in keys:output['records'].append(deepcopy(row));keys.add(row['receipt_key'])
    output.update(updated_at=now.isoformat(),count=len(output['records']),notice=NOTICE,primary_model_eligible=False,official_grade_eligible=False,calibrated=False)
    return output

def settle(archive,final_rows,now=None):
    """Final values live separately from immutable prediction receipts."""
    now=stamp(now or datetime.now(timezone.utc));out=deepcopy(archive);out.setdefault('outcomes',{})
    candidates={}
    for row in final_rows:
        if row.get('grade_source')!='NBA_CDN_FINAL' or not row.get('source_game_id'):continue
        v=row.get('actual')
        if type(v) not in (int,float) or not math.isfinite(v) or v<0:continue
        key=(str(row.get('player_id')),row.get('team'),row.get('game'),row.get('start'),row.get('stat'))
        candidates.setdefault(key,set()).add((float(v),row['source_game_id']))
    for row in out['records']:
        key=(str(row['player_id']),row['team'],row['game'],row['start'],row['stat'])
        values=candidates.get(key,set())
        if len(values)!=1 or now<=stamp(row['start']):continue
        actual,game_id=next(iter(values));receipt=row['receipt_key']
        value={'actual':actual,'source':'NBA_CDN_FINAL','source_game_id':game_id,
               'observed_at':now.isoformat(),'result':'OVER' if actual>row['line'] else 'UNDER' if actual<row['line'] else 'PUSH'}
        if receipt not in out['outcomes']:out['outcomes'][receipt]=value
        elif out['outcomes'][receipt]['actual']!=actual:raise ValueError('CONFLICTING_FINAL_ACTUAL')
    return out

def main():
    import pandas as pd,requests
    from io import BytesIO
    def read(p):return json.loads((ROOT/p).read_text())
    pack=train(ROOT/'data/research-short-history-probability')
    response=requests.get('https://huggingface.co/datasets/cbratkovics/nba-game-logs/resolve/main/game_logs/game_logs_2026-27.parquet',timeout=(12,45));response.raise_for_status()
    if len(response.content)>12_000_000:raise ValueError('SOURCE_TOO_LARGE')
    df=pd.read_parquet(BytesIO(response.content)).rename(columns={'player_id':'id','game_date':'date'})
    df['date']=pd.to_datetime(df['date'],errors='raise').dt.strftime('%Y-%m-%d')
    records,_=current_games(read('data/nba/current/current_games.json'),df.to_dict(orient='records'))
    feed=capture(records,read('docs/prizepicks_model_input.json'),pack,primary=read('docs/lagged_matchup_all_market_ledger.json'),injuries=read('docs/injury_context.json'),news=read('docs/underdog_nba_injury_alerts.json'),free_watch=read('docs/free_nba_injury_watch.json'))
    path=ROOT/'docs/short_history_probability_research.json'
    previous=json.loads(path.read_text()) if path.exists() else None
    output=settle(merge(previous,feed),read('docs/standard_quote_ai_research_archive.json')['records'])
    output['last_capture_blocker']=feed.get('blocker');output['last_capture_count']=len(feed['records'])
    path.write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps({'records':output['count'],'new_feed':len(feed['records']),'outcomes':len(output['outcomes']),'blocker':feed.get('blocker'),'primary_eligible':False}))

if __name__=='__main__':main()
