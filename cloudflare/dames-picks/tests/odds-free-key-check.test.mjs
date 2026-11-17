import test from "node:test";
import assert from "node:assert/strict";
import worker from "../src/worker.js";
import {isCollectionEnabled} from "../src/odds-collector.js";
import {FREE_SPORTS_ENDPOINT,probeFreeSportsEndpoint,probeFreeKeyOnCron,freeKeyProbeStatus} from "../src/odds-free-key-check.js";

const KEY="example_credential_only_for_tests_123";
const sports=[
 {key:"basketball_nba",active:true,title:"NBA"},
 {key:"americanfootball_nfl",active:true,title:"NFL"},
 {key:"soccer_epl",active:true,title:"EPL"}
];
function apiReply({status=200,body=sports,headers={"x-requests-last":"0","x-requests-remaining":"500"}}={}){
 return {ok:status>=200&&status<300,status,headers:new Headers(headers),json:async()=>body};
}
function fakeD1(){
 const rows=[];
 let readCount=0;
 return {rows,get readCount(){return readCount},
  prepare(sql){
   const stmt={bind(...args){stmt.args=args;return stmt},
    async first(){
     readCount++;
     assert.match(sql,/SELECT.*scheduler_runs/);
     return rows.at(-1)||null;
    },
    async run(){
     assert.match(sql,/INSERT INTO scheduler_runs/);
     const [job,scheduled_at,completed_at,outcome,detail]=stmt.args;
     rows.push({job,scheduled_at,completed_at,outcome,detail});
     return {success:true,meta:{changes:1}};
    }
   };
   return stmt;
  }
 };
}
test("The Odds API free credential check uses ONLY /v4/sports and header auth",async()=>{
 let calls=0,seen;
 const mock=async (url,opts)=>{
  calls++;seen={url,method:opts.method,headers:opts.headers};
  return apiReply();
 };
 const x=await probeFreeSportsEndpoint(KEY,{fetcher:mock});
 assert.equal(calls,1);
 assert.equal(seen.url,FREE_SPORTS_ENDPOINT);
 assert.equal(seen.method,"GET");
 assert.equal(seen.headers["x-api-key"],KEY);
 assert.ok(!seen.url.includes(KEY));
 assert.equal(x.state,"authenticated");
 assert.equal(x.last_call_credits,0);
 assert.equal(x.quota_remaining,500);
 assert.equal(x.nba_active,true);
 assert.equal(x.nfl_active,true);
 assert.equal(x.sports_count,3);
 assert.ok(!JSON.stringify(x).includes(KEY));
});
test("unavailable or invalid key NEVER triggers network or is falsely marked authenticated",async()=>{
 let calls=0;
 for(const key of ["","short",null]){
  const x=await probeFreeSportsEndpoint(key,{fetcher:async()=>{calls++;throw Error("must not happen")}});
  assert.equal(x.state,"secret_not_configured");
 }
 assert.equal(calls,0);
 const x=await probeFreeSportsEndpoint(KEY,{fetcher:async()=>apiReply({status:401})});
 assert.equal(x.state,"authentication_rejected");
 assert.equal(x.http_status,401);
});
test("request error and zero credit-header ambiguity produce truthful statuses",async()=>{
 let x=await probeFreeSportsEndpoint(KEY,{fetcher:async()=>{throw Error("network")},timeoutMs:500});
 assert.equal(x.state,"network_or_timeout");
 x=await probeFreeSportsEndpoint(KEY,{fetcher:async()=>apiReply({headers:{}})});
 assert.equal(x.state,"unverified_request_cost");
 assert.equal(x.last_call_credits,null);
 x=await probeFreeSportsEndpoint(KEY,{fetcher:async()=>apiReply({headers:{"x-requests-last":"1"}})});
 assert.equal(x.state,"unverified_request_cost");
 assert.equal(x.last_call_credits,1);
});
test("Cron stores only sanitized free-auth result, no raw key, and paid collection stays disabled",async()=>{
 const db=fakeD1();
 const env={DB:db,ODDS_API_KEY:KEY,PAID_PROVIDER_REQUESTS:"disabled",APP_STAGE:"staging"};
 assert.equal(isCollectionEnabled(env),false);
 let requests=0;
 const now=Date.now();
 const x=await probeFreeKeyOnCron(env,{now,fetcher:async(url,options)=>{
  requests++;assert.equal(url,FREE_SPORTS_ENDPOINT);
  return apiReply();
 }});
 assert.equal(x.status,"authenticated");
 assert.equal(x.performed_request,true);
 assert.equal(x.last_call_credits,0);
 assert.equal(requests,1);
 assert.equal(db.rows.length,1);
 assert.equal(db.rows[0].outcome,"success");
 assert.ok(!JSON.stringify(db.rows).includes(KEY));
 assert.ok(!JSON.stringify(db.rows).includes("x-api-key"));
 assert.ok(!JSON.stringify(db.rows).includes("PrizePicks"));
 const read=await freeKeyProbeStatus(env);
 assert.equal(read.secret_configured,true);
 assert.equal(read.status,"authenticated");
 assert.equal(read.key_authentication_verified,true);
 assert.equal(read.quota_remaining,500);
 assert.equal(read.paid_collection,"disabled");
});
test("Cron skips second network request within six hours after a success",async()=>{
 const db=fakeD1();const env={DB:db,ODDS_API_KEY:KEY};
 const now=Date.now();
 let calls=0;
 const mock=async()=>{calls++;return apiReply()};
 assert.equal((await probeFreeKeyOnCron(env,{fetcher:mock,now})).status,"authenticated");
 assert.deepEqual(await probeFreeKeyOnCron(env,{fetcher:mock,now:now+1000}),
  {status:"skipped",reason:"recently_checked"});
 assert.equal(calls,1);
 assert.equal(db.rows.length,1);
});
test("newly added secret is tested promptly after previous skipped missing-secret receipt",async()=>{
 const db=fakeD1();const now=Date.now();
 const miss=await probeFreeKeyOnCron({DB:db},{now,fetcher:async()=>{throw Error("No key")}});
 assert.equal(miss.status,"secret_not_configured");
 const x=await probeFreeKeyOnCron({DB:db,ODDS_API_KEY:KEY},{
  now:now+10*1000,fetcher:async()=>apiReply()});
 assert.equal(x.status,"authenticated");
 assert.equal(db.rows.length,2);
});
test("failed key attempts are throttled for thirty minutes, not forever",async()=>{
 const db=fakeD1(),now=Date.now(),env={DB:db,ODDS_API_KEY:KEY};
 let calls=0;const bad=async()=>{calls++;return apiReply({status:401})};
 const initial=await probeFreeKeyOnCron(env,{now,fetcher:bad});
 assert.equal(initial.status,"authentication_rejected");
 assert.equal((await probeFreeKeyOnCron(env,{now:now+2000,fetcher:bad})).reason,"recently_checked");
 // use a synthetic completed_at to test elapsed time without timers.
 db.rows.at(-1).completed_at=new Date(now-31*60000).toISOString();
 const again=await probeFreeKeyOnCron(env,{now,fetcher:bad});
 assert.equal(again.status,"authentication_rejected");
 assert.equal(calls,2);
});
test("GET connection status is read-only; public clients never trigger provider requests",async()=>{
 const db=fakeD1();
 const saved=await freeKeyProbeStatus({DB:db,ODDS_API_KEY:KEY});
 assert.equal(saved.status,"awaiting_free_check");
 const absent=await freeKeyProbeStatus({DB:db});
 assert.equal(absent.status,"secret_not_configured");
 let outgoing=0;
 const old=globalThis.fetch;
 globalThis.fetch=async()=>{outgoing++;throw Error("public GET must not use fetch")};
 try{
  const res=await worker.fetch(new Request("https://stage.example/api/v1/odds/connection"),{DB:db,ODDS_API_KEY:KEY});
  assert.equal(res.status,200);
  const body=await res.json();
  assert.equal(body.status,"awaiting_free_check");
  assert.ok(!JSON.stringify(body).includes(KEY));
  assert.equal(outgoing,0);
 }finally{globalThis.fetch=old}
});
test("an absent D1 binding yields a clear unavailable result, not free authentication success",async()=>{
 const res=await worker.fetch(new Request("https://stage.example/api/v1/odds/connection"),{ODDS_API_KEY:KEY});
 assert.equal(res.status,200);
 assert.equal((await res.json()).status,"database_not_connected");
});

