"""
Tennis Statistical Feature Engineering Pipeline

Transforms raw player-match rows into a rich feature set for XGBoost models.
Creates 150+ predictive features including rolling averages, surface splits,
opponent rank adjustments, fatigue indicators, and H2H signals.

Targets (7 markets, Fantasy Score deferred):
    total_games, games_won, total_sets, aces,
    bp_won, total_tiebreaks, double_faults

Output:
    data/tennis/processed/training_dataset.csv

Usage:
    $ python3 -m src.sports.tennis.features
"""

import pandas as pd
import numpy as np
import os

FEATURE_CONTRACT_VERSION = 'tennis_pre_tournament_v2'
HISTORY_AVAILABILITY_LAG_DAYS = 21

# --- CONFIGURATION ---
BASE_DIR    = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
ATP_FILE    = os.path.join(BASE_DIR, 'data', 'tennis', 'raw', 'atp_raw_matches.csv')
WTA_FILE    = os.path.join(BASE_DIR, 'data', 'tennis', 'raw', 'wta_raw_matches.csv')
OUTPUT_FILE = os.path.join(BASE_DIR, 'data', 'tennis', 'processed', 'training_dataset.csv')

# These are the columns our XGBoost models will predict (one model per target)
TARGET_STATS = [
    'total_games',
    'games_won',
    'total_sets',
    'aces',
    'bp_won',
    'total_tiebreaks',
    'double_faults',
]

# Surface encoding (one-hot)
SURFACES = ['Hard', 'Clay', 'Grass', 'Carpet']

# Round encoding (ordinal — later rounds = higher stakes/longer matches)
ROUND_ORDER = {
    'R128': 1, 'R64': 2, 'R32': 3, 'R16': 4,
    'QF': 5, 'SF': 6, 'F': 7, 'RR': 3,
}


# ---------------------------------------------------------------------------
# LOAD
# ---------------------------------------------------------------------------

def load_data():
    print("...Loading raw match data")
    frames = []
    for path, tour in [(ATP_FILE, 'atp'), (WTA_FILE, 'wta')]:
        if not os.path.exists(path):
            print(f"   ⚠️  Missing: {path}  — run builder.py first")
            continue
        df = pd.read_csv(path, low_memory=False)
        df['tour'] = tour
        frames.append(df)

    if not frames:
        print("ERROR: No data found.")
        return None

    df = pd.concat(frames, ignore_index=True)
    df['tourney_date'] = pd.to_datetime(df['tourney_date'], errors='coerce')
    df = df.dropna(subset=['tourney_date', 'player_id'])
    df = df.sort_values(['tour', 'player_id', 'tourney_date']).reset_index(drop=True)

    # Drop retired matches from TARGETS — partial stats skew the model
    df = df[df['retired'] == 0].copy()

    print(f"   Loaded {len(df):,} completed matches | {df['player_name'].nunique():,} players")
    return df


# ---------------------------------------------------------------------------
# SURFACE & CONTEXT FEATURES
# ---------------------------------------------------------------------------

def add_context_features(df):
    print("...Adding context features")

    # One-hot surface
    for s in SURFACES:
        df[f'surface_{s.lower()}'] = (df['surface'] == s).astype(int)

    # Round ordinal
    df['round_ordinal'] = df['round'].map(ROUND_ORDER).fillna(3)

    # Best-of indicator (best_of=5 for Slams)
    df['is_best_of_5'] = (df['best_of'] == 5).astype(int)

    # Tour indicator
    df['is_atp'] = (df['tour'] == 'atp').astype(int)

    # Rank features
    df['player_rank']   = pd.to_numeric(df['player_rank'],   errors='coerce').fillna(200)
    df['opp_rank']      = pd.to_numeric(df['opp_rank'],      errors='coerce').fillna(200)
    df['rank_delta']    = df['player_rank'] - df['opp_rank']   # negative = you're higher ranked
    df['rank_ratio']    = df['player_rank'] / (df['opp_rank'] + 1)
    df['log_rank']      = np.log1p(df['player_rank'])
    df['log_opp_rank']  = np.log1p(df['opp_rank'])

    return df


