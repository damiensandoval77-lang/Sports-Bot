"""Offline threshold/history-count diagnostic of the exact frozen artifact."""
import argparse,json
from pathlib import Path
import numpy as np
from .short_history_candidate import load,prepare,FEATURES
from .short_history_direct_capture import load_bundle

def evaluate(data_dir):
    pack,manifest=load_bundle();rows,_=load(data_dir);samples,_=prepare(rows)
    test=[r for r in samples if r['season']=='2025-26'];features=np.array([[r['features'][k] for k in FEATURES] for r in test]);counts=np.array([r['features']['history_count'] for r in test]);actual=np.array([r['actual'] for r in test]);result={}
    for index,(stat,lines) in enumerate(pack['threshold_grid'].items()):
        y=actual.sum(axis=1) if index==3 else actual[:,index];by_line={}
        previous=None
        for line in lines:
            x=np.column_stack([features,np.repeat(line,len(features))]);p=pack['maps'][stat].predict(pack['models'][stat].predict_proba(x)[:,1]);obs=(y>line).astype(float)
            if previous is not None and np.any(p>previous+1e-10):raise ValueError('NONMONOTONE_FROZEN_MODEL')
            previous=p
            def metrics(mask):
                probs=p[mask];outcomes=obs[mask];ece=0.
                for lo in np.arange(0,1,.1):
                    ix=(probs>=lo)&(probs<(lo+.1) if lo<.9 else probs<=1)
                    if ix.any():ece+=ix.mean()*abs(probs[ix].mean()-outcomes[ix].mean())
                return dict(player_games=int(mask.sum()),brier=float(np.mean((probs-outcomes)**2)),mean_prediction=float(probs.mean()),actual_over_rate=float(outcomes.mean()),ece=float(ece))
            by_line[str(line)]=dict(all=metrics(np.ones(len(test),dtype=bool)),by_prior_count={str(n):metrics(counts==n) for n in range(3,8)})
        result[stat]=by_line
    return dict(artifact_sha256=manifest['artifact_sha256'],previously_inspected_season='2025-26',primary_release_eligible=False,threshold_and_history_count_diagnostics=result)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--data-dir',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.write_text(json.dumps(evaluate(a.data_dir),indent=2)+'\n')
