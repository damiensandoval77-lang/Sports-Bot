"""Separate research inference for an accepted short-history market only.

Never writes primary models, frozen ledgers, grades, hit probabilities or the
existing descriptive-baseline feed. Use only the strict provisional eligibility
checks, then evaluate the separately trained candidate from original history.
"""
from collections import Counter
from datetime import datetime, timezone
import numpy as np
from .provisional_short_history import estimates as eligible
from .live_lagged_matchup_sidecar import stamp
from .live_multimarket_matchup import ET
from .short_history_candidate import MODEL,FEATURES,TRAIN,VALIDATE,features
from .expanded_matchup_research import build_team_games

STATUS='SHORT_HISTORY_TRAINED_RESEARCH_PROJECTIONS'
NOTICE=('Separate short-history trained research projections. Historically evaluated, '
        'not prospectively validated or calibrated betting probabilities. '
        'Not primary picks and excluded from official grades and hit-rate metrics.')


def estimates(records,feed,pack,report,*,primary,now=None,injuries=None,news=None,free_watch=None):
    now=stamp(now or datetime.now(timezone.utc))
    if (pack.get('model')!=MODEL or tuple(pack.get('features',()))!=FEATURES or
        tuple(pack.get('training_seasons',()))!=TRAIN or pack.get('validation_season')!=VALIDATE or
        pack.get('research_only') is not True or pack.get('calibrated') is not False or
        pack.get('primary_model_eligible') is not False or report.get('model')!=MODEL or
        report.get('status')!='SHORT_HISTORY_RETROSPECTIVE_VALIDATION'):
        raise ValueError('Unverified separate model artifact')
    allowed=set()
    for s in ('PTS','REB','AST','PRA'):
        v=report['validation'][s];d=report['diagnostic'][s]
        if (v['n']>=1000 and v['dates']>=30 and d['n']>=1000 and
            v['date_clustered_difference_ci95'][1]<0 and d['mae_difference']<=0 and
            pack['accepted_markets'].get(s) is True):allowed.add(s)
    # Existing rigorous current-line/identity/injury/duplicate/date guards do
    # eligibility only. Their descriptive projection is NEVER promoted.
    base=eligible(records,feed,primary=primary,now=now,injuries=injuries,news=news,free_watch=free_watch)
    output=[];excluded=Counter(base['excluded'])
    context=build_team_games([r for r in records if not r.get('history_source_confidence')],season='2026-27')
    for row in base['estimates']:
        stat=row['stat']
        if stat not in allowed:
            excluded['MARKET_FAILED_PREDECLARED_VALIDATION_GATE']+=1;continue
        day=stamp(row['start']).astimezone(ET).date().isoformat()
        prior=[r for r in records if str(r.get('id'))==row['player_id'] and
               not r.get('history_source_confidence')]
        f,reason=features(prior,row['team'],row['opponent'],day,context)
        if reason:excluded[reason]+=1;continue
        x=np.array([[f[k] for k in FEATURES]],dtype=float)
        raw_components={s:float(pack['models'][s].predict(x)[0]) for s in ('PTS','REB','AST')}
        if not all(np.isfinite(v) for v in raw_components.values()):
            excluded['INVALID_MODEL_OUTPUT']+=1;continue
        components={s:max(0.,v) for s,v in raw_components.items()}
        projection=sum(components.values()) if stat=='PRA' else components[stat]
        if not np.isfinite(projection) or not 0<=projection<=200:
            excluded['INVALID_MODEL_OUTPUT']+=1;continue
        output.append({**row,'projection':round(projection,3),
            'descriptive_baseline_projection':row['projection'],
            'label':'Short-history model (research)','cohort':'SHORT_HISTORY_TRAINED_RESEARCH',
            'model':MODEL,'method':MODEL,'trained_model':True,
            'historically_evaluated':True,'prospective_validation_verified':False,
            'primary_model_eligible':False,'official_grade_eligible':False,
            'estimated_hit_chance':None,'hit_probability':None,'calibrated_probability':None,
            'opponent_context':'PRIOR_RECIPROCAL_TEAM_BOXES_MINIMUM_3',
            'historical_validation_mae':report['validation'][stat]['model_mae']})
    result={'status':STATUS,'model':MODEL,'generated_at':now.isoformat(),
        'estimates':output,'count':len(output),'excluded':dict(excluded),
        'trained_model':True,'historically_evaluated':True,'prospective_validation_verified':False,
        'primary_model_eligible':False,'official_grade_eligible':False,
        'performance_metrics':None,'calibrated':False,'notice':NOTICE,
        'official_report_issued_at':base['official_report_issued_at'],
        'accepted_markets':sorted(allowed)}
    if base.get('blocker'):result['blocker']=base['blocker']
    return result


