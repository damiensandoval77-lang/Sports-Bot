"""Strict, local-only import of Valuebetennis's CC BY 4.0 season exports.

Source/required attribution: Valuebetennis, Tennis results and odds since 2021,
https://www.valuebetennis.com/en/donnees.htm
License: https://creativecommons.org/licenses/by/4.0/

No network calls or credentials. CSV files are semicolon-separated. Their date
is the match time in UTC, NOT the time the result became available. No completion
time, serve statistics, rankings, or upcoming fixtures are fabricated. Score
orientation is undocumented: only symmetric match targets are emitted. Player
IDs are namespaced and must not be joined to Sackmann/ATP IDs directly.
"""
import re
from pathlib import Path
import pandas as pd

SOURCE_URL = 'https://www.valuebetennis.com/en/donnees.htm'
LICENSE_URL = 'https://creativecommons.org/licenses/by/4.0/'
ATTRIBUTION = f'Valuebetennis, Tennis results and odds since 2021, {SOURCE_URL}'
SURFACES = {'dur': 'Hard', 'dur intérieur': 'Hard', 'terre battue': 'Clay',
            'gazon': 'Grass', 'moquette intérieur': 'Carpet'}
REQUIRED = ['match_id', 'date', 'tournoi', 'tournoi_id', 'genre', 'surface',
            'tour', 'joueur1', 'joueur1_id', 'joueur2', 'joueur2_id',
            'vainqueur_id', 'score']
OUTPUT = ['source', 'source_url', 'license_url', 'attribution', 'match_id',
          'match_num', 'match_time_utc', 'tourney_date', 'tourney_id',
          'tourney_name', 'tour', 'surface', 'source_round', 'player_id',
          'player_name', 'opp_id', 'opp_name', 'won_match', 'score',
          'total_games', 'total_sets', 'total_tiebreaks']


def symmetric_score_targets(score):
    """Return complete conventional BO3/BO5 match totals, or raise ValueError.

    Reject retirement/walkover text, partial sets, super-tiebreaks and ambiguous
    advantage sets. Do not interpret whose side of the score is whose.
    """
    if not isinstance(score, str):
        raise ValueError('Missing score')
    tokens = score.strip().split()
    if not 2 <= len(tokens) <= 5:
        raise ValueError('Unsupported match length')
    wins = [0, 0]
    games = tiebreaks = 0
    prefixes = []
    for i, token in enumerate(tokens):
        m = re.fullmatch(r'(\d+)-(\d+)(?:\((\d+)\))?', token)
        if not m:
            raise ValueError('Unsupported score token')
        a, b = int(m[1]), int(m[2])
        high, low = max(a, b), min(a, b)
        if not ((high == 6 and low <= 4) or (high == 7 and low in (5, 6))):
            raise ValueError('Incomplete or unsupported set')
        tb = high == 7 and low == 6
        if m[3] is not None and not tb:
            raise ValueError('Tiebreak annotation on non-tiebreak set')
        wins[int(b > a)] += 1
        games += a + b
        tiebreaks += int(tb)
        prefixes.append(max(wins))
    needed = 3 if max(wins) == 3 else 2
    if any(n >= needed for n in prefixes[:-1]):
        raise ValueError('Sets played after match already decided')
    if max(wins) != needed or min(wins) >= needed:
        raise ValueError('Incomplete match')
    return dict(total_games=games, total_sets=len(tokens), total_tiebreaks=tiebreaks)


def import_season_csv(path):
    """Return (player_rows, rejection_report) from a legitimately obtained file.

    Missing schema/duplicate source match IDs fail the whole import. Malformed
    individual records are excluded and counted, never silently zero-filled.
    """
    path = Path(path)
    df = pd.read_csv(path, sep=';', dtype=str)
    missing = set(REQUIRED) - set(df.columns)
    if missing:
        raise ValueError(f'Missing source columns: {sorted(missing)}')
    if df.match_id.isna().any() or df.match_id.duplicated().any():
        raise ValueError('Missing or duplicate source match ID')
    rows, reasons = [], {}
    for record in df.to_dict('records'):
        try:
            if any(pd.isna(record[k]) or not str(record[k]).strip() for k in REQUIRED):
                raise ValueError('Missing required value')
            if record['genre'] not in ('atp', 'wta'):
                raise ValueError('Unsupported tour')
            if record['surface'] not in SURFACES:
                raise ValueError('Unsupported surface')
            ids = [record['joueur1_id'], record['joueur2_id']]
            if ids[0] == ids[1] or record['vainqueur_id'] not in ids:
                raise ValueError('Invalid participant identity')
            stamp = pd.to_datetime(record['date'], format='%Y-%m-%d %H:%M:%S', errors='raise', utc=True)
            if pd.isna(stamp):
                raise ValueError('Invalid match timestamp')
            targets = symmetric_score_targets(record['score'])
            for side, other in ((1, 2), (2, 1)):
                rows.append(dict(source='valuebetennis', source_url=SOURCE_URL,
                    license_url=LICENSE_URL, attribution=ATTRIBUTION,
                    match_id='valuebetennis:' + record['match_id'],
                    match_num=record['match_id'], match_time_utc=stamp,
                    tourney_date=stamp, tourney_id='valuebetennis:' + record['tournoi_id'],
                    tourney_name=record['tournoi'], tour=record['genre'],
                    surface=SURFACES[record['surface']], source_round=record['tour'],
                    player_id='valuebetennis:' + record[f'joueur{side}_id'],
                    player_name=record[f'joueur{side}'],
                    opp_id='valuebetennis:' + record[f'joueur{other}_id'],
                    opp_name=record[f'joueur{other}'],
                    won_match=int(record[f'joueur{side}_id'] == record['vainqueur_id']),
                    score=record['score'], **targets))
        except (ValueError, TypeError, OverflowError) as exc:
            reason = str(exc) if str(exc) in ('Missing required value', 'Unsupported tour',
                'Unsupported surface', 'Invalid participant identity', 'Invalid match timestamp',
                'Missing score', 'Unsupported match length', 'Unsupported score token',
                'Incomplete or unsupported set', 'Tiebreak annotation on non-tiebreak set',
                'Sets played after match already decided', 'Incomplete match') else 'Invalid match timestamp'
            reasons[reason] = reasons.get(reason, 0) + 1
    return pd.DataFrame(rows, columns=OUTPUT), {
        'input_matches': len(df), 'accepted_matches': len(rows) // 2,
        'rejected_matches': sum(reasons.values()), 'reasons': reasons,
        'score_orientation': 'unverified; symmetric targets only',
        'timestamp_semantics': 'match time UTC, not result availability',
    }
