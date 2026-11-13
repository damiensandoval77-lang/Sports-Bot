"""Separate 3–7-game cohort research model, never a primary-model override.

Fixed candidate specification: train 2022-23/2023-24; evaluate 2024-25 and
previously inspected 2025-26 diagnostic. No hyperparameter selection on either.
PTS/REB/AST estimated independently; PRA is their exact sum. No probabilities.
"""
import argparse
from collections import defaultdict, Counter
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
from statistics import mean
import joblib
import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor
from .expanded_matchup_research import build_team_games

TRAIN=('2022-23','2023-24')
VALIDATE='2024-25'
DIAGNOSTIC='2025-26'
STATS=('PTS','REB','AST')
FEATURES=('history_count','minutes_mean','minutes_last3','minutes_last',
          'PTS_mean','PTS_last3','PTS_per_min','REB_mean','REB_last3','REB_per_min',
          'AST_mean','AST_last3','AST_per_min','FGA_per_min','FTA_per_min','TOV_per_min',
          'own_possessions','opponent_possessions','opponent_points_allowed_per100')
MODEL='SEPARATE_SHORT_HISTORY_HGB_ABSOLUTE_V1'
SOURCE_SHA256={
'2022-23':'f398a553e4c92216fc2dfc4d25622470c8a62bd8254811fccb3496d4cafc553f',
'2023-24':'5fff5e5a57dd73ea36b6610c61fb1cb182156ace89e5c8e1c7024427bb9eefc4',
'2024-25':'a4cc538112a7c4c7a4f42476022726159907ed71fc13cdd9a070c9950c2b50d6',
'2025-26':'2119a573915ebcd548a290e9d2d9c509921adb85b7e01e570908f423d60cb3a3'}


def features(prior, team, opponent, day, context):
    prior=sorted((r for r in prior if r['team']==team and r['date']<day),key=lambda r:r['date'])
    if not 3<=len(prior)<=7:return None,'OUTSIDE_3_TO_7_GAME_COHORT'
    if len({r['date'] for r in prior})!=len(prior):return None,'DUPLICATE_PRIOR_DATE'
    required=(*STATS,'MIN','FGA','FTA','TOV')
    if any(type(r.get(k)) not in (int,float) or not math.isfinite(r[k]) or r[k]<0 for r in prior for k in required):
        return None,'INVALID_PRIOR_VALUE'
    if any(not 1<=r['MIN']<=60 for r in prior):return None,'INVALID_PRIOR_MINUTES'
    own=[x for x in context.get(team,[]) if x[0]<day][-5:]
    opp=[x for x in context.get(opponent,[]) if x[0]<day][-5:]
    if min(len(own),len(opp))<3:return None,'INSUFFICIENT_PRIOR_RECIPROCAL_TEAM_CONTEXT'
    f={'history_count':len(prior),'minutes_mean':mean(r['MIN'] for r in prior),
       'minutes_last3':mean(r['MIN'] for r in prior[-3:]),'minutes_last':prior[-1]['MIN'],
       'own_possessions':mean(x[1]['poss'] for x in own),
       'opponent_possessions':mean(x[1]['poss'] for x in opp),
       'opponent_points_allowed_per100':mean(100*x[2]['PTS']/x[2]['poss'] for x in opp)}
    for s in STATS:
        f[s+'_mean']=mean(r[s] for r in prior)
        f[s+'_last3']=mean(r[s] for r in prior[-3:])
        f[s+'_per_min']=sum(r[s] for r in prior)/sum(r['MIN'] for r in prior)
    for s in ('FGA','FTA','TOV'):f[s+'_per_min']=sum(r[s] for r in prior)/sum(r['MIN'] for r in prior)
    if not all(math.isfinite(f[k]) for k in FEATURES):return None,'NONFINITE_FEATURE'
    return f,None


