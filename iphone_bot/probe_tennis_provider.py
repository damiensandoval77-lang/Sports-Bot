"""One authorized bounded tennis schema probe; no recurring reads or activation."""
import datetime as dt
import json
import os
import math
from pathlib import Path
import urllib.error
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
REQUEST=ROOT/'docs/tennis/provider_probe_request.json'
OUTPUT=ROOT/'docs/tennis/provider_probe_status.json'
URL='https://prizepicksapi.com/api/v1/projections?league=TENNIS&status=active&tier=standard&limit=100'

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):
        raise urllib.error.HTTPError(URL, 302, 'Redirect refused', {}, None)


def summary(payload):
    if not isinstance(payload,dict) or not isinstance(payload.get('data'),list):
        raise ValueError('Invalid provider response')
    meta=payload.get('meta') or {}
    if not isinstance(meta,dict):raise ValueError('Invalid metadata')
    if meta.get('mode')!='live' or any(r.get('is_demo') is True for r in payload['data'] if isinstance(r,dict)):
        raise ValueError('Not authenticated live data')
    rows=payload['data']
    if len(rows)>100:
        raise ValueError('Provider exceeded row limit')
    shapes=[]
    for row in rows:
        if not isinstance(row,dict) or str(row.get('league','')).upper()!='TENNIS':
            raise ValueError('Unexpected league or record')
        event=row.get('event') or {}; player=row.get('player') or {}; fields=row.get('source_fields') or {}
        if not all(isinstance(o,dict) for o in [event,player,fields]):
            raise ValueError('Unexpected source shape')
        shapes.append({'keys':sorted(row),'event_keys':sorted(event),'player_keys':sorted(player),
            'source_field_keys':sorted(fields),
            'has_player_id':bool(player.get('id')),'has_player_name':bool(player.get('name')),
            'has_opponent':bool(event.get('opponent')),'has_start':bool(event.get('starts_at')),
            'has_surface':bool(event.get('surface') or fields.get('surface')),
            'has_tour':bool(event.get('tour') or fields.get('tour')),
            'has_best_of':bool(event.get('best_of') or fields.get('best_of')),
            'stat':(row.get('market') or {}).get('stat') if isinstance(row.get('market'),dict) else None})
    return {'provider_mode':meta.get('mode'),'source_status':meta.get('source_status'),
        'rows_returned':len(rows),'has_next_page':bool(meta.get('next_cursor')),
        'complete_board_claimed':False,'shapes':shapes}


