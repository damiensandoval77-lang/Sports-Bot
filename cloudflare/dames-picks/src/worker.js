import {BOOTSTRAP_0001_SQL} from "./bootstrap-0001.js";
import {BOOTSTRAP_0002_ODDS_SQL} from "./bootstrap-0002-odds.js";
import {readOddsCatalog,readMarketBoard,readOddsBudget} from "./odds-query.js";
import {collectOddsIfEnabled,isCollectionEnabled} from "./odds-collector.js";
/**
 * Dame's Picks staging Worker. Zero paid provider calls. No changes to
 * Federal Briefing or to the current GitHub Pages production deployment.
 *
 * Phase 1: serve the approved unified site, expose honest D1 readiness and
 * prove an independent Cloudflare Cron heartbeat before paid collectors.
 *
 * D1 binding is deliberately optional until created in the owner's account.
 * Do not set service status to "ready" merely because the Worker is reachable.
 */
const SERVICE = "dames-picks-staging";
const JSON_HEADERS = Object.freeze({
  "content-type": "application/json; charset=utf-8",
  "cache-control": "no-store, max-age=0",
  "x-content-type-options": "nosniff",
  "referrer-policy": "no-referrer"
});
const EXPECTED = [
  "nba_scores", "nba_player_stats", "nfl_scores", "nfl_player_stats",
  "prizepicks_standard_lines", "frozen_ai_projections", "postgame_grades"
];
const json = (value, status = 200, extra = {}) =>
  new Response(JSON.stringify(value), {status, headers:{...JSON_HEADERS,...extra}});

export function hasD1(env) {
  return typeof env?.DB?.prepare === "function";
}
function ageInMinutes(when, now) {
  if (!when) return null;
  const raw=String(when).trim();
  const iso = raw.includes(" ") && !raw.includes("T") ? raw.replace(" ","T")+"Z" : raw;
  const ms=Date.parse(iso);
  if (!Number.isFinite(ms) || ms > now + 120000) return null;
  return Math.max(0, Math.round((now - ms) / 60000));
}
export function normalizeSource(row, now = Date.now()) {
  const ageMinutes = ageInMinutes(row.last_observed_at, now);
  const maxAgeMinutes = Number(row.max_age_minutes) || 0;
  const stale = row.status === "ok" && (ageMinutes === null || ageMinutes > maxAgeMinutes);
  return {
    source: row.source_id,
    league: row.league,
    status: stale ? "stale" : row.status,
    last_observed_at: row.last_observed_at || null,
    last_success_at: row.last_success_at || null,
    last_attempt_at: row.last_attempt_at || null,
    age_minutes: ageMinutes,
    max_age_minutes: maxAgeMinutes,
    records: Number(row.records) || 0,
    note: row.note || ""
  };
}
async function status(env) {
  if (!hasD1(env)) return json({
    service: SERVICE,
    status: "setup_required",
    database: "not_bound",
    automatic_collectors: "not_connected",
    paid_provider_calls: "disabled",
    expected_sources: EXPECTED,
    message: "Create a separate Dame's Picks D1 database and apply migrations before enabling collectors."
  }, 503);
  try {
    const [sources, heartbeat] = await Promise.all([
      env.DB.prepare("SELECT source_id,league,status,last_observed_at,last_success_at,last_attempt_at,max_age_minutes,records,note FROM source_health ORDER BY source_id").all(),
      env.DB.prepare("SELECT job,scheduled_at,completed_at,outcome FROM scheduler_runs WHERE job = ? ORDER BY run_id DESC LIMIT 1").bind("staging-heartbeat").first()
    ]);
    const rows = (sources?.results || []).map(row => normalizeSource(row));
    const byId = new Set(rows.map(row => row.source));
    const complete = EXPECTED.every(id => byId.has(id) && rows.find(row=>row.source===id)?.status==="ok");
    return json({
      service: SERVICE,
      status: complete ? "data_ready" : "collectors_not_ready",
      database: "connected",
      scheduled_heartbeat: heartbeat || null,
      automatic_collectors: "not_connected",
      paid_provider_calls: "disabled",
      sources: rows,
      missing_source_rows: EXPECTED.filter(id=>!byId.has(id))
    }, 200);
  } catch (_error) {
    // Never echo DB exception, SQL text or credentials to the browser.
    return json({service:SERVICE,status:"database_unavailable",message:"D1 migration or binding unavailable"},503);
  }
}
async function health(env) {
  return json({
    service: SERVICE,
    stage: "staging",
    worker_reachable: true,
    database_binding_present: hasD1(env),
    provider_collection_active: false,
    provider_collection_configured: isCollectionEnabled(env),
    paid_provider_calls: isCollectionEnabled(env) ? "enabled" : "disabled",
    schema_bootstrap_version: "0001 + 0002 odds",
    scheduler_mode: "cloudflare_cron_d1_heartbeat",
    current_public_site_unchanged: true
  });
}
/**
 * Bootstrap the *new staging database only* from the versioned 0001 migration.
 * No public HTTP route is allowed to run this mutation. Replays are safe:
 * the CREATE statements use IF NOT EXISTS; source seeds use OR IGNORE.
 *
 * Existing tables never get dropped or replaced. Later migrations must still
 * go through reviewed versioned D1 migration commands, not this initializer.
 */