def prepare(rows):
    by_season=defaultdict(list)
    for r in rows:by_season[r['season']].append(r)
    context={s:build_team_games(rs,s) for s,rs in by_season.items()}
    grouped=defaultdict(list)
    for r in rows:grouped[(r['season'],r['id'],r['team'])].append(r)
    samples=[];excluded=Counter()
    for (season,pid,team),games in grouped.items():
        days=defaultdict(list)
        for r in games:days[r['date']].append(r)
        prior=[]
        for day in sorted(days):
            if len(days[day])!=1:
                excluded['AMBIGUOUS_PLAYER_DATE']+=1;continue
            row=days[day][0]
            f,reason=features(prior,team,row['opponent'],day,context[season])
            if f:
                samples.append({'season':season,'date':day,'player_id':pid,'team':team,
                                'features':f,'actual':[row[s] for s in STATS],
                                'baseline':[f[s+'_mean'] for s in STATS]})
            else:excluded[reason]+=1
            prior.append(row)
    return samples,dict(excluded)


def fit(samples):
    train=[r for r in samples if r['season'] in TRAIN]
    val=[r for r in samples if r['season']==VALIDATE]
    diag=[r for r in samples if r['season']==DIAGNOSTIC]
    if len(train)<3000 or min(len(val),len(diag))<1000:raise ValueError('Insufficient real season-separated cohort samples')
    def X(rows):return np.array([[r['features'][k] for k in FEATURES] for r in rows])
    y=np.array([r['actual'] for r in train]);models={}
    for i,s in enumerate(STATS):
        m=HistGradientBoostingRegressor(loss='absolute_error',max_iter=100,max_leaf_nodes=7,
            max_depth=3,min_samples_leaf=100,learning_rate=.05,l2_regularization=10,
            early_stopping=False,random_state=20261112)
        m.fit(X(train),y[:,i]);models[s]=m
    def evaluate(rows):
        predicted=np.maximum(0,np.column_stack([models[s].predict(X(rows)) for s in STATS]))
        actual=np.array([r['actual'] for r in rows]);baseline=np.array([r['baseline'] for r in rows])
        predicted=np.column_stack([predicted,predicted.sum(axis=1)])
        actual=np.column_stack([actual,actual.sum(axis=1)])
        baseline=np.column_stack([baseline,baseline.sum(axis=1)])
        result={}
        dates=sorted({r['date'] for r in rows})
        # Date-clustered bootstrap, not pseudo-independent player-game errors.
        for i,s in enumerate((*STATS,'PRA')):
            error=np.abs(predicted[:,i]-actual[:,i]);base_error=np.abs(baseline[:,i]-actual[:,i])
            delta=error-base_error
            totals=np.array([delta[[r['date']==d for r in rows]].sum() for d in dates])
            counts=np.array([sum(r['date']==d for r in rows) for d in dates])
            rng=np.random.default_rng(20261112)
            ix=rng.integers(0,len(dates),size=(1000,len(dates)))
            draws=totals[ix].sum(axis=1)/counts[ix].sum(axis=1)
            result[s]={'n':len(rows),'dates':len(dates),'model_mae':float(error.mean()),
                'baseline_mae':float(base_error.mean()),'mae_difference':float(delta.mean()),
                'date_clustered_difference_ci95':[float(x) for x in np.quantile(draws,[.025,.975])],
                'by_prior_count':{str(n):{'n':sum(r['features']['history_count']==n for r in rows),
                   'model_mae':float(error[[r['features']['history_count']==n for r in rows]].mean()),
                   'baseline_mae':float(base_error[[r['features']['history_count']==n for r in rows]].mean())}
                   for n in range(3,8)}}
        return result
    validation=evaluate(val);diagnostic=evaluate(diag)
    accepted={s:(validation[s]['date_clustered_difference_ci95'][1]<0 and
                 diagnostic[s]['mae_difference']<=0) for s in (*STATS,'PRA')}
    report={'status':'SHORT_HISTORY_RETROSPECTIVE_VALIDATION','model':MODEL,
      'training_seasons':TRAIN,'validation_season':VALIDATE,'previously_seen_diagnostic_season':DIAGNOSTIC,
      'training_rows':len(train),'validation':validation,'diagnostic':diagnostic,
      'library_versions':{'sklearn':__import__('sklearn').__version__,'numpy':np.__version__},
      'accepted_by_predeclared_gate':accepted,'calibrated':False,'probabilities':None,
      'primary_model_eligible':False,'production_modified':False,
      'gate':'Validation date-clustered upper95% MAE delta<0 and diagnostic mean MAE delta<=0; no tuning after results.',
      'limitations':['Retrospective accuracy is not prospective reliability or betting win rate.',
        '2025-26 has previously been inspected by other project experiments; not an untouched confirmation set.',
        'No sportsbook quotes, injuries or individual defender assignments used in historical model fitting.',
        'Separate 3–7 prior same-team game cohort; never changes primary eight-game eligibility.']}
    pack={'model':MODEL,'models':models,'features':FEATURES,'training_seasons':TRAIN,
          'validation_season':VALIDATE,'accepted_markets':accepted,'research_only':True,
          'calibrated':False,'primary_model_eligible':False}
    return pack,report


