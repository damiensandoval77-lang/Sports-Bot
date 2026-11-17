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
  const [runs,attempts,counts]=await Promise.all([
   env.DB.prepare("SELECT completed_at,outcome,detail FROM scheduler_runs WHERE job=? ORDER BY run_id DESC LIMIT 5").bind(JOB).all(),
   env.DB.prepare("SELECT league,event_id,requested_at,outcome,charged_credits,quotes_stored,note FROM odds_api_attempts ORDER BY id DESC LIMIT 5").all(),
   env.DB.prepare("SELECT league,COUNT(*) AS total, SUM(CASE WHEN event_start>? AND market_observed_at>? THEN 1 ELSE 0 END) AS recent_pregame FROM odds_api_quotes GROUP BY league").bind(future,since).all()
  ]);
  return {
   status:"ok",
   collector_configured:configured,
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
