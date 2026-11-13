"""Verified, partial ESPN final-stat supplement while nflverse weekly data lags.

No live observations, inferred zeros, DNPs or fantasy scores are settlements.
Only exact final event + scheduled scores + ESPN-ID/GSIS-ID registry joins pass.
"""
import csv
import hashlib
import io
import math
import json
import re
import unicodedata
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.request import Request, urlopen
from fetch_nfl_live import load, parse_summary, canonical_team, SUMMARY, WEEK_SCOREBOARD

ROOT = Path('docs/nfl/data')
REGISTRY = 'https://github.com/nflverse/nflverse-data/releases/download/players/players.csv'
FIELDS = {'PASS_CMP':'completions','PASS_ATT':'attempts','PASS_YDS':'passing_yards',
          'PASS_TD':'passing_tds','PASS_INT':'passing_interceptions','RUSH_ATT':'carries',
          'RUSH_YDS':'rushing_yards','RUSH_TD':'rushing_tds','REC':'receptions',
          'REC_YDS':'receiving_yards','REC_TD':'receiving_tds','TGT':'targets'}

def utc(value):
    d = datetime.fromisoformat(str(value).replace('Z','+00:00'))
    if not d.tzinfo: raise ValueError('Naive event timestamp')
    return d.astimezone(timezone.utc)

def name(value):
    return re.sub('[^a-z0-9]', '', unicodedata.normalize('NFKD',str(value)).encode('ascii','ignore').decode().lower())

def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def identities(text):
    result = {}
    registry_sha256=hashlib.sha256(text.encode()).hexdigest()
    for r in csv.DictReader(io.StringIO(text)):
        eid, gid = str(r.get('espn_id') or '').strip(), str(r.get('gsis_id') or '').strip()
        if not eid or not gid: continue
        if not re.fullmatch(r'\d+',eid) or not re.fullmatch(r'00-\d+',gid): continue
        if eid in result and result[eid]['gsis_id'] != gid: raise ValueError('Ambiguous ESPN/GSIS registry')
        r['registry_sha256']=registry_sha256
        result[eid] = r
    if not result: raise ValueError('Empty identity registry')
    return result

def build_game(payload, scheduled, registry, fetched_at):
    header = payload.get('header') or {}
    competitions = header.get('competitions') or []
    if len(competitions)!=1: raise ValueError('Ambiguous final competition')
    c = competitions[0]
    event = str(header.get('id') or '')
    if not event.isdigit() or str(c.get('id')) != event: raise ValueError('Event ID mismatch')
    season = header.get('season') or {}
    if season.get('year')!=2026 or season.get('type')!=2: raise ValueError('Wrong season')
    week=header.get('week')
    if isinstance(week,dict): week=week.get('number')
    if week!=int(scheduled['week']): raise ValueError('Wrong week')
    status = (c.get('status') or {}).get('type') or {}
    if status.get('completed') is not True or status.get('state')!='post' or not c.get('boxscoreAvailable'):
        raise ValueError('Source is not a completed final boxscore')
    if scheduled.get('status')!='final' or abs((utc(c.get('date'))-utc(scheduled['kickoff_utc'])).total_seconds())>60:
        raise ValueError('Final schedule/kickoff mismatch')
    sides = c.get('competitors') or []
    if len(sides)!=2: raise ValueError('Wrong competitor count')
    for role in ('away','home'):
        matches=[s for s in sides if s.get('homeAway')==role]
        if len(matches)!=1: raise ValueError('Missing scheduled side')
        s=matches[0]
        if canonical_team((s.get('team') or {}).get('abbreviation'))!=canonical_team(scheduled[role]):
            raise ValueError('Final team mismatch')
        if float(s.get('score'))!=float(scheduled[role+'_score']): raise ValueError('Final score mismatch')
    teams={canonical_team(scheduled[k]) for k in ('away','home')}
    raw_sides=(payload.get('boxscore') or {}).get('players') or []
    if len(raw_sides)!=2 or {canonical_team((s.get('team') or {}).get('abbreviation')) for s in raw_sides}!=teams:
        raise ValueError('Boxscore team mismatch')
    # Reject duplicate statistical rows rather than let a parser overwrite them.
    seen=set()
    for side in raw_sides:
        for group in side.get('statistics',[]):
            if group.get('name') not in ('passing','rushing','receiving'): continue
            for entry in group.get('athletes',[]):
                key=(side['team']['abbreviation'],group['name'],str((entry.get('athlete') or {}).get('id')))
                if key in seen: raise ValueError('Duplicate player category')
                seen.add(key)
    rows=[]; unknown=[]
    for p in parse_summary(payload,scheduled['away'],scheduled['home']):
        identity=registry.get(p['espn_id'])
        if not identity or name(identity['display_name'])!=name(p['player']):
            unknown.append({'espn_id':p['espn_id'],'player':p['player'],'team':p['team']})
            continue
        row={'player_id':identity['gsis_id'],'espn_id':p['espn_id'],'player':p['player'],
             'team':next(scheduled[k] for k in ('away','home') if canonical_team(scheduled[k])==p['team']),
             'position':identity.get('position') or ''}
        row.update({field:p['stats'].get(stat) for stat,field in FIELDS.items()})
        row['fumbles_lost']=None
        rows.append(row)
    if {canonical_team(r['team']) for r in rows}!=teams or len({r['player_id'] for r in rows})!=len(rows):
        raise ValueError('Incomplete or ambiguous verified player identities')
    game={k:scheduled[k] for k in ('game_id','week','home','away','home_score','away_score','kickoff_utc')}
    game.update(source='ESPN_COMPLETED_EXPLICIT_STATS', source_url=SUMMARY.format(event=event),
                espn_event_id=event, verified_final=True, fetched_at=fetched_at,
                identity_source=REGISTRY, identity_registry_observed_at=fetched_at, identity_registry_sha256=next(iter(registry.values()))['registry_sha256'], partial_stats=True, unknown_players=unknown,
                players=rows, source_payload_sha256=digest(payload))
    game['integrity_sha256']=digest(game)
    return game