export async function ensureStagingSchema(db) {
  try {
    const source = await db.prepare("SELECT COUNT(*) AS count FROM source_health").first();
    await db.prepare("SELECT COUNT(*) AS count FROM scheduler_runs").first();
    if (Number(source?.count) >= 7) return {initialized:false,source_rows:Number(source.count)};
  } catch (_) {
    // A new empty D1 database has no tables, so it needs the first migration.
    // All unexpected DB errors are treated as failures unless the migration
    // succeeds and the expected source rows are independently verified below.
  }
  const oneTimeSql = BOOTSTRAP_0001_SQL.replace("PRAGMA foreign_keys = ON;","");
  await db.exec(oneTimeSql);
  const result = await db.prepare("SELECT COUNT(*) AS count FROM source_health").first();
  await db.prepare("SELECT COUNT(*) AS count FROM scheduler_runs").first();
  if (Number(result?.count) < 7) throw new Error("D1 bootstrap verification failed");
  return {initialized:true,source_rows:Number(result.count)};
}
/**
 * Private scheduled initialization of the versioned, idempotent 0002 odds
 * cache and credit reservations. Never initialized from a public URL.
 */
export async function ensureOddsSchema(db){
 try{
  await db.prepare("SELECT month_utc FROM odds_api_budget LIMIT 1").all();
  await db.prepare("SELECT quote_key FROM odds_api_quotes LIMIT 1").all();
  await db.prepare("SELECT id FROM odds_api_attempts LIMIT 1").all();
  return {initialized:false};
 }catch(_){/* fresh D1 requires the second migration */}
 await db.exec(BOOTSTRAP_0002_ODDS_SQL);
 await db.prepare("SELECT month_utc FROM odds_api_budget LIMIT 1").all();
 await db.prepare("SELECT quote_key FROM odds_api_quotes LIMIT 1").all();
 await db.prepare("SELECT id FROM odds_api_attempts LIMIT 1").all();
 return {initialized:true};
}
export async function cronHeartbeat(controller, env) {
  if (!hasD1(env)) return {status:"skipped",reason:"d1_not_bound"};
  if (!["disabled","enabled"].includes(env.PAID_PROVIDER_REQUESTS))
    return {status:"skipped",reason:"invalid_paid_configuration"};
  // Prepare the initial seven-source readiness schema before inserting any heartbeat.
  // No odds, player statistics, or prediction APIs are called here.
  try { await ensureStagingSchema(env.DB); }
  catch (_) {
    console.error("Dame\'s Picks staging D1 initialization failed; no external provider was contacted.");
    return {status:"failure",reason:"d1_bootstrap_failed"};
  }
  const time = Number(controller?.scheduledTime) || Date.now();
  const scheduledAt = new Date(time).toISOString();
  const completedAt = new Date().toISOString();
  try {
    await env.DB.prepare(
      "INSERT INTO scheduler_runs(job,scheduled_at,completed_at,outcome,detail) VALUES(?,?,?,?,?)"
    ).bind("staging-heartbeat",scheduledAt,completedAt,"success","No external sports/odds provider called").run();
    return {status:"success",scheduled_at:scheduledAt};
  } catch (_error) {
    console.error("Dame's Picks staging Cron could not write D1 heartbeat; migration or binding may be missing.");
    return {status:"failure",reason:"d1_unavailable"};
  }
}
export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const path = url.pathname;
    const api = path.startsWith("/api/");
    if ((api || path === "/healthz") && request.method !== "GET") {
      return json({error:"method_not_allowed"},405,{"allow":"GET"});
    }
    if (path === "/healthz" || path === "/api/v1/health") return health(env);
    if (path === "/api/v1/status") return status(env);
    if (path === "/api/v1/odds/catalog")return json(readOddsCatalog());
    if (path === "/api/v1/odds/budget"){
      const state=await readOddsBudget(env.DB,env);
      return json(state,state.status==="ok"?200:503);
    }
    if (path === "/api/v1/odds/board"){
      const league=String(url.searchParams.get("league")||"NBA").toUpperCase();
      const limit=Number(url.searchParams.get("limit")||60);
      const state=await readMarketBoard(env.DB,{league,limit});
      return json(state,state.status==="invalid_league"?400:
       ["database_not_connected","market_schema_unavailable"].includes(state.status)?503:200);
    }
    if (api) return json({error:"unknown_api_endpoint"},404);
    if (request.method !== "GET" && request.method !== "HEAD") {
      return json({error:"method_not_allowed"},405,{"allow":"GET, HEAD"});
    }
    if (path === "/") return Response.redirect(new URL("/dames-picks/",url),302);
    if (!env?.ASSETS?.fetch) return json({error:"assets_not_deployed"},503);
    return env.ASSETS.fetch(request);
  },
  scheduled(controller, env, context) {
    context.waitUntil((async()=>{
      const heartbeat=await cronHeartbeat(controller,env);
      if(heartbeat.status!=="success")return;
      try{await ensureOddsSchema(env.DB)}
      catch(_){console.error("Dame's Picks staging odds D1 schema is not ready");return}
      // Paid requests require three explicit opt-ins, a Worker secret and
      // positive persisted monthly/daily caps. Defaults spend exactly zero.
      if(!isCollectionEnabled(env))return;
      try{
        const run=await collectOddsIfEnabled(env);
        const at=new Date().toISOString();
        await env.DB.prepare(
         "INSERT INTO scheduler_runs(job,scheduled_at,completed_at,outcome,detail) VALUES(?,?,?,?,?)"
        ).bind("odds-api-budgeted-collector",new Date(Number(controller?.scheduledTime)||Date.now()).toISOString(),
         at,["ok","empty","no_eligible_events","budget_blocked","disabled"].includes(run.status)?"skipped":"failure",
         JSON.stringify({status:run.status,credits:run.credits_charged??0,quotes:run.quotes_stored??0}).slice(0,240)).run();
      }catch(_){console.error("Dame's Picks optional Odds API collector failed safely")}
    })());
  }
};
