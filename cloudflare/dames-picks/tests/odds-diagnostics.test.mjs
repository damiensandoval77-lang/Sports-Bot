import test from "node:test";
import assert from "node:assert/strict";
import worker from "../src/worker.js";
import {readOddsDiagnostics} from "../src/odds-diagnostics.js";
import {collectOddsIfEnabled} from "../src/odds-collector.js";

const secret="test_secret_that_must_never_appear_123456";
const now=Date.parse("2026-11-17T19:00:00.000Z");
const fixtureEvent={id:"a512a48a58c4329048174217b2cc7ce0",
 commence_time:"2026-11-17T21:00:00Z",home_team:"Boston Celtics",away_team:"New York Knicks"};
const enabled={
 APP_STAGE:"staging",ODDS_API_KEY:secret,PAID_PROVIDER_REQUESTS:"enabled",ODDS_API_COLLECTION:"enabled",
 ODDS_API_MONTHLY_CREDIT_CAP:"100",ODDS_API_DAILY_CREDIT_CAP:"12"
};
test("zero-credit discovery 403 is reported as a provider error, not no upcoming games",async()=>{
 let calls=0;
 const db={prepare(sql){return {bind(){return this},async all(){return{results:[]}}}}};
 const mock=async(url)=>{
  calls++;
  assert.match(url,/\/events$/);
  return {ok:false,status:403,headers:new Headers()};
 };
 const result=await collectOddsIfEnabled({...enabled,DB:db},{fetcher:mock,now,leagueOrder:["NBA"]});
 assert.equal(result.status,"discovery_failed");
 assert.equal(result.paid_requests,0);
 assert.equal(calls,1);
 assert.deepEqual(result.discovery,[{league:"NBA",status:"discovery_error",reason:"ODDS_API_HTTP_403"}]);
 assert.ok(!JSON.stringify(result).includes(secret));
});
test("empty free event list is distinct from a failed provider request",async()=>{
 let calls=0;
 const db={prepare(){return {bind(){return this},async all(){return{results:[]}}}}};
 const mock=async()=>{calls++;return {ok:true,status:200,headers:new Headers(),json:async()=>[]}};
 const result=await collectOddsIfEnabled({...enabled,DB:db},{fetcher:mock,now,leagueOrder:["NBA"]});
 assert.equal(result.status,"no_eligible_events");
 assert.equal(result.paid_requests,0);
 assert.equal(calls,1);
 assert.deepEqual(result.discovery,[{league:"NBA",status:"no_eligible_event",event_count:0}]);
});
test("D1 receipt includes safe successful record counts, not secrets, on GET diagnostics",async()=>{
 const run={completed_at:"2026-11-17T18:58:00Z",outcome:"success",
  detail:JSON.stringify({status:"ok",league:"NBA",credits:2,quotes:4,
   discovery:[{league:"NBA",status:"eligible",event_count:8}],
   providers_seen:["prizepicks","fanduel","evil"],rejected:{missing_sportsbook_price:2}})};
 const db={prepare(sql){
  const p={bind(...args){p.args=args;return p},async all(){
   if(sql.includes("FROM scheduler_runs"))return {results:[run]};
   if(sql.includes("FROM odds_api_attempts"))return {results:[{
    league:"NBA",event_id:fixtureEvent.id,requested_at:"2026-11-17T18:57:00Z",
    outcome:"ok",charged_credits:2,quotes_stored:4,note:""
   }]};
   if(sql.includes("FROM odds_api_quotes"))return{results:[{league:"NBA",total:4,recent_pregame:4}]};
   throw Error("unexpected query");
  }};
  return p;
 }};
 let outgoing=0;const original=globalThis.fetch;
 globalThis.fetch=async()=>{outgoing++;throw Error("No provider requests on diagnostic GET")};
 try{
  const res=await worker.fetch(new Request("https://staging.example/api/v1/odds/diagnostics"),{...enabled,DB:db});
  assert.equal(res.status,200);
  const json=await res.json();
  assert.equal(json.collector_configured,true);
  assert.equal(json.recent_runs[0].quotes_stored,4);
  assert.deepEqual(json.recent_runs[0].providers_seen,["prizepicks","fanduel"]);
  assert.equal(json.recent_attempts[0].credits_charged,2);
  assert.deepEqual(json.stored_quote_counts,[{league:"NBA",stored:4,recent_pregame:4}]);
  assert.equal(outgoing,0);
  assert.ok(!JSON.stringify(json).includes(secret));
 }finally{globalThis.fetch=original}
});
test("GET diagnostics are unavailable without database and never create schema",async()=>{
 const res=await worker.fetch(new Request("https://staging.example/api/v1/odds/diagnostics"),enabled);
 assert.equal(res.status,503);
 assert.equal((await res.json()).status,"database_not_connected");
});
test("unhandled D1 query failure returns explicit unavailable status, never sensitive exception",async()=>{
 const db={prepare(){throw Error("private row with "+secret)}};
 const result=await readOddsDiagnostics({...enabled,DB:db},now);
 assert.equal(result.status,"database_unavailable");
 assert.ok(!JSON.stringify(result).includes(secret));
});