# ---------------------------------------------------------------------------
# ROLLING AVERAGES (player's own recent form)
# ---------------------------------------------------------------------------

def _prior_mean(df, stat, keys, window=None, min_periods=1, eligible=None):
    """Pre-tournament snapshot using strictly earlier tournament-start dates.

    Match numbers are identities, not timestamps. Outcomes become eligible only when their tournament start plus 21 days
    is strictly earlier than the prediction tournament start. Same-date outcomes
    are never available to one another. A trailing match window includes the entire oldest
    date bucket at its boundary (so it can exceed N matches), avoiding arbitrary
    ordering within a date. These are NOT true match-time/live features: the 21-day lag is a conservative research assumption, not proof of
    completion. Real completion timestamps are required before production activation.
    """
    result = np.full(len(df), np.nan)
    work = df.reset_index(drop=True)
    dates = pd.to_datetime(work['tourney_date'], errors='coerce')
    if dates.isna().any() or work[keys].isna().any().any():
        raise ValueError('Tennis history requires valid tour/player/date identity')
    mask = np.ones(len(work), dtype=bool) if eligible is None else np.asarray(eligible, dtype=bool)
    values = pd.to_numeric(work[stat], errors='coerce')
    for _, indices in work.groupby(keys, sort=False).indices.items():
        idx = np.asarray(indices)
        history = pd.DataFrame({'date': dates.iloc[idx].to_numpy(),
                                'value': values.iloc[idx].where(mask[idx]).to_numpy(),
                                'eligible': mask[idx].astype(int)})
        buckets = history.groupby('date', sort=True).agg(
            total=('value', 'sum'), count=('value', 'count'), rows=('eligible', 'sum'))
        totals = np.r_[0., buckets.total.cumsum().to_numpy()]
        counts = np.r_[0, buckets['count'].cumsum().to_numpy()]
        rows = np.r_[0, buckets.rows.cumsum().to_numpy()]
        right = buckets.index.searchsorted(
            buckets.index - pd.Timedelta(days=HISTORY_AVAILABILITY_LAG_DAYS), side='left')
        left = np.zeros(len(buckets), dtype=int)
        if window is not None:
            left = np.searchsorted(rows, np.maximum(rows[right] - window, 0), side='right') - 1
            left = np.minimum(left, right)
        n = counts[right] - counts[left]
        means = np.divide(totals[right] - totals[left], n,
                          out=np.full(len(n), np.nan), where=n >= min_periods)
        result[idx] = pd.Series(means, index=buckets.index).reindex(dates.iloc[idx]).to_numpy()
    return pd.Series(result, index=df.index)


def add_rolling_features(df):
    df = df.copy()
    stats = TARGET_STATS + ['won_match', 'sets_won', 'bp_faced', 'svpt', 'svc_games']
    features = {}
    for stat in stats:
        if stat not in df:
            continue
        for suffix, window, minimum in [('L5', 5, 3), ('L20', 20, 10), ('Season', None, 1)]:
            features[f'{stat}_{suffix}'] = _prior_mean(
                df, stat, ['tour', 'player_id'], window, minimum)
    return pd.concat([df, pd.DataFrame(features, index=df.index)], axis=1)


def add_surface_rolling(df):
    """Last 10 surface matches, with whole-date boundaries; see _prior_mean."""
    features = {}
    for surf in ['Hard', 'Clay', 'Grass']:
        for stat in ['aces', 'double_faults', 'total_games', 'games_won', 'bp_won']:
            if stat in df:
                features[f'{stat}_{surf.lower()}_L10'] = _prior_mean(
                    df, stat, ['tour', 'player_id'], 10, 3, df['surface'].eq(surf))
    return pd.concat([df.copy(), pd.DataFrame(features, index=df.index)], axis=1)


