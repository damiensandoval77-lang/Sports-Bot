/**
 * Safe read-only visibility into the staging odds collector.
 * This endpoint performs no upstream fetches and never exposes secrets,
 * provider responses, unrestricted D1 SQL, or raw exception strings.
 */
import {isCollectionEnabled} from "./odds-collector.js";
const JOB="odds-api-budgeted-collector";
const cleanStatus=s=>typeof s==="string"&&/^[a-z_]{2,50}$/.test(s)?s:"unknown";
const safeInt=v=>Number.isSafeInteger(Number(v))&&Number(v)>=0?Number(v):null;
const safeLeague=l=>["NBA","NFL"].includes(l)?l:null;
const BOOKS=["prizepicks","underdog","fanduel","draftkings"];
const EVENT_LIMIT=100;
const safeTime=v=>typeof v==="string"&&Number.isFinite(Date.parse(v))?new Date(v).toISOString():null;
// Counts come from accepted persisted quotes, NOT providers_seen in a response.
// Rank before filtering freshness so old line versions cannot inflate coverage.
const COVERAGE_CTE=`WITH ranked AS (
 SELECT *,ROW_NUMBER() OVER (
  PARTITION BY league,event_id,bookmaker,market_key,player_key
  ORDER BY market_observed_at DESC,captured_at DESC,quote_key DESC) AS latest
 FROM odds_api_quotes WHERE source='the_odds_api' AND is_alternate=0
 AND bookmaker IN ('prizepicks','underdog','fanduel','draftkings')
), coverage AS (
 SELECT *,CASE WHEN latest=1 AND event_start>? AND market_observed_at>?
  AND market_observed_at<=? AND captured_at<=? AND market_observed_at<=captured_at
  AND captured_at<event_start THEN 1 ELSE 0 END AS fresh_latest FROM ranked
) `;
const COVERAGE_FIELDS=`COUNT(*) AS accepted_observations,
 SUM(fresh_latest) AS fresh_pregame_lines,
 MIN(market_observed_at) AS oldest_observed_at,
 MAX(market_observed_at) AS latest_observed_at,MAX(captured_at) AS latest_captured_at`;
