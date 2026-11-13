"""Standalone, read-only NBA live player feed for an always-on Python host.

Serves existing tracker JSON from an in-memory 35-second ESPN poll, with
per-game observations, explicit coverage, and no prediction or betting secrets.
Run: python -m iphone_bot.live_tracker_service
Requires an external always-on host; this process is NOT launched by Pages.
"""
import json
import os
import threading
import time
from datetime import datetime,timezone
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

try:
    from .publish_live_tracker_feed import build,get
except ImportError:
    from publish_live_tracker_feed import build,get

ET=ZoneInfo("America/New_York")
POLL_SECONDS=max(20,min(90,int(os.environ.get("LIVE_POLL_SECONDS","35"))))
ALLOWED_ORIGIN=os.environ.get("LIVE_CORS_ORIGIN","https://damiensandoval77-lang.github.io")
STATE={"payload":None,"last_error":None,"last_attempt":None}
LOCK=threading.RLock()

def collect(previous=None,request=get,now=None):
    now=now or datetime.now(timezone.utc)
    date=now.astimezone(ET).strftime("%Y%m%d")
    board=request("/scoreboard?dates="+date+"&limit=100")
    summaries={}
    failures=[]
    for e in board.get("events",[]):
        if e.get("status",{}).get("type",{}).get("state") not in ("in","post"):
            continue
        event_id=str(e.get("id",""))
        if not event_id.isdecimal():continue
        try:summaries[event_id]=request("/summary?event="+event_id)
        except Exception as error:failures.append({"event_id":event_id,"reason":type(error).__name__})
    result=build(now,board,summaries,previous)
    result["errors"].extend(failures)
    result["polling_interval_seconds"]=POLL_SECONDS
    result["delivery"]="ALWAYS_ON_SERVICE_WHEN_HOSTED"
    return result

def poll_forever(request=get,stop=None):
    while not (stop and stop.is_set()):
        at=datetime.now(timezone.utc)
        with LOCK:
            prior=STATE["payload"]
            STATE["last_attempt"]=at.isoformat()
        try:
            data=collect(prior,request,at)
            with LOCK:
                STATE["payload"]=data
                STATE["last_error"]=None
        except Exception as error:
            with LOCK:STATE["last_error"]=type(error).__name__
        if stop:
            if stop.wait(POLL_SECONDS):break
        else:time.sleep(POLL_SECONDS)

class Handler(BaseHTTPRequestHandler):
    def respond(self,code,payload):
        raw=json.dumps(payload,separators=(",",":"),ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type","application/json; charset=utf-8")
        self.send_header("Cache-Control","no-store, max-age=0")
        self.send_header("Access-Control-Allow-Origin",ALLOWED_ORIGIN)
        self.send_header("Vary","Origin")
        self.send_header("X-Content-Type-Options","nosniff")
        self.send_header("Content-Length",str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)
    def do_GET(self):
        path=urlsplit(self.path).path
        with LOCK:
            data=STATE["payload"]
            error=STATE["last_error"]
            attempt=STATE["last_attempt"]
        if path=="/healthz":
            age=(datetime.now(timezone.utc)-
                 datetime.fromisoformat(data["captured_at"])).total_seconds() if data else None
            healthy=data is not None and age is not None and age<2*POLL_SECONDS+30
            self.respond(200 if healthy else 503,{"status":"HEALTHY" if healthy else "DEGRADED",
                "last_attempt":attempt,"last_success":data.get("captured_at") if data else None,
                "age_seconds":round(age,1) if age is not None else None,
                "coverage":data.get("coverage") if data else None,
                "last_error_type":error})
        elif path=="/live_player_tracking.json":
            if data is None:
                self.respond(503,{"status":"NO_VERIFIED_ESPN_DATA","last_error_type":error})
                return
            self.respond(200,data)
        else:self.respond(404,{"error":"Not found"})
    def log_message(self,format,*args):
        return

def main():
    port=int(os.environ.get("PORT","8080"))
    thread=threading.Thread(target=poll_forever,daemon=True)
    thread.start()
    server=ThreadingHTTPServer(("0.0.0.0",port),Handler)
    print("NBA live tracker service listening",port,"poll",POLL_SECONDS,flush=True)
    try:server.serve_forever(poll_interval=.25)
    finally:server.server_close()

if __name__=="__main__":main()