def load(directory):
    import pandas as pd
    rows=[];sources=[]
    for season in (*TRAIN,VALIDATE,DIAGNOSTIC):
        path=directory/(season+'.parquet');raw=path.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=SOURCE_SHA256[season]:raise ValueError('Historical source changed; require new review before retraining')
        df=pd.read_parquet(path)
        sources.append({'season':season,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'rows':len(df)})
        if len(df)<15000:raise ValueError('Unexpectedly small historical source')
        seen=set()
        for r in df.to_dict(orient='records'):
            key=(str(r['player_id']),str(r['game_id']))
            if key in seen:raise ValueError('Duplicate historical player game')
            seen.add(key)
            vals={k:float(r[k.lower() if k!='MIN' else 'minutes']) for k in (*STATS,'MIN','FGA','FTA','TOV','OREB')}
            if any(not math.isfinite(x) or x<0 for x in vals.values()) or not 1<=vals['MIN']<=60:continue
            rows.append({**vals,'id':str(r['player_id']),'game_id':str(r['game_id']),
                'team':r['team'],'opponent':r['opponent'],'date':str(r['game_date'])[:10],'season':season})
    return rows,sources


def download(directory):
    import urllib.request
    directory.mkdir(parents=True,exist_ok=True)
    for season in (*TRAIN,VALIDATE,DIAGNOSTIC):
        target=directory/(season+'.parquet')
        if target.exists():continue
        url='https://huggingface.co/datasets/Sangameshsb/nba-game-logs/resolve/main/game_logs/game_logs_{}.parquet'.format(season)
        payload=urllib.request.urlopen(url,timeout=90).read()
        if not 100000<=len(payload)<=12000000:raise ValueError('Unexpected archive size')
        target.write_bytes(payload)

def report_digest(report):
    content={k:v for k,v in report.items() if k!='model_sha256'}
    return hashlib.sha256(json.dumps(content,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def save_artifacts(pack,report,directory):
    directory.mkdir(parents=True,exist_ok=True)
    pack={**pack,'validation_report_sha256':report_digest(report)}
    model_path=directory/'short_history_candidate.joblib'
    joblib.dump(pack,model_path)
    report={**report,'model_sha256':hashlib.sha256(model_path.read_bytes()).hexdigest()}
    (directory/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    return report

def main():
    p=argparse.ArgumentParser();p.add_argument('--data-dir',type=Path,required=True)
    p.add_argument('--output-dir',type=Path,required=True);p.add_argument('--download',action='store_true');args=p.parse_args()
    if args.download:download(args.data_dir)
    rows,sources=load(args.data_dir);samples,excluded=prepare(rows)
    pack,report=fit(samples);report.update(sources=sources,excluded=excluded,generated_at=datetime.now(timezone.utc).isoformat())
    report=save_artifacts(pack,report,args.output_dir)
    print(json.dumps(report),flush=True)

if __name__=='__main__':main()