# ---------------------------------------------------------------------------
# OPPONENT ROLLING AVERAGES (how does the opponent typically play?)
# ---------------------------------------------------------------------------

def _attach_exact_opponent(df, columns):
    """Join the reciprocal player row, never another match in the tournament.

    Sackmann's tourney_date is the tournament start, not a unique match date.
    Old raw files must be rebuilt to retain match_num before using this join.
    """
    keys = ['tour', 'tourney_id', 'match_num', 'tourney_date']
    identity = keys + ['player_id', 'opp_id']
    if any(c not in df for c in identity) or df[identity].isna().any().any():
        raise ValueError('Tennis match identity missing; rebuild raw data with match_num')
    if df.duplicated(identity).any():
        raise ValueError('Duplicate tennis player-match identity')
    lookup = df[identity + columns].rename(columns={
        'player_id': 'opp_id', 'opp_id': 'player_id',
        **{c: 'opp_' + c for c in columns},
    })
    return df.merge(lookup, on=identity, how='left', validate='one_to_one', sort=False)


def add_opponent_features(df):
    """
    For each match, attach the opponent's recent rolling stats.
    E.g. opp_aces_L10 = how many aces the opponent typically hits.
    Helps predict total_games, aces allowed, etc.
    """
    print("...Attaching opponent rolling stats")

    # Build a lookup of player's rolling stats by player_id + tourney_date
    opp_cols = {}
    for stat in ['total_games', 'games_won', 'aces', 'double_faults', 'bp_won', 'bp_faced']:
        for window in ['L5', 'L20']:
            col = f'{stat}_{window}'
            if col in df.columns:
                opp_cols[f'opp_{col}'] = col

    if not opp_cols:
        return df

    return _attach_exact_opponent(df, list(opp_cols.values()))


def add_opponent_surface_context(df):
    """
    Merge opponent's SURFACE-SPECIFIC rolling stats.
    e.g. opp_aces_clay_L10 = how many aces the opponent hits ON CLAY.
    """
    print("...Attaching opponent surface-specific stats")
    
    # Identify surface-specific rolling cols from add_surface_rolling
    # Format: {stat}_{surface}_L10
    surf_cols = [c for c in df.columns if '_L10' in c and ('hard' in c or 'clay' in c or 'grass' in c)]
    
    if not surf_cols:
        return df
        
    return _attach_exact_opponent(df, surf_cols)


# ---------------------------------------------------------------------------
# FATIGUE / SCHEDULE FEATURES
# ---------------------------------------------------------------------------

def _prior_schedule(df):
    """Lagged start-date proxies, NOT actual fatigue/rest. With a 21-day lag
    matches_L14D is necessarily zero; no recent completion history is known."""
    work = df.reset_index(drop=True)
    dates = pd.to_datetime(work['tourney_date'], errors='coerce')
    if dates.isna().any() or work[['tour', 'player_id']].isna().any().any():
        raise ValueError('Tennis history requires valid tour/player/date identity')
    career = np.zeros(len(df), dtype=int)
    rest = np.full(len(df), 14., dtype=float)
    recent = np.zeros(len(df), dtype=int)
    for _, indices in work.groupby(['tour', 'player_id'], sort=False).indices.items():
        idx = np.asarray(indices)
        buckets = dates.iloc[idx].value_counts().sort_index()
        d = buckets.index
        cumulative = np.r_[0, buckets.cumsum().to_numpy()]
        available = d.searchsorted(d - pd.Timedelta(days=HISTORY_AVAILABILITY_LAG_DAYS), side='left')
        past = cumulative[available]
        left = d.searchsorted(d - pd.Timedelta(days=14), side='right')
        recent_counts = past - cumulative[np.minimum(left, available)]
        previous = pd.Series(pd.NaT, index=d, dtype=d.dtype)
        has_history = available > 0
        previous.loc[has_history] = d[available[has_history] - 1].to_numpy()
        days_rest = (pd.Series(d, index=d) - previous).dt.days.clip(upper=30).fillna(14)
        career[idx] = pd.Series(past, index=d).reindex(dates.iloc[idx]).to_numpy()
        recent[idx] = pd.Series(recent_counts, index=d).reindex(dates.iloc[idx]).to_numpy()
        rest[idx] = days_rest.reindex(dates.iloc[idx]).to_numpy()
    return career, rest, recent


