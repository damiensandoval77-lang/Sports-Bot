"""Offline, score-only research. Not a live estimate or betting probability.

Consumes local legally obtained Valuebetennis CSV; never makes provider requests.
Future fixture ingestion and calibrated offered-line validation remain release gates.
"""
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error
from src.sports.tennis.validation import chronological_masks

TARGETS = ['total_games', 'total_sets', 'total_tiebreaks']
FEATURES = ['surface_code', 'is_atp', 'history_count', 'opp_history_count'] + [
    prefix + target + '_L10' for prefix in ['', 'opp_'] for target in TARGETS]


def make_features(rows):
    """Strict prior history, 48h embargo from recorded match start, tour+ID keyed.

    Match start is not completion time. This lag is a conservative research
    approximation, not enough provenance for production pregame estimates.
    """
    frame = rows.copy()
    frame['match_time_utc'] = pd.to_datetime(frame['match_time_utc'], utc=True, errors='raise')
    frame = frame.sort_values(['match_time_utc', 'match_id', 'player_id']).reset_index(drop=True)
    frame['surface_code'] = frame.surface.map({'Hard':0, 'Clay':1, 'Grass':2, 'Carpet':3})
    if frame['surface_code'].isna().any():
        raise ValueError('Unsupported surface')
    frame['is_atp'] = (frame.tour == 'atp').astype(int)
    for c in ['history_count'] + [t+'_L10' for t in TARGETS]:
        frame[c] = np.nan
    for _, group in frame.groupby(['tour', 'player_id'], sort=False):
        times = group.match_time_utc.array.asi8
        values = group[TARGETS].to_numpy(dtype=float)
        derived = np.full((len(group), 4), np.nan)
        for i, index in enumerate(group.index):
            # searchsorted(left) excludes exact 48h boundary, current and later rows.
            end = np.searchsorted(times, times[i]-pd.Timedelta(days=2).value, side='left')
            history = values[max(0,end-10):end]
            derived[i, 0] = end
            if len(history):
                derived[i, 1:] = np.mean(history, axis=0)
        frame.loc[group.index, ['history_count']+[t+'_L10' for t in TARGETS]] = derived
    keys = ['match_id','tour','player_id','opp_id']
    cols = ['history_count']+[t+'_L10' for t in TARGETS]
    lookup = frame[keys+cols].rename(columns={'player_id':'opp_id','opp_id':'player_id', **{c:'opp_'+c for c in cols}})
    return frame.merge(lookup, on=keys, how='left', validate='one_to_one')


def evaluate(rows, output_dir, as_of):
    as_of = pd.Timestamp(as_of)
    if as_of.tzinfo is None:
        raise ValueError('as_of needs explicit timezone')
    rows = rows[pd.to_datetime(rows.match_time_utc, utc=True) + pd.Timedelta(days=2) < as_of].copy()
    frame = make_features(rows)
    # One copy per match for symmetric score targets, selected by stable ID not winner.
    frame = frame[frame.player_id.astype(str) < frame.opp_id.astype(str)].copy()
    train, test, cutoff = chronological_masks(frame, date_column='match_time_utc', embargo_days=2)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    report = {'mode':'offline_research_only', 'live_ready':False,
              'as_of':str(as_of), 'holdout_start':str(cutoff),
              'train_matches':int(train.sum()), 'test_matches':int(test.sum()),
              'source':'https://www.valuebetennis.com/en/donnees.htm',
              'attribution':'Valuebetennis, CC BY 4.0; transformed score-only research',
              'limitations':['No verified future fixtures', 'No calibrated betting-line probabilities',
                             '48h completion availability is an assumption, not observed provenance',
                             'No aces, double faults, break points or games-won model'], 'metrics':{}}
    for target in TARGETS:
        model = HistGradientBoostingRegressor(max_iter=100, max_leaf_nodes=15, l2_regularization=10, random_state=42)
        model.fit(frame.loc[train, FEATURES], frame.loc[train,target])
        pred = model.predict(frame.loc[test, FEATURES])
        baseline = np.full(test.sum(), frame.loc[train,target].mean())
        report['metrics'][target] = {'mae':float(mean_absolute_error(frame.loc[test,target], pred)),
                                    'training_mean_baseline_mae':float(mean_absolute_error(frame.loc[test,target], baseline))}
        import joblib
        joblib.dump({'model':model,'features':FEATURES,'mode':'offline_research_only'}, out / (target+'.joblib'))
    (out/'evaluation.json').write_text(json.dumps(report, indent=2)+'\n')
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--csv',required=True)
    parser.add_argument('--output-dir',required=True)
    parser.add_argument('--as-of',required=True)
    args=parser.parse_args()
    from src.sports.tennis.valuebetennis import import_season_csv
    rows, source_report = import_season_csv(args.csv)
    report = evaluate(rows,args.output_dir,args.as_of)
    import hashlib
    report['source_import'] = source_report
    report['source_sha256'] = hashlib.sha256(Path(args.csv).read_bytes()).hexdigest()
    (Path(args.output_dir)/'evaluation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':
    main()
