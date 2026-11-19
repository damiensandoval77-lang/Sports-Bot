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
# Additional source-reviewed games only; hashes are not generated at runtime.
REVIEWED_GAMES={'2026_10_LA_ARI':{
    'sha':'000c296c5263d665bc1fd8484953339a2c6debc73462773dce00f1e912d7a2be',
    'pdf_sha':'5bc5f89cde8e0cdb66ffac14e63808d85197c5652abd9cbade4346ea1ecaf8fa',
    'url':'https://static.www.nfl.com/image/upload/v1794854921/gamecenter/ab78a133-4feb-11f1-abca-2c54536568a9.pdf',
    'rows':23}}

REVIEWED_GAMES.update({'2026_10_BUF_NYJ': {'excluded_targets': ['TGT'],
                     'pdf_sha': '19f04098343b73fd0633519f68469a65e877a9a7270b5e299b167cbbcb947527',
                     'rows': 24,
                     'sha': '22d07f230fdb2a4ffe4a4fcfc8ce3d157185f467ccaca51848e52efe99f9199f',
                     'url': 'https://static.www.nfl.com/image/upload/v1794829722/gamecenter/ab789ac9-4feb-11f1-abca-2c54536568a9.pdf'},
 '2026_10_MIN_GB': {'excluded_targets': ['TGT'],
                    'pdf_sha': 'd19ef8d9871d04eac9da1a14eec1d9cea99e027bb9d683b0192a1665413c4189',
                    'rows': 22,
                    'sha': 'd42bd473ed91298b356c967ee28499fad055f3951fd9fa77e8bcbb888a4a11ef',
                    'url': 'https://static.www.nfl.com/image/upload/v1794829721/gamecenter/ab788967-4feb-11f1-abca-2c54536568a9.pdf'},
 '2026_10_SEA_LV': {'excluded_targets': ['TGT'],
                    'pdf_sha': '2e5c44630e0f55fa54b0794451168da1a88eccc42ea0dda90be5beb0221298d3',
                    'rows': 20,
                    'sha': '2a9b61a5dca1d6d06a14b82c8da9ba23c4efdb55fe755e61c1ab717fa298daa9',
                    'url': 'https://static.www.nfl.com/image/upload/v1794829726/gamecenter/ab78a43c-4feb-11f1-abca-2c54536568a9.pdf'}})

# Early-injury/Reboot outcome not established: preserve every original outcome.
REVIEWED_GAMES['2026_10_BUF_NYJ']['excluded_player_ids']=['00-0041511']