def add_fatigue_features(df):
    df = df.copy()
    _, df['days_rest'], df['matches_L14D'] = _prior_schedule(df)
    df['is_b2b'] = (df['days_rest'] <= 1).astype(int)
    return df


def add_h2h_features(df):
    df = df.copy()
    # Directed pair avoids counting reciprocal rows twice and never mixes tours.
    keys = ['tour', 'player_id', 'opp_id']
    df['h2h_win_rate'] = _prior_mean(df, 'won_match', keys).fillna(0.5)
    # No full-dataset fallback: unseen H2H remains missing, never future-informed.
    df['h2h_avg_games'] = _prior_mean(df, 'total_games', keys)
    return df


def add_rank_bracket_performance(df):
    df = df.copy()
    for bracket in [20, 50, 100]:
        df[f'career_win_pct_vs_top{bracket}'] = _prior_mean(
            df, 'won_match', ['tour', 'player_id'],
            eligible=df['opp_rank'].le(bracket)).fillna(0)
    return df


def add_career_features(df):
    df = df.copy()
    df['career_matches'], _, _ = _prior_schedule(df)
    df['is_early_career'] = (df['career_matches'] < 30).astype(int)
    return df


# ---------------------------------------------------------------------------
# FINALIZE
# ---------------------------------------------------------------------------

def finalize_dataset(df):
    print("...Finalizing dataset")

    # Drop rows where all targets are NaN
    df = df.dropna(subset=TARGET_STATS, how='all')

    # Fill remaining NaNs in feature cols with 0 (safe default for tree models)
    feature_cols = [c for c in df.columns if c not in TARGET_STATS + [
        'player_id', 'opp_id', 'player_name', 'opp_name',
        'tourney_id', 'tourney_name', 'score', 'tourney_date',
    ]]
    df[feature_cols] = df[feature_cols].fillna(0)

    print(f"   Final dataset: {len(df):,} rows × {len(df.columns)} columns")
    print(f"   Players: {df['player_name'].nunique():,}")
    print(f"   Date range: {df['tourney_date'].min().date()} → {df['tourney_date'].max().date()}")
    return df


# ---------------------------------------------------------------------------
# PIPELINE
# ---------------------------------------------------------------------------

def transform_features(df):
    """Transform history and upcoming NaN-target rows without dropping fixtures."""
    df = add_context_features(df)
    df = add_rolling_features(df)
    df = add_surface_rolling(df)
    df = add_opponent_features(df)
    df = add_opponent_surface_context(df)  # NEW
    df = add_fatigue_features(df)
    df = add_h2h_features(df)
    df = add_rank_bracket_performance(df)  # NEW
    df = add_career_features(df)
    df['feature_contract_version'] = FEATURE_CONTRACT_VERSION
    return df


def build_features():
    print("=" * 55)
    print("   🎾 TENNIS FEATURE ENGINEERING")
    print("=" * 55)

    df = load_data()
    if df is None:
        return

    df = transform_features(df)
    df = finalize_dataset(df)

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    df.to_csv(OUTPUT_FILE, index=False)

    print(f"\n✅  Saved training dataset → {OUTPUT_FILE}")
    print("   Next step: Run train.py to build models.")
    print("=" * 55)


if __name__ == "__main__":
    build_features()
