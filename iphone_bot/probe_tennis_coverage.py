"""Single zero-credit provider coverage read; no quotes, retries or activation."""
import datetime as dt
import json
import os
from pathlib import Path
import urllib.request
import urllib.error

URL = 'https://prizepicksapi.com/api/v1/coverage'
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError('Redirect refused')

def safe(value, secret):
    """Bound metadata and remove any accidental credential echo before artifact output."""
    raw = json.dumps(value)
    if secret and secret in raw:
        raise ValueError('Credential echo refused')
    if len(raw) > 1000000:
        raise ValueError('Oversize metadata')
    return value

def main():
    key = os.environ.get('PRIZEPICKS_API_KEY', '')
    if not key:
        raise SystemExit('Configured provider key missing; no request made')
    req = urllib.request.Request(URL, headers={'Authorization': 'Bearer '+key,
        'X-User-Request': 'Inspect tennis coverage metadata without requesting paid data'})
    result = {'checked_at': dt.datetime.now(dt.timezone.utc).isoformat(),
              'endpoint': URL, 'quotes_requested': False, 'live_ready': False}
    try:
        with urllib.request.build_opener(NoRedirect).open(req,timeout=30) as response:
            raw = response.read(1000001)
            if len(raw)>1000000: raise ValueError('Oversize metadata')
            payload = safe(json.loads(raw),key)
            result.update(status='RECEIVED',http_status=response.status,
                          credits_cost='0' if response.headers.get('X-Credits-Cost') == '0' else 'UNVERIFIED',
                          coverage=payload)
    except urllib.error.HTTPError as exc:
        result.update(status='HTTP_ERROR',http_status=exc.code)
    except Exception:
        result.update(status='INVALID_OR_UNAVAILABLE')
    Path('tennis-coverage-status.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='coverage'}))
if __name__ == '__main__': main()