# Remaining source-reviewed Week 10 games.
REVIEWED_GAMES.update({'2026_10_CAR_NO': {'excluded_targets': ['TGT'],
                    'pdf_sha': '0145bf25a0105f8c54ea0a2c59fa8f8434b921236dff5c7dcbc8f823ac6c2e1f',
                    'rows': 19,
                    'sha': 'e1f2f8f63be49fd96a4576420ede32de03a5f3b413a5b0679de16e612fca63c3',
                    'url': 'https://static.www.nfl.com/image/upload/v1794829721/gamecenter/ab789769-4feb-11f1-abca-2c54536568a9.pdf'},
 '2026_10_HOU_CLE': {'excluded_targets': ['TGT'],
                     'pdf_sha': 'c46193bbb201a09c90657693c75a2ab2fa7c96dda0cca612a7b1529ad2374b40',
                     'rows': 20,
                     'sha': '562b0435746ebd882ca6c788870185575922a20e1c7d5c965d75f518db64c838',
                     'url': 'https://static.www.nfl.com/image/upload/v1794829724/gamecenter/ab583279-4feb-11f1-abca-2c54536568a9.pdf'},
 '2026_10_JAX_TEN': {'excluded_targets': ['TGT'],
                     'pdf_sha': 'a3307c0f336e8dbb48a99238294203479ad9faa8a6120012170018b5dcd5565a',
                     'rows': 21,
                     'sha': '536fa91ad20ef2e1ac07a20841a05e1bd75b89dc281238d39536550a318ae7c0',
                     'url': 'https://static.www.nfl.com/image/upload/v1794829722/gamecenter/ab789e15-4feb-11f1-abca-2c54536568a9.pdf'},
 '2026_10_KC_ATL': {'excluded_targets': ['TGT'],
                    'pdf_sha': '387e0e0fc327989a835c824064d1b3527e0c7aa284c3782ef8dd3ea0e7e59741',
                    'rows': 23,
                    'sha': 'f80b660cf2c7932688bde795aaa964fe33a162fd62e4674fe4ff937572951706',
                    'url': 'https://static.www.nfl.com/image/upload/v1794829722/gamecenter/ab582f5b-4feb-11f1-abca-2c54536568a9.pdf'},
 '2026_10_LAC_BAL': {'excluded_targets': ['TGT'],
                     'pdf_sha': 'a208d7cc02dbe9502d3ff0e3125eabe890c74a0fe132bec844e4eda231a2dbd7',
                     'rows': 19,
                     'sha': '90851f1d49dc46e35d50c8cb3e29e762e4fd61cd3493a6235163dd2b9e0e45aa',
                     'url': 'https://static.www.nfl.com/image/upload/v1794916121/gamecenter/ab78ad5a-4feb-11f1-abca-2c54536568a9.pdf'},
 '2026_10_MIA_IND': {'allow_reviewed_defensive_scores': True,
                     'excluded_targets': ['TGT'],
                     'pdf_sha': '107be568d8049a10fa4a02b35b37392815424e95f8f3cb8125165b4bbd4798fc',
                     'rows': 22,
                     'sha': 'f9b89952c147cf7998284809b2b75f6e4d0501d9668fc0286d7d31ac5ed6025d',
                     'url': 'https://static.www.nfl.com/image/upload/v1794829723/gamecenter/ab789365-4feb-11f1-abca-2c54536568a9.pdf'},
 '2026_10_NE_DET': {'excluded_targets': ['TGT'],
                    'pdf_sha': '26b3c925e5cd0fd34d3eebae219faa6e98bd6c6dbe64b902ae677d7f8af225a0',
                    'rows': 24,
                    'sha': 'bd91273ba5700992679ba3a7af6f1cd565d62ba370223e07b3cf04f9dfdadd47',
                    'url': 'https://static.www.nfl.com/image/upload/v1794829721/gamecenter/ab582c2f-4feb-11f1-abca-2c54536568a9.pdf'},
 '2026_10_PIT_CIN': {'allow_reviewed_two_point_conversions': True,
                     'excluded_targets': ['TGT'],
                     'pdf_sha': 'ac36c23ed9f831d9684fdb474a7503313d035012a5ce52a6755690f8936e6e1d',
                     'rows': 23,
                     'sha': 'a5a8e0e3cea83566a631cfaf0b85117ea4e29c7d413e9489074296cd22a8f144',
                     'url': 'https://static.www.nfl.com/image/upload/v1794829727/gamecenter/ab78aa48-4feb-11f1-abca-2c54536568a9.pdf'},
 '2026_10_SF_DAL': {'allow_reviewed_two_point_conversions': True,
                    'excluded_targets': ['TGT'],
                    'pdf_sha': 'c5378c33a7fcac7cc0c2dde42e6a89640252f86325f192692a577d37b4cdc651',
                    'rows': 22,
                    'sha': 'aa0cf288a117848a1ca57dbfd954ad200b96b8dfa5dcf74a9fe8e11030457bdc',
                    'url': 'https://static.www.nfl.com/image/upload/v1794829724/gamecenter/ab78a748-4feb-11f1-abca-2c54536568a9.pdf'}})

def reviewed_spec(game):
    if game==GAME:return {'sha':REVIEWED_SHA,'pdf_sha':PDF_SHA,'url':URL,'rows':20}
    return REVIEWED_GAMES.get(game)

