import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import worker,{normalizeSource,cronHeartbeat,ensureStagingSchema} from "../src/worker.js";
import {BOOTSTRAP_0001_SQL} from "../src/bootstrap-0001.js";

const request=(path,method="GET")=>new Request("https://dames-picks-staging.example"+path,{method});
const statusRow={source_id:"nba_scores",league:"NBA",status:"ok",last_observed_at:"2026-11-17T10:00:00.000Z",
 last_success_at:"2026-11-17T10:00:00.000Z",last_attempt_at:null,max_age_minutes:10,records:12,note:"verified"};
function fakeDb({empty=false,broken=false}={}){
 const runs=[];
 let seeded=!empty,bootstraps=0;
 const db={
  prepare(sql) {
   const stmt={bind(...args){stmt.args=args;return stmt},
    async all(){
     if(!seeded)throw Error("no such table: source_health");
     assert.match(sql,/FROM source_health/);
     return {results:[statusRow]};
    },
    async first(){
     if(!seeded)throw Error("no such table");
     if(sql.includes("COUNT(*) AS count FROM source_health"))return {count:7};
     if(sql.includes("COUNT(*) AS count FROM scheduler_runs"))return {count:runs.length};
     assert.match(sql,/FROM scheduler_runs/);
     return runs.length?{job:"staging-heartbeat",outcome:"success",scheduled_at:runs.at(-1)[1]}:null;
    },
    async run(){
     if(!seeded)throw Error("no such table");
     assert.match(sql,/INSERT INTO scheduler_runs/);
     runs.push(stmt.args);
     return {success:true};
    }
   };
   return stmt;
  },
  async exec(sql){
   if(broken)throw Error("simulated D1 failure");
   assert.ok(!sql.includes("PRAGMA foreign_keys = ON;"),"D1 migration must not change runtime pragma");
   assert.match(sql,/CREATE TABLE IF NOT EXISTS source_health/);
   assert.match(sql,/CREATE TABLE IF NOT EXISTS scheduler_runs/);
   assert.match(sql,/INSERT OR IGNORE INTO source_health/);
   seeded=true;bootstraps++;
   return {count:4};
  }
 };
 return {db,runs,bootstraps:()=>bootstraps};
}
test("staging Worker reachable without D1 but cannot claim automatic data collection",async()=>{
 const r=await worker.fetch(request("/healthz"),{});
 assert.equal(r.status,200);
 const x=await r.json();
 assert.equal(x.stage,"staging");
 assert.equal(x.provider_collection_active,false);
 assert.equal(x.database_binding_present,false);
 assert.equal(x.paid_provider_calls,"disabled");
 assert.equal(x.schema_bootstrap_version,"0001 + 0002 odds");
 assert.equal(x.scheduler_mode,"cloudflare_cron_d1_heartbeat");
});
test("readiness returns 503 without D1 and all sources disclosed as not connected",async()=>{
 const r=await worker.fetch(request("/api/v1/status"),{});
 assert.equal(r.status,503);
 const x=await r.json();
 assert.equal(x.status,"setup_required");
 assert.equal(x.expected_sources.length,7);
 assert.equal(x.automatic_collectors,"not_connected");
});
test("D1 readiness stays unavailable until the actual schema exists; public GET never initializes it",async()=>{
 const {db,bootstraps}=fakeDb({empty:true});
 const r=await worker.fetch(request("/api/v1/status"),{DB:db});
 assert.equal(r.status,503);
 assert.equal((await r.json()).status,"database_unavailable");
 assert.equal(bootstraps(),0);
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
test("the Cron bootstraps an empty D1 database once and persists heartbeats on subsequent runs",async()=>{
 const {db,runs,bootstraps}=fakeDb({empty:true});
 const first=await cronHeartbeat({scheduledTime:Date.parse("2026-11-17T10:15:00Z")},{DB:db,PAID_PROVIDER_REQUESTS:"disabled"});
 assert.equal(first.status,"success");
 assert.equal(bootstraps(),1);
 const second=await cronHeartbeat({scheduledTime:Date.parse("2026-11-17T10:30:00Z")},{DB:db,PAID_PROVIDER_REQUESTS:"disabled"});
 assert.equal(second.status,"success");
 assert.equal(bootstraps(),1,"Already-created schema cannot be rewritten on every Cron");
 assert.equal(runs.length,2);
 assert.deepEqual(runs.map(r=>r[0]),["staging-heartbeat","staging-heartbeat"]);
 assert.match(runs[0][4],/No external/);
});
test("one-time bootstrap SQL matches versioned migration bytes precisely",()=>{
 const sql=readFileSync(new URL("../migrations/0001_bootstrap.sql",import.meta.url),"utf8");
 assert.equal(BOOTSTRAP_0001_SQL,sql);
 assert.match(sql,/postgame_grades/);
 assert.match(sql,/prizepicks_standard_lines/);
});
test("D1 initialization failures do not write heartbeat or claim success",async()=>{
 const {db,runs}=fakeDb({empty:true,broken:true});
 const result=await cronHeartbeat({scheduledTime:Date.now()},{DB:db,PAID_PROVIDER_REQUESTS:"disabled"});
 assert.equal(result.status,"failure");
 assert.equal(result.reason,"d1_bootstrap_failed");
 assert.equal(runs.length,0);
});
test("cron fails closed with unbound database or a misconfigured paid mode",async()=>{
 assert.equal((await cronHeartbeat({scheduledTime:0},{})).status,"skipped");
 const {db,runs,bootstraps}=fakeDb({empty:true});
 const r=await cronHeartbeat({scheduledTime:0},{DB:db,PAID_PROVIDER_REQUESTS:"invalid"});
 assert.equal(r.status,"skipped");
 assert.equal(runs.length,0);
 assert.equal(bootstraps(),0);
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
test("only the owner's Dame's Picks D1 is bound and paid collectors remain disabled",()=>{
 const config=JSON.parse(readFileSync(new URL("../wrangler.jsonc",import.meta.url),"utf8"));
 assert.equal(config.name,"dames-picks-staging");
 assert.notEqual(config.name,"federal-briefing-mvp");
 assert.equal(config.vars.PAID_PROVIDER_REQUESTS,"disabled");
 assert.deepEqual(config.triggers.crons,["*/15 * * * *"]);
 assert.deepEqual(config.d1_databases,[{
  binding:"DB",
  database_name:"dames-picks-staging-db",
  database_id:"7ccf157d-aab6-4efd-afb8-d9dfb69d8af8",
  migrations_dir:"migrations"
 }]);
 assert.ok(!JSON.stringify(config).includes("api_key"));
});
