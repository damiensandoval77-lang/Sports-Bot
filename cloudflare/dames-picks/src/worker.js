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
    paid_provider_calls: "disabled",
    current_public_site_unchanged: true
  });
}
export async function cronHeartbeat(controller, env) {
  if (!hasD1(env)) return {status:"skipped",reason:"d1_not_bound"};
  if (env.PAID_PROVIDER_REQUESTS !== "disabled")
    return {status:"skipped",reason:"paid_calls_must_remain_disabled_in_staging"};
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
    if (api) return json({error:"unknown_api_endpoint"},404);
    if (request.method !== "GET" && request.method !== "HEAD") {
      return json({error:"method_not_allowed"},405,{"allow":"GET, HEAD"});
    }
    if (path === "/") return Response.redirect(new URL("/dames-picks/",url),302);
    if (!env?.ASSETS?.fetch) return json({error:"assets_not_deployed"},503);
    return env.ASSETS.fetch(request);
  },
  scheduled(controller, env, context) {
    context.waitUntil(cronHeartbeat(controller,env));
  }
};
