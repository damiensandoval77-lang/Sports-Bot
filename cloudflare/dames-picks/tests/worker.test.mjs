import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import worker,{normalizeSource,cronHeartbeat} from "../src/worker.js";

const request=(path,method="GET")=>new Request("https://dames-picks-staging.example"+path,{method});
const statusRow={source_id:"nba_scores",league:"NBA",status:"ok",last_observed_at:"2026-11-17T10:00:00.000Z",
 last_success_at:"2026-11-17T10:00:00.000Z",last_attempt_at:null,max_age_minutes:10,records:12,note:"verified"};
function fakeDb(){
 const runs=[];
 const db={
  prepare(sql) {
   const stmt={bind(...args){stmt.args=args;return stmt},
    async all(){assert.match(sql,/source_health/);return {results:[statusRow]}},
    async first(){assert.match(sql,/scheduler_runs/);return runs.length?{job:"staging-heartbeat",outcome:"success",scheduled_at:runs[0][1]}:null},
    async run(){runs.push(stmt.args);return {success:true}}
   };return stmt;
  }
 };
 return {db,runs};
}
test("staging Worker reachable without D1 but cannot claim automatic data collection",async()=>{
 const r=await worker.fetch(request("/healthz"),{});
 assert.equal(r.status,200);
 const x=await r.json();
 assert.equal(x.stage,"staging");
 assert.equal(x.provider_collection_active,false);
 assert.equal(x.database_binding_present,false);
 assert.equal(x.paid_provider_calls,"disabled");
});
test("readiness returns 503 without D1 and all sources disclosed as not connected",async()=>{
 const r=await worker.fetch(request("/api/v1/status"),{});
 assert.equal(r.status,503);
 const x=await r.json();
 assert.equal(x.status,"setup_required");
 assert.equal(x.expected_sources.length,7);
 assert.equal(x.automatic_collectors,"not_connected");
});
test("D1 status never claims connected collectors just because cron or partial data exists",async()=>{
 const {db}=fakeDb();
 const r=await worker.fetch(request("/api/v1/status"),{DB:db});
 assert.equal(r.status,200);
 const x=await r.json();
 assert.equal(x.database,"connected");
 assert.equal(x.status,"collectors_not_ready");
 assert.equal(x.automatic_collectors,"not_connected");
 assert.ok(x.missing_source_rows.includes("postgame_grades"));
});
test("freshness timestamps compare actual observed time, not build/deploy time",()=>{
 const now=Date.parse("2026-11-17T10:20:00Z");
 const x=normalizeSource(statusRow,now);
 assert.equal(x.status,"stale");
 assert.equal(x.age_minutes,20);
 const y=normalizeSource({...statusRow,last_observed_at:"2026-11-17 10:15:00"},now);
 assert.equal(y.status,"ok");
 assert.equal(y.age_minutes,5);
});
test("cron records a persistent heartbeat without contacting paid or free sports APIs",async()=>{
 const {db,runs}=fakeDb();
 const result=await cronHeartbeat({scheduledTime:Date.parse("2026-11-17T10:15:00Z")},{DB:db,PAID_PROVIDER_REQUESTS:"disabled"});
 assert.equal(result.status,"success");
 assert.equal(runs.length,1);
 assert.equal(runs[0][0],"staging-heartbeat");
 assert.match(runs[0][4],/No external/);
});
test("cron fails closed with unbound database or a misconfigured paid mode",async()=>{
 assert.equal((await cronHeartbeat({scheduledTime:0},{})).status,"skipped");
 const {db,runs}=fakeDb();
 const r=await cronHeartbeat({scheduledTime:0},{DB:db,PAID_PROVIDER_REQUESTS:"enabled"});
 assert.equal(r.status,"skipped");
 assert.equal(runs.length,0);
});
test("unknown API and non-GET writes are unavailable; root redirects to internal staging site",async()=>{
 const r=await worker.fetch(request("/api/internal/ingest","POST"),{});
 assert.equal(r.status,405);
 const unknown=await worker.fetch(request("/api/internal/ingest"),{});
 assert.equal(unknown.status,404);
 const root=await worker.fetch(request("/"),{});
 assert.equal(root.status,302);
 assert.equal(new URL(root.headers.get("location")).pathname,"/dames-picks/");
});
test("all other assets use the provided public site asset binding",async()=>{
 const assets={async fetch(req){assert.match(req.url,/dames-picks\/index.html/);return new Response("existing sports homepage")}};
 const r=await worker.fetch(request("/dames-picks/index.html"),{ASSETS:assets});
 assert.equal(await r.text(),"existing sports homepage");
});
test("Cloudflare account isolation and zero automatic provider charges are explicit",()=>{
 const config=JSON.parse(readFileSync(new URL("../wrangler.jsonc",import.meta.url),"utf8"));
 assert.equal(config.name,"dames-picks-staging");
 assert.notEqual(config.name,"federal-briefing-mvp");
 assert.equal(config.vars.PAID_PROVIDER_REQUESTS,"disabled");
 assert.deepEqual(config.triggers.crons,["*/15 * * * *"]);
 assert.ok(!JSON.stringify(config).includes("api_key"));
});
