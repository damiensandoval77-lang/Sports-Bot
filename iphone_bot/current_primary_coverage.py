"""Read-only current offer coverage, separate from immutable archive gaps.

Only authentic two-sided standard offers for this slate's future games count.
Neither research previews nor short-history baselines satisfy primary coverage.
"""
import datetime as dt
import math
from collections import defaultdict
from .multimarket_forecast_ledger import valid, utc

STATS={'Points':'PTS','Rebounds':'REB','Assists':'AST','Points Rebounds Assists':'PRA'}

def key(row):
    return (str(row['player']).casefold(),row['team'],row['game'],utc(row['start']),row['stat'],float(row['line']))

def evaluate(feed, ledger, games, now):
    result={'status':'UNVERIFIED','checked_at':now.isoformat(),'source_generated_at':feed.get('source_generated_at'),
            'verified_current_offers':0,'matched_primary_offers':0,'missing_primary_offers':0,
            'games':[],'issues':[],'scope':'CURRENT_UPCOMING_STANDARD_OFFERS_ONLY',
            'research_and_provisional_count_as_primary':False}
    try:
        source=utc(feed['source_generated_at']);updated=utc(feed['updated_at'])
        if (feed.get('source')!='AUTHENTIC_PRIZEPICKS_PICKEM_NO_ODDS' or
            feed.get('status')!='FRESH_AUTHENTIC_PRIZEPICKS_LINES' or feed.get('is_live') is not True or
            not source<=updated<=now+dt.timedelta(seconds=120) or now-source>dt.timedelta(hours=6) or
            ledger.get('status')!='FROZEN_NEW_AI_ALL_MARKET'):
            raise ValueError('invalid inputs')
        fixtures={(g['game'],utc(g['start'])) for g in games if utc(g['start'])>now}
        frozen=set()
        for row in ledger.get('records',[]):
            if valid(row):frozen.add(key(row))
        grouped=defaultdict(list)
        for p in feed.get('picks',[]):
            if not isinstance(p,dict) or p.get('stat') not in STATS or p.get('pickem_tier')!='standard':continue
            if (p.get('game'),utc(p.get('start'))) not in fixtures:continue
            if p.get('source')!='independent_prizepicksapi_com' or p.get('direction') not in ('More','Less'):continue
            line=float(p['line']);observed=utc(p['market_updated'])
            if not math.isfinite(line) or not 0<=line<=100 or not observed<=updated or not observed<utc(p['start']):continue
            if not p.get('player') or not p.get('team'):continue
            row={**p,'stat':STATS[p['stat']]}
            grouped[key(row)[:-1]].append(row)
        selected=[]
        for rows in grouped.values():
            if len({float(r['line']) for r in rows})!=1 or {r['direction'] for r in rows}!={'More','Less'}:continue
            selected.append(rows[0])
        for game,start in sorted(fixtures):
            rows=[r for r in selected if r['game']==game and utc(r['start'])==start]
            missing=[{'player':r['player'],'team':r['team'],'stat':r['stat'],'line':r['line']} for r in rows if key(r) not in frozen]
            result['games'].append({'game':game,'start':start.isoformat(),'verified_current_offers':len(rows),
                                    'matched_primary_offers':len(rows)-len(missing),'missing_primary_offers':len(missing),'missing':missing})
            if not rows:result['issues'].append(game+': NO_CURRENT_VERIFIED_STANDARD_OFFERS')
        for field in ('verified_current_offers','matched_primary_offers','missing_primary_offers'):
            result[field]=sum(g[field] for g in result['games'])
        result['status']='INCOMPLETE' if result['issues'] or result['missing_primary_offers'] else 'COMPLETE'
    except (KeyError,ValueError,TypeError,OverflowError):
        result['issues'].append('CURRENT_SOURCE_OR_PRIMARY_LEDGER_UNVERIFIED')
    return result