function coverageRow(r,now){
 const observed=safeTime(r.latest_observed_at);
 return {league:safeLeague(r.league),bookmaker:BOOKS.includes(r.bookmaker)?r.bookmaker:null,
  accepted_observations:safeInt(r.accepted_observations)??0,
  fresh_pregame_lines:safeInt(r.fresh_pregame_lines)??0,
  oldest_observed_at:safeTime(r.oldest_observed_at),latest_observed_at:observed,
  latest_captured_at:safeTime(r.latest_captured_at),
  latest_observation_age_seconds:observed&&Date.parse(observed)<=now?Math.floor((now-Date.parse(observed))/1000):null};
}
function safeReason(value){
 if(typeof value!=="string")return null;
 return /^ODDS_API_HTTP_[0-9]{3}$/.test(value)||[
  "ODDS_API_INVALID_EVENTS_RESPONSE","ODDS_API_DISCOVERY_FAILED",
  "odds_d1_schema_not_installed","no_owner_opt_in","not_staging",
  "Provider quota anomaly","Event identity mismatch"
 ].includes(value)?value:null;
}
function parseReceipt(row){
 let payload={};
 try{payload=JSON.parse(row.detail||"{}")}catch(_){}
 return {
  completed_at:row.completed_at||null,
  outcome:row.outcome==="success"?"success":row.outcome==="skipped"?"skipped":"failure",
  status:cleanStatus(payload.status),
  league:safeLeague(payload.league),
  credits_charged:safeInt(payload.credits),
  quotes_stored:safeInt(payload.quotes),
  discovery:Array.isArray(payload.discovery)?payload.discovery.slice(0,2).map(x=>({
   league:safeLeague(x?.league),
   status:cleanStatus(x?.status),
   event_count:safeInt(x?.event_count),
   reason:safeReason(x?.reason)
  })):[],
  providers_seen:Array.isArray(payload.providers_seen)?
   payload.providers_seen.filter(x=>["prizepicks","underdog","fanduel","draftkings"].includes(x)).slice(0,4):[],
  rejected:payload.rejected && typeof payload.rejected==="object"?
   Object.fromEntries(Object.entries(payload.rejected).filter(([k,v])=>
    /^[a-z_]{3,70}$/.test(k)&&safeInt(v)!==null).slice(0,10).map(([k,v])=>[k,Number(v)])):null
 };
}
export async function readOddsDiagnostics(env,now=Date.now()){
 const configured=isCollectionEnabled(env);
 if(typeof env?.DB?.prepare!=="function")return {
  status:"database_not_connected",collector_configured:configured,
  recent_runs:[],recent_attempts:[],stored_quote_counts:[]
 };
 try{
  const since=new Date(now-90*60000).toISOString();
  const future=new Date(now).toISOString();
  const [runs,attempts,counts,books,events]=await Promise.all([
   env.DB.prepare("SELECT completed_at,outcome,detail FROM scheduler_runs WHERE job=? ORDER BY run_id DESC LIMIT 5").bind(JOB).all(),
   env.DB.prepare("SELECT league,event_id,requested_at,outcome,charged_credits,quotes_stored,note FROM odds_api_attempts ORDER BY id DESC LIMIT 5").all(),
   env.DB.prepare("SELECT league,COUNT(*) AS total, SUM(CASE WHEN event_start>? AND market_observed_at>? THEN 1 ELSE 0 END) AS recent_pregame FROM odds_api_quotes GROUP BY league").bind(future,since).all(),
   env.DB.prepare(COVERAGE_CTE+"SELECT league,bookmaker,"+COVERAGE_FIELDS+
    " FROM coverage GROUP BY league,bookmaker ORDER BY league,bookmaker LIMIT 8")
    .bind(future,since,future,future).all(),
   env.DB.prepare(COVERAGE_CTE+"SELECT league,bookmaker,event_id,event_start,"+COVERAGE_FIELDS+
    " FROM coverage GROUP BY league,bookmaker,event_id,event_start "+
    "ORDER BY MAX(captured_at) DESC,league,bookmaker,event_id,event_start LIMIT ?")
    .bind(future,since,future,future,EVENT_LIMIT+1).all()
  ]);
  return {
   status:"ok",
   collector_configured:configured,
   quote_coverage:{
    checked_at:future,freshness_window_minutes:90,
    provenance:"accepted_the_odds_api_nonalternate_quotes_not_native_tier_verification",
    counts_include_historical_observations:true,
    fresh_lines_count_latest_player_market_per_event_bookmaker:true,
    bookmaker_counts:(books.results||[]).map(r=>coverageRow(r,now)),
    event_bookmaker_counts:(events.results||[]).slice(0,EVENT_LIMIT).map(r=>({
     ...coverageRow(r,now),
     event_id:typeof r.event_id==="string"&&/^[a-zA-Z0-9]{8,80}$/.test(r.event_id)?r.event_id:null,
     event_start:safeTime(r.event_start)
    })),
    event_group_limit:EVENT_LIMIT,event_groups_truncated:(events.results||[]).length>EVENT_LIMIT
   },
   recent_runs:(runs.results||[]).map(parseReceipt),
   recent_attempts:(attempts.results||[]).map(r=>({
    league:safeLeague(r.league),
    event_id:typeof r.event_id==="string"&&/^[a-zA-Z0-9]{8,80}$/.test(r.event_id)?r.event_id:null,
    requested_at:r.requested_at||null,
    outcome:cleanStatus(r.outcome),
    credits_charged:safeInt(r.charged_credits),
    quotes_stored:safeInt(r.quotes_stored),
    reason:safeReason(r.note)
   })),
   stored_quote_counts:(counts.results||[]).map(r=>({
    league:safeLeague(r.league),
    stored:safeInt(r.total)??0,
    recent_pregame:safeInt(r.recent_pregame)??0
   }))
  };
 }catch(_){
  return {status:"database_unavailable",collector_configured:configured,
   recent_runs:[],recent_attempts:[],stored_quote_counts:[]};
 }
}