test("real scheduled zero-credit authentication remains visible when HTTP worker lacks its binding",async()=>{
 const db=fakeD1(),now=Date.now();
 const run=await probeFreeKeyOnCron({DB:db,ODDS_API_KEY:KEY,PAID_PROVIDER_REQUESTS:"disabled"},
  {now,fetcher:async(url,opts)=>{assert.equal(url,FREE_SPORTS_ENDPOINT);return apiReply()}});
 assert.equal(run.status,"authenticated");
 const publicStatus=await freeKeyProbeStatus({DB:db,PAID_PROVIDER_REQUESTS:"disabled"});
 assert.equal(publicStatus.secret_configured,false);
 assert.equal(publicStatus.http_handler_secret_visible,false);
 assert.equal(publicStatus.scheduled_cron_authentication_verified,true);
 assert.equal(publicStatus.http_cron_binding_mismatch,true);
 assert.equal(publicStatus.key_authentication_verified,true);
 assert.equal(publicStatus.status,"authenticated_by_cron_http_binding_mismatch");
 assert.equal(publicStatus.http_status,200);
 assert.equal(publicStatus.last_call_credits,0);
 assert.equal(publicStatus.quota_remaining,500);
 assert.equal(publicStatus.paid_collection,"disabled");
 assert.ok(!JSON.stringify(publicStatus).includes(KEY));
});
test("a stale scheduled receipt cannot be reported as valid authentication without current secret",async()=>{
 const db=fakeD1(),now=Date.now();
 await probeFreeKeyOnCron({DB:db,ODDS_API_KEY:KEY},{now,fetcher:async()=>apiReply()});
 db.rows[0].completed_at=new Date(now-9*60*60*1000).toISOString();
 const status=await freeKeyProbeStatus({DB:db});
 assert.equal(status.secret_configured,false);
 assert.equal(status.key_authentication_verified,false);
 assert.equal(status.scheduled_cron_authentication_verified,false);
 assert.equal(status.http_cron_binding_mismatch,false);
 assert.equal(status.status,"secret_not_configured");
});

