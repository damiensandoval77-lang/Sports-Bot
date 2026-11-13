"""Strictly reviewed complete official final ledger, never partial-feed zero fill.

New games/corrections require source review and a new pinned transcription hash.
The PDF pages 1-3 prove participation, complete categories, scoring and fumbles.
"""
import hashlib,json,math
from pathlib import Path
GAME='2026_10_WAS_NYG'
FILE='verified_gamebook_'+GAME+'.json'
REVIEWED_SHA='ae56c0f2736c8d0c48a4ea3d0b154b478c95e4dfcf497b8e0a2f0a946e0d7024'
PDF_SHA='b32911c5f585d65b89b513fb559801cc4cfeebbd3252356d0e04fac8f9ec8c53'
URL='https://static.www.nfl.com/image/upload/v1794544320/gamecenter/ab5828d9-4feb-11f1-abca-2c54536568a9.pdf'
CATEGORIES={'passing':('attempts','completions','passing_yards','passing_tds','passing_interceptions'),
 'rushing':('carries','rushing_yards','rushing_tds'),
 'receiving':('targets','receptions','receiving_yards','receiving_tds')}
FIELDS=sum(CATEGORIES.values(),())+('fumbles_lost',)

def digest(data):return hashlib.sha256(json.dumps(data,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def validate(data,scheduled):
    if digest(data)!=REVIEWED_SHA:raise ValueError('Unreviewed official gamebook transcription')
    if data.get('source_sha256')!=PDF_SHA or data.get('source_url')!=URL:raise ValueError('Gamebook source mismatch')
    if not scheduled or scheduled.get('status')!='final' or data.get('verified_final') is not True:
        raise ValueError('Gamebook is not scheduled final')
    if any(data.get(k)!=scheduled.get(k) for k in ('game_id','week','away','home','away_score','home_score','kickoff_utc')):
        raise ValueError('Gamebook exact event/score mismatch')
    rows=data['players']; by_id={p['player_id']:p for p in rows}
    if len(rows)!=20 or len(by_id)!=20:raise ValueError('Ambiguous gamebook identities')
    for p in rows:
        if p.get('participation_page')!=1 or p.get('participation')!='starter_or_substitute_on_gamebook_page_1':
            raise ValueError('Missing verified participation')
        if any(isinstance(p.get(k),bool) or not isinstance(p.get(k),(int,float)) or not math.isfinite(p[k]) for k in FIELDS):
            raise ValueError('Incomplete final player components')
    for team in ('WAS','NYG'):
        teamrows=[p for p in rows if p['team']==team]
        for field,total in data['verified_team_totals'][team].items():
            if sum(p[field] for p in teamrows)!=total:raise ValueError('Incomplete category total')
        for category,fields in CATEGORIES.items():
            observed=data['observed_'+category+'_rows'][team]
            members=data['category_membership'][category][team]
            if members!=[r[0] for r in observed]:raise ValueError('Incomplete category membership')
            for p in teamrows:
                matches=[r[1:] for r in observed if r[0]==p['player']]
                expected=matches[0] if len(matches)==1 else [0]*len(fields) if not matches else None
                if expected!=[p[k] for k in fields]:raise ValueError('Individual row disagrees with complete ledger')
        scoring=data['verified_game_scoring']
        if any(scoring[k]!=[] for k in ('two_point_conversions','return_touchdowns','offensive_fumble_recovery_touchdowns')):
            raise ValueError('Unsupported extra scoring')
        for p in teamrows:
            for kind,field in [('rushing','rushing_tds'),('receiving','receiving_tds')]:
                if p[field]!=sum(t['player_id']==p['player_id'] and t['type']==kind for t in scoring['touchdowns']):
                    raise ValueError('Scoring and individual TD conflict')
            losses=data['verified_fumbles_lost'][team]['player_lost']
            if p['fumbles_lost']!=sum(x['lost'] for x in losses if x['player_id']==p['player_id']):
                raise ValueError('Fumble attribution conflict')
        points=6*sum(by_id[t['player_id']]['team']==team for t in scoring['touchdowns'])
        points+=3*sum(f['team']==team for f in scoring['field_goals'])
        points+=sum(x['made'] for x in scoring['kicking_extra_points'] if x['team']==team)
        if points!=data['away_score' if team=='WAS' else 'home_score']:raise ValueError('Incomplete final scoring')
    return rows

def fantasy(p):
    return round(.04*p['passing_yards']+4*p['passing_tds']-p['passing_interceptions']+
      .1*p['rushing_yards']+6*p['rushing_tds']+p['receptions']+
      .1*p['receiving_yards']+6*p['receiving_tds']-p['fumbles_lost'],8)

def supplement(boxroot,schedule,boxes):
    path=Path(boxroot)/FILE
    if not path.exists():return
    rows=validate(json.loads(path.read_text()),schedule.get(GAME))
    old=boxes.get(GAME,{})
    for p in rows:
        previous=old.get(p['player_id'],{})
        if previous and (previous.get('team')!=p['team'] or previous.get('player')!=p['player']):
            raise ValueError('Gamebook player identity conflicts with published source')
        for field in FIELDS:
            if previous.get(field) is not None and float(previous[field])!=p[field]:
                raise ValueError('Gamebook conflicts with published final stats: '+field)
    # Only this fully validated path may mark complete fantasy components.
    boxes[GAME]={p['player_id']:{**p,'verified_gamebook_sha256':REVIEWED_SHA,
        'verified_prizepicks_full_ppr':fantasy(p)} for p in rows}
