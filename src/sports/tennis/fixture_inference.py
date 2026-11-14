"""Fail-closed local research inference; no provider calls or public publishing.

Fixtures must come from a permitted source, with explicit timezone and exact
Valuebetennis player IDs. This is an integration boundary, not a fixture feed.
"""
from urllib.parse import urlparse
import numpy as np
import pandas as pd
from src.sports.tennis.score_research import FEATURES, TARGETS, make_features

CONTRACT = 'tennis_score_research_v1'


def _utc(value):
    stamp = pd.Timestamp(value)
    if pd.isna(stamp) or stamp.tzinfo is None:
        raise ValueError('Explicit timezone required')
    return stamp.tz_convert('UTC')


def fixture_features(history, fixture, *, as_of, history_observed_at):
    now, observed = _utc(as_of), _utc(history_observed_at)
    seen, start = _utc(fixture['observed_at']), _utc(fixture['start_time_utc'])
    if not pd.Timedelta(0) <= now-observed <= pd.Timedelta(hours=24):
        raise ValueError('History observation is stale or future-dated')
    if not pd.Timedelta(0) <= now-seen <= pd.Timedelta(minutes=30):
        raise ValueError('Fixture observation is stale or future-dated')
    if not now < start <= now + pd.Timedelta(days=7):
        raise ValueError('Fixture must be upcoming within seven days')
    if fixture.get('status') != 'scheduled':
        raise ValueError('Fixture is not scheduled')
    source = urlparse(fixture.get('source_url',''))
    if source.scheme != 'https' or not source.netloc:
        raise ValueError('Fixture source URL required')
    if fixture.get('tour') not in ('atp','wta') or fixture.get('surface') not in ('Hard','Clay','Grass','Carpet'):
        raise ValueError('Verified tour and surface required')
    ids = fixture['player_ids']
    if len(ids) != 2 or ids[0] == ids[1] or any(not isinstance(p,str) or not p.startswith('valuebetennis:') for p in ids):
        raise ValueError('Two distinct namespaced player IDs required')
    match_id = fixture.get('match_id')
    if not isinstance(match_id,str) or not match_id or match_id in set(history.match_id):
        raise ValueError('New fixture identity required')
    times = pd.to_datetime(history.match_time_utc, utc=True, errors='raise')
    if (times > observed).any():
        raise ValueError('Historical result starts after observation')
    if times.isna().any():
        raise ValueError('History timestamp missing')
    # Observed before prediction AND mature under the same research assumption.
    eligible = history[(times + pd.Timedelta(days=2) < now)].copy()
    if eligible.empty or times.max() < now-pd.Timedelta(days=7):
        raise ValueError('No recent source history')
    for player in ids:
        count = len(eligible[(eligible.player_id==player)&(eligible.tour==fixture['tour'])])
        if count < 10:
            raise ValueError('Insufficient exact player history')
    upcoming = pd.DataFrame([dict(match_id=match_id,player_id=p,opp_id=o,
        tour=fixture['tour'],surface=fixture['surface'],match_time_utc=start,
        **{target:np.nan for target in TARGETS}) for p,o in (ids,ids[::-1])])
    # Same implementation as training; never copy the previous match feature row.
    frame = make_features(pd.concat([eligible,upcoming],ignore_index=True))
    row = frame[(frame.match_id==match_id)&(frame.player_id==min(ids))]
    if len(row)!=1 or row[FEATURES].isna().any().any():
        raise ValueError('Incomplete exact fixture features')
    return row[FEATURES]


def predict_fixture(history, fixture, bundles, *, as_of, history_observed_at):
    now = _utc(as_of)
    features = fixture_features(history,fixture,as_of=now,history_observed_at=history_observed_at)
    projections = {}
    for target,bundle in bundles.items():
        if target not in TARGETS or bundle.get('target') != target or bundle.get('contract') != CONTRACT:
            raise ValueError('Unsupported model contract')
        if bundle.get('features') != FEATURES or bundle.get('mode') != 'offline_research_only':
            raise ValueError('Incompatible model feature schema')
        trained = _utc(bundle['trained_as_of'])
        if not pd.Timedelta(0) <= now-trained <= pd.Timedelta(days=30):
            raise ValueError('Model is stale or future-trained')
        value = float(bundle['model'].predict(features)[0])
        if not np.isfinite(value) or value < 0:
            raise ValueError('Invalid model output')
        projections[target] = value
    if not projections:
        raise ValueError('No models supplied')
    return {'mode':'offline_research_only','live_ready':False,
        'match_id':fixture['match_id'],'as_of':str(now),
        'source_url':fixture['source_url'],'projections':projections,
        'probabilities':None,'limitations':['Not calibrated betting probabilities',
            '48h result-availability assumption, not observed completion provenance',
            'Fixture supplied locally; no automated fixture feed is configured']}