test("read-only status distinguishes HTTP version from the Cron version without exposing secrets",async()=>{
 const db=fakeD1(),now=Date.now();
 const cronVersion="cron-release-123",httpVersion="http-release-456";
 const verified=await probeFreeKeyOnCron({DB:db,ODDS_API_KEY:KEY,
  CF_VERSION_METADATA:{id:cronVersion}},{now,fetcher:async()=>apiReply()});
 assert.equal(verified.status,"authenticated");
 const row=JSON.parse(db.rows.at(-1).detail);
 assert.equal(row.worker_version,cronVersion);
 assert.ok(!JSON.stringify(row).includes(KEY));
 const publicStatus=await freeKeyProbeStatus({DB:db,CF_VERSION_METADATA:{id:httpVersion}});
 assert.equal(publicStatus.http_worker_version,httpVersion);
 assert.equal(publicStatus.scheduled_cron_worker_version,cronVersion);
 assert.equal(publicStatus.http_cron_version_mismatch,true);
 assert.equal(publicStatus.http_cron_binding_mismatch,true);
 assert.equal(publicStatus.key_authentication_verified,true);
 assert.equal(publicStatus.last_call_credits,0);
 const same=await freeKeyProbeStatus({DB:db,ODDS_API_KEY:KEY,CF_VERSION_METADATA:{id:cronVersion}});
 assert.equal(same.http_cron_version_mismatch,false);
 assert.equal(same.http_cron_binding_mismatch,false);
 assert.equal(same.status,"authenticated");
});