def blocked_result(now,reason):
    return {'status':STATUS,'model':MODEL,'generated_at':stamp(now).isoformat(),
        'estimates':[],'count':0,'excluded':{},'blocker':reason,
        'trained_model':True,'historically_evaluated':True,'prospective_validation_verified':False,
        'primary_model_eligible':False,'official_grade_eligible':False,'calibrated':False,
        'performance_metrics':None,'official_report_issued_at':None,'accepted_markets':[], 'notice':NOTICE}


def load_verified_artifacts(directory):
    import hashlib,json,joblib
    from .short_history_candidate import report_digest
    raw=(directory/'short_history_candidate.joblib').read_bytes()
    report=json.loads((directory/'validation.json').read_text())
    if report.get('library_versions',{}).get('sklearn')!=__import__('sklearn').__version__:
        raise ValueError('MODEL_RUNTIME_VERSION_MISMATCH')
    if hashlib.sha256(raw).hexdigest()!=report.get('model_sha256'):
        raise ValueError('MODEL_ARTIFACT_HASH_MISMATCH')
    from io import BytesIO
    pack=joblib.load(BytesIO(raw))
    if pack.get('validation_report_sha256')!=report_digest(report):
        raise ValueError('MODEL_VALIDATION_REPORT_HASH_MISMATCH')
    return pack,report


def check_history_freshness(form,now):
    from datetime import date
    latest=date.fromisoformat(form['latest_game_date'])
    if not 0<=(stamp(now).astimezone(ET).date()-latest).days<=5:
        raise ValueError('Current player history stale')


def build_current(root,model_directory,now):
    import json,urllib.request
    from io import BytesIO
    import pandas as pd
    from .live_lagged_matchup_sidecar import current_games
    def read(name):return json.loads((root/name).read_text())
    check_history_freshness(read('docs/current_form.json'),now)
    pack,report=load_verified_artifacts(model_directory)
    url='https://huggingface.co/datasets/cbratkovics/nba-game-logs/resolve/main/game_logs/game_logs_2026-27.parquet'
    payload=urllib.request.urlopen(url,timeout=45).read()
    if len(payload)>12000000:raise ValueError('Unexpected current-source size')
    source=pd.read_parquet(BytesIO(payload)).rename(columns={'player_id':'id','game_date':'date'})
    source['date']=pd.to_datetime(source['date'],errors='raise').dt.strftime('%Y-%m-%d')
    records,coverage=current_games(read('data/nba/current/current_games.json'),source.to_dict(orient='records'))
    result=estimates(records,read('docs/prizepicks_model_input.json'),pack,report,now=now,
        primary=read('docs/lagged_matchup_all_market_ledger.json'),
        injuries=read('docs/injury_context.json'),news=read('docs/underdog_nba_injury_alerts.json'),
        free_watch=read('docs/free_nba_injury_watch.json'))
    result['source_coverage']=coverage
    result['model_artifact_sha256']=report['model_sha256']
    return result


def publish_current(root,model_directory,output,now=None,blocked=None):
    import json
    now=stamp(now or datetime.now(timezone.utc))
    try:
        result=blocked_result(now,blocked) if blocked else build_current(root,model_directory,now)
    except Exception as exc:
        result=blocked_result(now,'SOURCE_OR_VALIDATION_ERROR:'+type(exc).__name__)
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,indent=2)+'\n')
    return result


def main():
    import argparse,json
    from pathlib import Path
    parser=argparse.ArgumentParser()
    parser.add_argument('--model-dir',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--blocked')
    args=parser.parse_args()
    result=publish_current(Path(__file__).resolve().parents[1],args.model_dir,args.output,blocked=args.blocked)
    print(json.dumps({'status':result['status'],'count':result['count'],'accepted_markets':result['accepted_markets'],'blocker':result.get('blocker')}))
    return 1 if result.get('blocker') else 0

if __name__=='__main__':raise SystemExit(main())
