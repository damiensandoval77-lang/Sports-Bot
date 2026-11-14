"""Offline Total Games distribution experiment, never an offered-line probability.

Three whole-day partitions, maturation purges and calibration-only residuals.
48h availability is an ASSUMPTION, not verified result publication provenance.
Consumes local CC BY 4.0 Valuebetennis data; performs no network or publication.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from src.sports.tennis.score_research import make_features, FEATURES
from src.sports.tennis.valuebetennis import import_season_csv


def split_three(frame, maturity_hours=48):
    if maturity_hours < 48:
        raise ValueError('Research maturity assumption must be at least 48 hours')
    dates = pd.to_datetime(frame.match_time_utc, utc=True, errors='raise')
    if dates.isna().any():
        raise ValueError('Missing match times')
    days = np.sort(dates.dt.floor('D').unique())
    if len(days) < 20:
        raise ValueError('Need at least 20 distinct UTC match days')
    calibration_start = pd.Timestamp(days[int(len(days)*.70)])
    test_start = pd.Timestamp(days[int(len(days)*.85)])
    lag = pd.Timedelta(hours=maturity_hours)
    train = dates + lag < calibration_start
    calibration = (dates >= calibration_start) & (dates + lag < test_start)
    test = dates >= test_start
    if not all(mask.any() for mask in (train, calibration, test)):
        raise ValueError('Empty partition after maturity purge')
    return train, calibration, test, calibration_start, test_start


def distribution_metrics(samples, outcomes):
    """samples(i) returns predictive integer-valued draws for held-out row i.

    Exact empirical CRPS: E|X-y| - 0.5 E|X-X'|, not a betting metric.
    Integer quantiles intentionally include boundary ties (coverage can exceed nominal).
    """
    totals = {k:0.0 for k in ('crps','coverage_50','coverage_80','coverage_90','width_50','width_80','width_90')}
    y = np.asarray(outcomes, dtype=float)
    if not len(y) or not np.isfinite(y).all() or (y<0).any() or (y!=np.rint(y)).any():
        raise ValueError('Need finite nonnegative integer outcomes')
    for i, outcome in enumerate(y):
        draws = np.sort(np.asarray(samples(i),dtype=float))
        if not len(draws) or not np.isfinite(draws).all() or (draws<0).any() or (draws!=np.rint(draws)).any():
            raise ValueError('Need finite nonnegative integer predictive draws')
        n = len(draws)
        spread = np.dot(2*np.arange(1,n+1)-n-1,draws)/(n*n)
        totals['crps'] += float(np.mean(np.abs(draws-outcome))-spread)
        for level in (50,80,90):
            tail = (1-level/100)/2
            lo,hi = np.quantile(draws,[tail,1-tail],method='inverted_cdf')
            totals['coverage_'+str(level)] += int(lo<=outcome<=hi)
            totals['width_'+str(level)] += float(hi-lo)
    return {key:value/len(y) for key,value in totals.items()}


def residual_draws(point, residuals):
    """Explicit research discretization: round shifted residuals, floor at zero.

    This is not a valid tennis-format generative model; impossible scores may have
    mass. Never turn this experimental distribution into public pick probabilities.
    """
    residuals = np.asarray(residuals,dtype=float)
    if not np.isfinite(point) or not len(residuals) or not np.isfinite(residuals).all():
        raise ValueError('Invalid calibration residuals or prediction')
    return np.maximum(0,np.rint(point+residuals))


def evaluate(csv_path, output_dir, as_of):
    as_of = pd.Timestamp(as_of)
    if as_of.tzinfo is None or pd.isna(as_of):
        raise ValueError('as_of must have timezone')
    rows, imported = import_season_csv(csv_path)
    # Research-only receipt approximation. Never label this observed availability.
    mature = pd.to_datetime(rows.match_time_utc,utc=True)+pd.Timedelta(hours=48)<as_of
    frame = make_features(rows.loc[mature].copy())
    # One symmetric target per match; inference must preserve this same ordering.
    frame = frame[frame.player_id.astype(str)<frame.opp_id.astype(str)].copy()
    if frame.match_id.duplicated().any():
        raise ValueError('Duplicate match identity')
    train, cal, test, cal_start, test_start = split_three(frame)
    model = HistGradientBoostingRegressor(max_iter=100,max_leaf_nodes=15,l2_regularization=10,random_state=42)
    model.fit(frame.loc[train,FEATURES],frame.loc[train,'total_games'])
    residuals = frame.loc[cal,'total_games'].to_numpy()-model.predict(frame.loc[cal,FEATURES])
    points = model.predict(frame.loc[test,FEATURES])
    truth = frame.loc[test,'total_games'].to_numpy()
    baseline = frame.loc[train,'total_games'].to_numpy()
    model_metrics = distribution_metrics(lambda i:residual_draws(points[i],residuals),truth)
    baseline_metrics = distribution_metrics(lambda i:baseline,truth)
    # Fixed subgroup diagnostics, never used to select or retune this model.
    breakdown = {}
    test_frame = frame.loc[test].reset_index(drop=True)
    for tour in ('atp','wta'):
        indices = np.flatnonzero(test_frame.tour.to_numpy()==tour)
        if len(indices):
            breakdown[tour] = {'matches':len(indices), **distribution_metrics(
                lambda i:residual_draws(points[indices[i]],residuals),truth[indices])}
    report = {
        'mode':'offline_distribution_research_only','live_ready':False,
        'production_activation_allowed':False,'offered_lines_used':False,
        'target':'total_games','as_of':str(as_of),'maturity_assumption_hours':48,
        'partition_rule':'whole UTC days: 70% train / 15% calibration / 15% test; 48h purge before each boundary',
        'calibration_start':str(cal_start),'test_start':str(test_start),
        'train_matches':int(train.sum()),'calibration_matches':int(cal.sum()),'test_matches':int(test.sum()),
        'purged_matches':int((~(train|cal|test)).sum()),
        'model_parameters':model.get_params(),'features':FEATURES,
        'feature_protocol':'rolling as-of histories; earlier calibration/test outcomes enter later histories only after assumed48h lag; model and residual distribution remain frozen',
        'distribution':'rounded nonnegative point forecast + empirical calibration-only residuals',
        'model':model_metrics,'training_climatology_baseline':baseline_metrics,'test_by_tour':breakdown,
        'source':'https://www.valuebetennis.com/en/donnees.htm','license':'CC BY 4.0',
        'attribution':'Valuebetennis, Tennis results and odds since 2021; transformed score-only research',
        'source_sha256':hashlib.sha256(Path(csv_path).read_bytes()).hexdigest(),'import':imported,
        'limitations':['48h maturity is not observed publication provenance',
            'Mixed competition levels and unverified scheduled match format',
            'Pooled residuals may miscalibrate tour/surface/format subgroups',
            'Rounded residual distribution may assign mass to impossible tennis scores',
            'One final holdout; no prospective validation, offered quotes or betting hit rates',
            'No production fixture context, identity crosswalk or calibrated quote probability contract'],
        'release_gates':['Observed result-availability receipts and as-of feature reconstruction',
            'Verified future opponent, surface, tour and scheduled format',
            'Independent prospective distribution validation and score-support checks',
            'Actual immutable standard-line capture and held-out Over/Under/Push validation',
            'Verified result matching and retirement/void policy; no fabricated historical quotes']}
    out=Path(output_dir);out.mkdir(parents=True,exist_ok=True)
    (out/'total_games_distribution_evaluation.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--csv',required=True);parser.add_argument('--output-dir',required=True);parser.add_argument('--as-of',required=True)
    args=parser.parse_args()
    print(json.dumps(evaluate(args.csv,args.output_dir,args.as_of),indent=2))

if __name__=='__main__':main()
