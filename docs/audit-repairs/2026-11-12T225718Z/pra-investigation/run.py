from iphone_bot import short_history_candidate as c
from pathlib import Path
import json, numpy as np, hashlib
from sklearn.ensemble import HistGradientBoostingRegressor
from datetime import datetime, timezone
out=Path('/tmp/pra-coherent-research')
spec=json.loads((out/'predeclared.json').read_text())
rows,sources=c.load(Path('/tmp/short-history-data')); samples,excluded=c.prepare(rows)
train=[r for r in samples if r['season'] in c.TRAIN]
def X(rs):return np.array([[r['features'][k] for k in c.FEATURES] for r in rs])
models=[]
for i,s in enumerate(c.STATS):
 m=HistGradientBoostingRegressor(loss='squared_error',max_iter=100,max_leaf_nodes=7,max_depth=3,min_samples_leaf=100,learning_rate=.05,l2_regularization=10,early_stopping=False,random_state=20261112)
 m.fit(X(train),np.array([r['actual'][i] for r in train]));models.append(m)
result={}
for season in (c.VALIDATE,c.DIAGNOSTIC):
 rs=[r for r in samples if r['season']==season]
 pred=np.maximum(0,np.column_stack([m.predict(X(rs)) for m in models])).sum(axis=1)
 actual=np.array([sum(r['actual']) for r in rs]);base=np.array([sum(r['baseline']) for r in rs])
 err=abs(pred-actual);be=abs(base-actual);delta=err-be
 days=np.array([r['date'] for r in rs]); dates=sorted(set(days)); totals=np.array([delta[days==d].sum() for d in dates]);counts=np.array([(days==d).sum() for d in dates])
 rng=np.random.default_rng(20261112);ix=rng.integers(0,len(dates),size=(10000,len(dates)));draws=totals[ix].sum(axis=1)/counts[ix].sum(axis=1)
 result[season]={'n':len(rs),'dates':len(dates),'mae':float(err.mean()),'baseline_mae':float(be.mean()),'mae_delta':float(delta.mean()),'ci95':np.quantile(draws,[.025,.975]).tolist(),'family2_ci97_5':np.quantile(draws,[.0125,.9875]).tolist(),'family8_ci99_375':np.quantile(draws,[.003125,.996875]).tolist(),'by_count':{str(n):{'n':sum(r['features']['history_count']==n for r in rs),'mae_delta':float(delta[[r['features']['history_count']==n for r in rs]].mean())} for n in range(3,8)}}
report={'specification':spec,'specification_sha256':hashlib.sha256((out/'predeclared.json').read_bytes()).hexdigest(),'generated_at':datetime.now(timezone.utc).isoformat(),'source_hashes':sources,'train_rows':len(train),'results':result,'passes_conservative_gate':result[c.VALIDATE]['family8_ci99_375'][1]<0 and result[c.DIAGNOSTIC]['mae_delta']<=0,'production_modified':False,'primary_model_eligible':False,'prospectively_validated':False}
(out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