def verified_fantasy(player):
    gid=player.get('verified_gamebook_game_id',GAME)
    spec=reviewed_spec(gid)
    if spec and player.get('verified_gamebook_sha256')==spec['sha']:
        return player.get('verified_prizepicks_full_ppr')
    return None

CATEGORIES={'passing':('attempts','completions','passing_yards','passing_tds','passing_interceptions'),
 'rushing':('carries','rushing_yards','rushing_tds'),
 'receiving':('targets','receptions','receiving_yards','receiving_tds')}
FIELDS=sum(CATEGORIES.values(),())+('fumbles_lost',)

def digest(data):return hashlib.sha256(json.dumps(data,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def validate(data,scheduled):
    spec=reviewed_spec(data.get('game_id'))
    if not spec or digest(data)!=spec['sha']:raise ValueError('Unreviewed official gamebook transcription')
    if data.get('source_sha256')!=spec['pdf_sha'] or data.get('source_url')!=spec['url']:raise ValueError('Gamebook source mismatch')
    if not scheduled or scheduled.get('status')!='final' or data.get('verified_final') is not True:
        raise ValueError('Gamebook is not scheduled final')
    if any(data.get(k)!=scheduled.get(k) for k in ('game_id','week','away','home','away_score','home_score','kickoff_utc')):
        raise ValueError('Gamebook exact event/score mismatch')
    rows=data['players']; by_id={p['player_id']:p for p in rows}
    if len(rows)!=spec['rows'] or len(by_id)!=spec['rows']:raise ValueError('Ambiguous gamebook identities')
    for p in rows:
        if p.get('participation_page')!=1 or p.get('participation')!='starter_or_substitute_on_gamebook_page_1':
            raise ValueError('Missing verified participation')
        if any(isinstance(p.get(k),bool) or not isinstance(p.get(k),(int,float)) or not math.isfinite(p[k]) for k in FIELDS):
            raise ValueError('Incomplete final player components')
        if data['game_id']!=GAME:
            snaps=p.get('offensive_snaps')
            snap_proof=(type(snaps) is int and snaps>0 and type(p.get('offensive_snaps_page')) is int and p['offensive_snaps_page']>0)
            if not (p.get('offensive_starter') is True or snap_proof or any(p[k]>0 for k in ('attempts','carries','targets'))):
                raise ValueError('No verified offensive participation')
    for p in rows:
        proof=p.get('verified_zero_targets')
        if proof is not None:
            totals=data['verified_team_totals'][p['team']]
            n=totals['attempts']
            if (proof.get('method')!='complete_team_targets_equal_pass_attempts_with_independent_pbp'
                    or proof.get('game_id')!=data['game_id'] or proof.get('team')!=p['team']
                    or proof.get('player_id')!=p['player_id'] or p['targets']!=0
                    or proof.get('official_gamebook_page')!=2 or n<=0
                    or totals['targets']!=n or proof.get('team_pass_attempts')!=n
                    or proof.get('team_receiver_targets')!=n
                    or len(proof.get('independent_pass_play_ids',[]))!=n
                    or len(set(proof['independent_pass_play_ids']))!=n
                    or len(proof.get('independent_receiver_ids',[]))!=n
                    or any(not x or x==p['player_id'] for x in proof['independent_receiver_ids'])):
                raise ValueError('Unproven zero target allocation')
    teams=(data['away'],data['home'])
    scoring=data['verified_game_scoring']
    conversions=scoring['two_point_conversions']
    defense=scoring.get('defensive_scores',[])
    if conversions and not spec.get('allow_reviewed_two_point_conversions'):
        raise ValueError('Unsupported extra scoring')
    if defense and not spec.get('allow_reviewed_defensive_scores'):
        raise ValueError('Unsupported defensive scoring')
    two_point_keys=set()
    for e in conversions:
        team,method,ids=e.get('team'),e.get('method'),e.get('player_ids')
        key=(team,e.get('quarter'),e.get('clock'))
        if (team not in teams or method not in ('pass','run') or not isinstance(ids,list)
                or len(ids)!=(2 if method=='pass' else 1) or len(set(ids))!=len(ids)
                or any(pid not in by_id or by_id[pid]['team']!=team for pid in ids)
                or type(e.get('quarter')) is not int or not 1<=e['quarter']<=5
                or not isinstance(e.get('clock'),str) or ':' not in e['clock']
                or key in two_point_keys):
            raise ValueError('Unverified two-point conversion attribution')
        two_point_keys.add(key)
    defensive_types={'interception_return_touchdown':6,'defensive_fumble_return_touchdown':6,'safety':2}
    defensive_keys=set()
    for e in defense:
        team,kind,points=e.get('team'),e.get('type'),e.get('points')
        key=(team,e.get('quarter'),e.get('clock'))
        if (team not in teams or kind not in defensive_types or type(points) is not int
                or points!=defensive_types[kind] or type(e.get('quarter')) is not int
                or not 1<=e['quarter']<=5 or not isinstance(e.get('clock'),str)
                or ':' not in e['clock'] or key in defensive_keys):
            raise ValueError('Unverified defensive scoring attribution')
        defensive_keys.add(key)
    for team in teams:
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
        if any(scoring[k]!=[] for k in ('return_touchdowns','offensive_fumble_recovery_touchdowns')):
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
        points+=2*sum(e['team']==team for e in conversions)
        points+=sum(e['points'] for e in defense if e['team']==team)
        if points!=data['away_score' if team==data['away'] else 'home_score']:raise ValueError('Incomplete final scoring')
    return rows

def fantasy(p,scoring=None):
    conversions=(scoring or {}).get('two_point_conversions',[])
    bonus=2*sum(p['player_id'] in e['player_ids'] for e in conversions)
    return round(.04*p['passing_yards']+4*p['passing_tds']-p['passing_interceptions']+
      .1*p['rushing_yards']+6*p['rushing_tds']+p['receptions']+
      .1*p['receiving_yards']+6*p['receiving_tds']-p['fumbles_lost']+bonus,8)

def supplement(boxroot,schedule,boxes):
    # Validate every supplied game before changing the caller's outcome map.
    staged={}
    for game in [GAME,*REVIEWED_GAMES]:
        path=Path(boxroot)/('verified_gamebook_'+game+'.json')
        if not path.exists():continue
        reviewed=json.loads(path.read_text())
        rows=validate(reviewed,schedule.get(game))
        spec=reviewed_spec(game)
        old=boxes.get(game,{})
        for p in rows:
            previous=old.get(p['player_id'],{})
            if previous and (previous.get('team')!=p['team'] or previous.get('player')!=p['player']):
                raise ValueError('Gamebook player identity conflicts with published source')
            for field in FIELDS:
                if previous.get(field) is not None and float(previous[field])!=p[field]:
                    raise ValueError('Gamebook conflicts with published final stats: '+field)
        updated=dict(old)
        for p in rows:
            if p['player_id'] in spec.get('excluded_player_ids',[]):continue
            updated[p['player_id']]={**p,'verified_gamebook_sha256':spec['sha'],
                'verified_gamebook_game_id':game,'verified_prizepicks_full_ppr':fantasy(p,reviewed['verified_game_scoring'])}
            if game!=GAME:
                # New recovery is scoped to standard picks only. Historical
                # alternate-tier research must retain its prior outcome inputs.
                updated[p['player_id']]['standard_recovery_only']=True
                updated[p['player_id']]['excluded_recovery_targets']=sorted(set(spec.get('excluded_targets',[])) | set(p.get('unverified_market_targets',[])))
                # Only exact, hash-pinned complete-allocation proof may release
                # this player's TGT hold. Never release another market or tier.
                if p.get('verified_zero_targets'):
                    updated[p['player_id']]['excluded_recovery_targets']=[
                        t for t in updated[p['player_id']]['excluded_recovery_targets'] if t!='TGT']
                updated[p['player_id']]['prior_verified_boxscore']=old.get(p['player_id'])
        staged[game]=updated
    boxes.update(staged)
