/**
 * Zero-credit The Odds API credential probe, executed only from Cloudflare Cron.
 * Official free endpoint: GET https://api.the-odds-api.com/v4/sports/
 * Authentication uses x-api-key header, never a URL or a browser response.
 *
 * This does NOT enable the paid odds collector, verify availability of
 * PrizePicks props, test game quotes or grade an AI pick.
 */
export const FREE_SPORTS_ENDPOINT="https://api.the-odds-api.com/v4/sports/";
export const MIN_PROBE_INTERVAL_MS=6*60*60*1000;
const JOB="odds-api-free-key-check";
const iso=ms=>new Date(ms).toISOString();
const hasKey=env=>typeof env?.ODDS_API_KEY==="string" && env.ODDS_API_KEY.trim().length>=12;
const numericHeader=(response,name)=>{
  const value=response.headers?.get?.(name);
  if(value===null || value===undefined || !/^\d{1,10}$/.test(String(value)))return null;
  return Number(value);
};
function parseDetail(row){
  try{
    const detail=JSON.parse(row?.detail||"{}");
    return {
      state:detail.state||"not_checked",
      http_status:Number.isSafeInteger(detail.http_status)?detail.http_status:null,
      last_call_credits:detail.last_call_credits??null,
      quota_remaining:detail.quota_remaining??null,
      nba_active:detail.nba_active??null,
      nfl_active:detail.nfl_active??null,
      sports_count:detail.sports_count??null
    };
  }catch(_){return {state:"invalid_saved_receipt",http_status:null,last_call_credits:null,quota_remaining:null,nba_active:null,nfl_active:null,sports_count:null}}
}
/** Read-only endpoint. Never calls The Odds API from an HTTP request. */
export async function freeKeyProbeStatus(env){
  const configured=hasKey(env);
  if(typeof env?.DB?.prepare!=="function")
    return {status:"database_not_connected",secret_configured:configured,paid_collection:"disabled"};
  try{
    const row=await env.DB.prepare(
      "SELECT scheduled_at,completed_at,outcome,detail FROM scheduler_runs WHERE job=? ORDER BY run_id DESC LIMIT 1"
    ).bind(JOB).first();
    if(!row)return {
      status:configured?"awaiting_free_check":"secret_not_configured",
      secret_configured:configured,probe_time:null,paid_collection:"disabled",
      key_authentication_verified:false
    };
    const details=parseDetail(row);
    const at=Date.parse(row.completed_at||"");
    const recent=Number.isFinite(at)&&Date.now()-at>=0&&Date.now()-at<8*60*60*1000;
    const authenticated=configured&&recent&&row.outcome==="success"&&details.state==="authenticated"&&details.last_call_credits===0;
    return {
      status:configured?(recent?details.state:"stale_check"):"secret_not_configured",
      secret_configured:configured,
      key_authentication_verified:authenticated,
      probe_time:row.completed_at||null,
      http_status:details.http_status,
      last_call_credits:details.last_call_credits,
      quota_remaining:details.quota_remaining,
      nba_active:details.nba_active,
      nfl_active:details.nfl_active,
      sports_count:details.sports_count,
      paid_collection:"disabled",
      note:"Free sports discovery only; does not verify PrizePicks/Underdog line access or activate paid quotes."
    };
  }catch(_){return {status:"database_unavailable",secret_configured:configured,paid_collection:"disabled"}}
}
export async function probeFreeSportsEndpoint(key,{fetcher=fetch,now=Date.now(),timeoutMs=8000}={}){
  if(typeof key!=="string"||key.trim().length<12)
    return {state:"secret_not_configured",http_status:null,last_call_credits:null,quota_remaining:null,nba_active:null,nfl_active:null,sports_count:null};
  const controller=new AbortController();
  const timer=setTimeout(()=>controller.abort(),timeoutMs);
  try{
    const res=await fetcher(FREE_SPORTS_ENDPOINT,{
      method:"GET",
      headers:{"x-api-key":key.trim(),"accept":"application/json"},
      cache:"no-store",
      signal:controller.signal
    });
    const last=numericHeader(res,"x-requests-last");
    const remaining=numericHeader(res,"x-requests-remaining");
    const output={
      state:"request_failed",
      http_status:res.status,
      last_call_credits:last,
      quota_remaining:remaining,
      nba_active:null,nfl_active:null,sports_count:null
    };
    if(!res.ok){
      output.state=res.status===401||res.status===403?"authentication_rejected":
        res.status===429?"rate_limited":"provider_http_error";
      return output;
    }
    const sports=await res.json();
    if(!Array.isArray(sports))return {...output,state:"unexpected_response"};
    output.sports_count=sports.length;
    output.nba_active=sports.some(s=>s.key==="basketball_nba"&&s.active===true);
    output.nfl_active=sports.some(s=>s.key==="americanfootball_nfl"&&s.active===true);
    // Docs promise this endpoint costs 0 credits; missing/positive cost
    // headers require a manual review, never a false "0 credits" assertion.
    output.state=last===0?"authenticated":"unverified_request_cost";
    return output;
  }catch(_){
    return {state:"network_or_timeout",http_status:null,last_call_credits:null,
      quota_remaining:null,nba_active:null,nfl_active:null,sports_count:null};
  }finally{clearTimeout(timer)}
}
/**
 * Every 15-minute Cron can invoke this helper, but it performs at most one
 * provider request per 6 hours. No paid event odds endpoint is ever called.
 */
export async function probeFreeKeyOnCron(env,{fetcher=fetch,now=Date.now()}={}){
  if(typeof env?.DB?.prepare!=="function")return {status:"skipped",reason:"db_missing"};
  // The free probe never alters flags, even if an owner later opts in.
  const last=await env.DB.prepare(
    "SELECT completed_at,outcome FROM scheduler_runs WHERE job=? ORDER BY run_id DESC LIMIT 1"
  ).bind(JOB).first();
  const configured=hasKey(env);
  if(last?.completed_at){
    const age=now-Date.parse(last.completed_at);
    const interval=last.outcome==="success" ? MIN_PROBE_INTERVAL_MS : 30*60*1000;
    // A newly entered key must be tested even if an earlier check saw no key.
    const needNewKeyProbe=last.outcome==="skipped" && configured;
    if(!needNewKeyProbe && Number.isFinite(age)&&age>=0&&age<interval)
      return {status:"skipped",reason:"recently_checked"};
  }
  const start=iso(now);
  const probe=configured?await probeFreeSportsEndpoint(env.ODDS_API_KEY,{fetcher,now}):
    {state:"secret_not_configured",http_status:null,last_call_credits:null,quota_remaining:null,
      nba_active:null,nfl_active:null,sports_count:null};
  const outcome=probe.state==="authenticated"?"success":
    probe.state==="secret_not_configured"?"skipped":"failure";
  // Persist only sanitized metadata; never store API keys, headers, or raw URLs.
  await env.DB.prepare(
    "INSERT INTO scheduler_runs(job,scheduled_at,completed_at,outcome,detail) VALUES(?,?,?,?,?)"
  ).bind(JOB,start,iso(Date.now()),outcome,JSON.stringify(probe).slice(0,1000)).run();
  return {status:probe.state,performed_request:configured,last_call_credits:probe.last_call_credits};
}