def normalized_board(payload, captured_at):
    """Minimal in-product quote display; never a raw feed/bulk history export."""
    meta=payload.get('meta') or {}
    out={'schema_version':'tennis_board_v1','sport':'TENNIS',
        'generated_at':captured_at,'source':'independent_prizepicksapi_com',
        'provider_mode':meta.get('mode'),'source_status':meta.get('source_status'),'is_demo':False,
        'complete_pagination':meta.get('next_cursor') is None,
        'model_status':'WITHHELD','blockers':['Tennis model context and probabilities not validated'],
        'quotes':[]}
    if meta.get('mode')!='live' or meta.get('source_status')!='fresh':return out
    now=dt.datetime.fromisoformat(captured_at)
    allowed={'Total Games','Total Games Won','Total Sets','Total Tie Breaks','Aces','Double Faults','Break Points Won','Fantasy Score'}
    for row in payload['data']:
        try:
            player=row.get('player') or {};event=row.get('event') or {};market=row.get('market') or {};fields=row.get('source_fields') or {}
            if str(row.get('league','')).upper()!='TENNIS' or row.get('is_demo') is True or row.get('status')!='active':continue
            if any(obj.get(k) is True for obj in (row,fields) for k in ('is_live','in_game','is_promo')):continue
            if market.get('stat') not in allowed or str(market.get('period','')).lower() not in ('full game','full match','full_game','full_match'):continue
            if fields.get('projection_type') != 'Single Stat':continue
            line=row.get('line')
            if isinstance(line,bool) or not isinstance(line,(int,float)) or not math.isfinite(line) or line<0:continue
            sides={s['side']:s for s in row.get('selections',[]) if isinstance(s,dict) and s.get('side') in ('more','less')}
            if any(sides.get(k,{}).get('available') is not True or sides.get(k,{}).get('tier')!='standard' for k in ('more','less')):continue
            start=dt.datetime.fromisoformat(event['starts_at'].replace('Z','+00:00'))
            observed=dt.datetime.fromisoformat(row['observed_at'].replace('Z','+00:00'))
            if not start.tzinfo or not observed.tzinfo or not observed<=now<start or now-observed>dt.timedelta(minutes=30):continue
            fixture=row.get('fixture_id') or event.get('id')
            if not all([row.get('id'),player.get('id'),player.get('name'),fixture,event.get('opponent')]):continue
            if not isinstance(event['opponent'],str):continue
            out['quotes'].append({'id':str(row['id']),'player_id':str(player['id']),
                'fixture_id':str(fixture),'player':player['name'],'opponent':event['opponent'],
                'stat':market['stat'],'period':'full_match','line':line,'status':'active','is_demo':False,'is_combo':False,
                'tier':'standard','more_tier':'standard','less_tier':'standard',
                'more_available':True,'less_available':True,'observed_at':observed.isoformat(),
                'captured_at':captured_at,'starts_at':start.isoformat()})
        except (KeyError,TypeError,ValueError,AttributeError):continue
    out['accepted_quote_count']=len(out['quotes'])
    out['rejected_quote_count']=len(payload['data'])-len(out['quotes'])
    return out


def probe(key,open_request=None):
    out={'checked_at':dt.datetime.now(dt.timezone.utc).isoformat(),
        'requested_rows':100,'documented_max_credits':3,'maximum_requests':1,'ongoing_polling_enabled':False,
        'raw_records_public':False,'status':'NOT_RUN'}
    if not key:return {**out,'status':'MISSING_GITHUB_SECRET'},None
    request=urllib.request.Request(URL,headers={'Authorization':'Bearer '+key,
        'Accept':'application/json','X-User-Request':'One bounded tennis fixture schema probe for authorized Sports-Bot integration'})
    opener=open_request or urllib.request.build_opener(NoRedirect()).open
    try:
        with opener(request,timeout=25) as reply:
            for header,name in [('X-Credits-Cost','credits_cost'),('X-Credits-Remaining','remaining_header')]:
                try:out[name]=int(reply.headers.get(header))
                except (TypeError,ValueError):out[name]=None
            raw=reply.read(1000001)
            if len(raw)>1000000:raise ValueError('Response size limit')
            payload=json.loads(raw)
            return {**out,**summary(payload),'status':'PROBE_COMPLETE'},payload
    except urllib.error.HTTPError as exc:
        return {**out,'status':'HTTP_ERROR','http_status':exc.code,'retried':False},None
    except (ValueError,TypeError,OSError,TimeoutError) as exc:
        return {**out,'status':'PROBE_FAILED','error_type':type(exc).__name__,'retried':False},None


def main():
    request=json.loads(REQUEST.read_text())
    request_id=request['request_id']
    previous=json.loads(OUTPUT.read_text()) if OUTPUT.exists() else {}
    if (previous.get('request_id') != request_id
        or previous.get('status') != 'CLAIMED_NO_RETRY'
        or previous.get('claim_token') != os.getenv('TENNIS_PROBE_CLAIM')
        or not os.getenv('TENNIS_PROBE_CLAIM')):
        print('No valid one-time durable claim; no provider call')
        return
    result,raw=probe(os.getenv('PRIZEPICKS_API_KEY','').strip())
    result['request_id']=request_id
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    OUTPUT.write_text(json.dumps(result,indent=2)+'\n')
    if raw is not None:
        board=normalized_board(raw,result['checked_at'])
        (ROOT/'docs/tennis_board.json').write_text(json.dumps(board,indent=2)+'\n')
    print(json.dumps(result))

if __name__=='__main__':main()
