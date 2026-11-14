"""One authorized bounded tennis schema probe; no recurring reads or activation."""
import datetime as dt
import json
import os
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
    print(json.dumps(result))

if __name__=='__main__':main()
