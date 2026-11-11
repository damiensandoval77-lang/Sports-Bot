"""Check whether real deployed browser can read independent live JSON providers.

No app mutations, no odds APIs, no player prediction or grade changes.
Cross-origin fetch is tested from actual GitHub Pages origin in Chromium.
"""
import json
from datetime import datetime, timezone
from playwright.sync_api import sync_playwright

URL="https://damiensandoval77-lang.github.io/Sports-Bot/dames-picks/"
ENDPOINTS={
 "NBA_CDN":"https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json",
 "NBA_S3":"https://nba-prod-us-east-1-mediaops-stats.s3.amazonaws.com/NBA/liveData/scoreboard/todaysScoreboard_00.json",
 "ESPN":"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates=20261110&limit=100",
 "GITHUB_RAW":"https://raw.githubusercontent.com/damiensandoval77-lang/Sports-Bot/main/docs/live_player_tracking.json",
 "GITHUB_API":"https://api.github.com/repos/damiensandoval77-lang/Sports-Bot/contents/docs/live_player_tracking.json?ref=main",
 "GITHUB_PAGES":"https://damiensandoval77-lang.github.io/Sports-Bot/live_player_tracking.json",
}

def main():
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=["--no-sandbox"])
        try:
            page=browser.new_page(viewport={"width":390,"height":844})
            page.goto(URL,wait_until="domcontentloaded",timeout=45000)
            result=page.evaluate("""async urls => {
              const out={};
              await Promise.all(Object.entries(urls).map(async ([name,url])=>{
                const ctl=new AbortController();
                const timer=setTimeout(()=>ctl.abort(),9000);
                try{
                  const res=await fetch(url,{cache:"no-store",signal:ctl.signal});
                  const status=res.status;
                  if(!res.ok){out[name]={ok:false,status};return}
                  const data=await res.json();
                  const raw=data?.scoreboard?.games||data?.events||data?.games;
                  const githubEncoded=data?.encoding==="base64"&&typeof data?.content==="string";
                  out[name]={ok:Array.isArray(raw)||githubEncoded,status,
                      game_count:Array.isArray(raw)?raw.length:null,
                      has_game_ids:Array.isArray(raw)&&raw.some(x=>x?.gameId||x?.id),
                      data_timestamp:data?.captured_at||data?.generated_at||null,
                      github_api_blob:githubEncoded};
                }catch(e){out[name]={ok:false,error_name:e?.name||"FETCH_ERROR",
                                     error:String(e?.message||e).slice(0,120)}}
                finally{clearTimeout(timer)}
              }));
              return out;
            }""",ENDPOINTS)
            print("BROWSER_PROVIDER_CORS",json.dumps({
                "checked_at":datetime.now(timezone.utc).isoformat(),
                "pages_origin":URL,"sources":result},sort_keys=True))
        finally:browser.close()

if __name__=="__main__":main()
