"""Offline deterministic builder for the reviewed research candidate, not a trainer job."""
import argparse,json,hashlib
from pathlib import Path
import joblib,numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.isotonic import IsotonicRegression
from .short_history_candidate import load,prepare,FEATURES
from .short_history_direct_capture import MODEL,SPEC,code_hashes,versions,BUNDLE

def build(data_dir,output):
    spec=json.loads(SPEC.read_text());rows,sources=load(data_dir);samples,_=prepare(rows)
    train=[r for r in samples if r['season'] in spec['training']];cal=[r for r in samples if r['season']==spec['calibration']]
    if min(len(train),len(cal))<1000:raise ValueError('INSUFFICIENT_TRAINING_DATA')
    X=lambda rs:np.array([[r['features'][k] for k in FEATURES] for r in rs])
    Y=lambda rs:np.array([r['actual'] for r in rs]);base=lambda rs:np.array([r['baseline'] for r in rs])
    residuals=Y(train)-base(train);models={};maps={};baseline_maps={}
    for i,(stat,lines) in enumerate(spec['threshold_grid'].items()):
        expand=lambda rs:np.column_stack([np.repeat(X(rs),len(lines),axis=0),np.tile(lines,len(rs))])
        def actual(rs):
            y=Y(rs);v=y.sum(axis=1) if i==3 else y[:,i];return (v[:,None]>np.array(lines)).astype(float).ravel()
        model=HistGradientBoostingClassifier(**spec['classifier'],monotonic_cst=[0]*len(FEATURES)+[-1],random_state=20261114)
        model.fit(expand(train),actual(train));models[stat]=model
        maps[stat]=IsotonicRegression(out_of_bounds='clip',y_min=0,y_max=1).fit(model.predict_proba(expand(cal))[:,1],actual(cal))
        bp=[]
        for b in base(cal):
            draws=np.maximum(0,np.floor(b+residuals+.5));v=draws.sum(axis=1) if i==3 else draws[:,i];bp.extend([(v>line).mean() for line in lines])
        baseline_maps[stat]=IsotonicRegression(out_of_bounds='clip',y_min=0,y_max=1).fit(bp,actual(cal))
    pack=dict(model=MODEL,features=FEATURES,models=models,maps=maps,baseline_residuals=residuals,baseline_maps=baseline_maps,threshold_grid=spec['threshold_grid'])
    output.mkdir(parents=True,exist_ok=True);path=output/'model.joblib';joblib.dump(pack,path,compress=3)
    manifest=dict(model=MODEL,artifact_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),spec_sha256=hashlib.sha256(SPEC.read_bytes()).hexdigest(),code_sha256=code_hashes(),builder_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),versions=versions(),source_hashes=sources,primary_release_eligible=False,diagnostic_previously_inspected=True)
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(manifest))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--data-dir',type=Path,required=True);p.add_argument('--output-dir',type=Path,default=BUNDLE);a=p.parse_args();build(a.data_dir,a.output_dir)