def validate_stored(game, scheduled):
    value=dict(game); checksum=value.pop('integrity_sha256',None)
    if checksum!=digest(value): raise ValueError('Final supplement integrity mismatch')
    if game.get('source')!='ESPN_COMPLETED_EXPLICIT_STATS' or game.get('verified_final') is not True or game.get('partial_stats') is not True:
        raise ValueError('Unverified final supplement')
    if game.get('source_url')!=SUMMARY.format(event=game.get('espn_event_id')) or game.get('identity_source')!=REGISTRY:
        raise ValueError('Unattributed final supplement')
    if not scheduled or scheduled.get('status')!='final' or any(game.get(k)!=scheduled.get(k) for k in ('game_id','week','home','away','home_score','away_score','kickoff_utc')):
        raise ValueError('Final supplement schedule mismatch')
    if utc(game['fetched_at'])<utc(scheduled['kickoff_utc']): raise ValueError('Invalid final observation time')
    rows=game.get('players') or []
    if not rows or len({p.get('player_id') for p in rows})!=len(rows): raise ValueError('Duplicate or missing final players')
    if any(not p.get('player_id') or not p.get('espn_id') or not p.get('player') or p.get('team') not in (scheduled['away'],scheduled['home']) for p in rows):
        raise ValueError('Invalid final player identity')
    if any(not re.fullmatch(r'00-\d+',p['player_id']) or not str(p['espn_id']).isdigit() for p in rows): raise ValueError('Invalid source IDs')
    if any(v is not None and (isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v)) for p in rows for k in FIELDS.values() for v in [p.get(k)]): raise ValueError('Invalid final numeric stats')
    return True

def run(root=ROOT, now=None, fetch=load, registry_text=None):
    now=now or datetime.now(timezone.utc)
    schedule=json.loads((root/'schedule_2026.json').read_text())
    if schedule.get('season')!=2026 or len(schedule.get('games',[]))!=272: raise ValueError('Incomplete schedule')
    out=root/'boxscores/espn_verified_finals.json'
    old=json.loads(out.read_text()) if out.exists() else {'season':2026,'games':[]}
    games={g['game_id']:g for g in old['games']}
    scheduled={g['game_id']:g for g in schedule['games']}
    for gid,g in games.items(): validate_stored(g,scheduled.get(gid))
    manifest=json.loads((root/'boxscores/manifest.json').read_text())
    covered=set(manifest.get('game_ids',[]))
    needed=[g for g in scheduled.values() if g.get('status')=='final' and g['game_id'] not in covered and
            timedelta(0)<=now-utc(g['kickoff_utc'])<=timedelta(days=3)]
    if not needed: print('No recent final game needs supplemental observations');return
    if registry_text is None:
        with urlopen(Request(REGISTRY,headers={'User-Agent':'DamesPicks-FinalVerification'}),timeout=60) as rsp:
            registry_text=rsp.read().decode()
    registry=identities(registry_text)
    errors=[]
    for week in sorted({g['week'] for g in needed}):
        board=fetch(WEEK_SCOREBOARD.format(season=2026,week=week))
        for g in [x for x in needed if x['week']==week]:
            candidates=[e for e in board.get('events',[]) if abs((utc(e['date'])-utc(g['kickoff_utc'])).total_seconds())<=60 and
                        {canonical_team((s.get('team') or {}).get('abbreviation')) for s in (e.get('competitions') or [{}])[0].get('competitors',[])}=={canonical_team(g['home']),canonical_team(g['away'])}]
            if len(candidates)!=1:
                errors.append(g['game_id']+': no unique scheduled event');continue
            try:
                payload=fetch(SUMMARY.format(event=candidates[0]['id']))
                record=build_game(payload,g,registry,now.isoformat())
                previous=games.get(g['game_id'])
                if previous and previous['players']!=record['players']:
                    raise ValueError('Changed previously verified final stats; review required')
                games[g['game_id']]=previous or record
            except (ValueError,KeyError,TypeError) as e:errors.append(g['game_id']+': '+str(e))
    content=json.dumps({'season':2026,'scope':'PARTIAL_EXPLICIT_FINAL_STATS_NO_ZERO_INFERENCE','games':sorted(games.values(),key=lambda g:g['game_id'])},sort_keys=True,indent=2)+'\n'
    if not out.exists() or out.read_text()!=content:
        out.parent.mkdir(parents=True,exist_ok=True);temp=out.with_suffix('.tmp');temp.write_text(content);temp.replace(out)
    print('Verified final supplements:',len(games),'games;',len(errors),'unresolved:',errors)
    if errors: raise RuntimeError('; '.join(errors))

if __name__=='__main__':run()
