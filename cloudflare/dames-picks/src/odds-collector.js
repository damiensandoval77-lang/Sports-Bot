/**
 * Credit-safe The Odds API adapter. NEVER invoked by browser requests.
 * Explicit opt-in requires all four: PAID_PROVIDER_REQUESTS=enabled,
 * ODDS_API_COLLECTION=enabled, ODDS_API_KEY Worker secret, and positive
 * ODDS_API_MONTHLY_CREDIT_CAP + ODDS_API_DAILY_CREDIT_CAP.
 *
 * Event discovery is free; event player props cost up to the number of
 * requested markets per 1 billed bookmaker group (we request 4 bookmakers).
 * This module never modifies the original model, frozen archive, or grades.
 */
import {CORE_MARKET_KEYS,BOOKMAKERS,catalogFor,isStandardPlayerMarket} from "./odds-catalog.js";
import {normalizeEventQuotes} from "./odds-normalize.js";

const ODDS_HOST="https://api.the-odds-api.com";
const sleep=()=>{};
const boundedInt=(v,min,max)=>Number.isSafeInteger(Number(v))&&Number(v)>=min&&Number(v)<=max?Number(v):null;
const utcDay=ms=>new Date(ms).toISOString().slice(0,10);
const utcMonth=ms=>utcDay(ms).slice(0,7);
const iso=ms=>new Date(ms).toISOString();
const scoreTime=s=>Number.isFinite(Date.parse(s))?Date.parse(s):NaN;

export function isCollectionEnabled(env){
 return env?.PAID_PROVIDER_REQUESTS==="enabled"&&
  env?.ODDS_API_COLLECTION==="enabled"&&
  typeof env?.ODDS_API_KEY==="string"&&env.ODDS_API_KEY.trim().length>=12&&
  boundedInt(env?.ODDS_API_MONTHLY_CREDIT_CAP,1,100000)!==null&&
  boundedInt(env?.ODDS_API_DAILY_CREDIT_CAP,1,10000)!==null&&
  typeof env?.DB?.prepare==="function";
}
export function requestMarketKeys(league,env={}){
 const catalog=catalogFor(league);
 if(!catalog)return [];
 // Exactly the markets with proven model/export contracts are first.
 const core=CORE_MARKET_KEYS[league]||[];
 const allowed=new Set(catalog.markets.filter(m=>m.tier==="expanded"&&m.bet_type==="over_under").map(x=>x.key));
 const extras=String(env.ODDS_API_EXTRA_MARKETS||"").split(",").map(s=>s.trim()).filter(x=>allowed.has(x)).slice(0,2);
 return [...new Set([...core,...extras])].slice(0,7);
}
export function maximumCost(league,env={}){
 const keys=requestMarketKeys(league,env);
 // Four exact bookmakers = one billed region. Never expand to unknown books.
 return keys.length;
}
export function chooseUpcomingEvent(events,now=Date.now(),lastAttemptById=new Map()){
 const min=now+15*60000,max=now+5*3600000;
 return (Array.isArray(events)?events:[])
  .filter(e=>typeof e?.id==="string"&&/^[a-zA-Z0-9]{8,80}$/.test(e.id)&&
   Number.isFinite(scoreTime(e.commence_time))&&scoreTime(e.commence_time)>=min&&
   scoreTime(e.commence_time)<=max&&
   now-(lastAttemptById.get(e.id)||0)>=90*60000)
  .sort((a,b)=>scoreTime(a.commence_time)-scoreTime(b.commence_time))[0]||null;
}
export function creditBudget(env){
 const monthly=boundedInt(env?.ODDS_API_MONTHLY_CREDIT_CAP,1,100000);
 const daily=boundedInt(env?.ODDS_API_DAILY_CREDIT_CAP,1,10000);
 return {monthly_cap:monthly,daily_cap:daily,run_cap:7,provider_group:BOOKMAKERS.join(","),
  price_quote_policy:"DFS prices indicative; not model probabilities",
  source:"The Odds API",collection_enabled:isCollectionEnabled(env)};
}
export async function reserveCredits(db,when,maximum,monthlyCap,dailyCap){
 if(maximum<1||maximum>7||!Number.isSafeInteger(maximum)||dailyCap<maximum||monthlyCap<maximum)
  return false;
 const month=utcMonth(when),day=utcDay(when);
 await db.prepare("INSERT OR IGNORE INTO odds_api_budget(month_utc,day_utc) VALUES(?,?)").bind(month,day).run();
 const statement=await db.prepare(
  "UPDATE odds_api_budget SET reserved_credits=reserved_credits+?, "+
  "daily_used=CASE WHEN day_utc=? THEN daily_used ELSE 0 END, "+
  "daily_reserved=CASE WHEN day_utc=? THEN daily_reserved+? ELSE ? END, "+
  "day_utc=?, updated_at=CURRENT_TIMESTAMP "+
  "WHERE month_utc=? AND used_credits+reserved_credits+?<=? "+
  "AND (CASE WHEN day_utc=? THEN daily_used+daily_reserved ELSE 0 END)+?<=?"
 ).bind(maximum,day,day,maximum,maximum,day,month,maximum,monthlyCap,day,maximum,dailyCap).run();
 return Number(statement?.meta?.changes)===1;
}
export async function settleCredits(db,when,maximum,charged,remaining=null){
 const month=utcMonth(when),day=utcDay(when);
 if(!Number.isInteger(charged)||charged<0||charged>maximum)charged=maximum;
 const result=await db.prepare(
  "UPDATE odds_api_budget SET used_credits=used_credits+?, reserved_credits=reserved_credits-?, "+
  "daily_used=CASE WHEN day_utc=? THEN daily_used+? ELSE daily_used END, "+
  "daily_reserved=CASE WHEN day_utc=? THEN MAX(0,daily_reserved-?) ELSE daily_reserved END, "+
  "provider_remaining=?,updated_at=CURRENT_TIMESTAMP "+
  "WHERE month_utc=? AND reserved_credits>=?"
 ).bind(charged,maximum,day,charged,day,maximum,remaining,month,maximum).run();
 if(Number(result?.meta?.changes)!==1)throw Error("Provider credit settlement did not persist");
 return charged;
}
export async function fetchOddsJSON(fetcher,url,key){
 const controller=new AbortController();
 const timer=setTimeout(()=>controller.abort(),9000);
 try{
  const response=await fetcher(url.toString(),{
   headers:{"x-api-key":key,"accept":"application/json"},
   cache:"no-store",signal:controller.signal
  });
  if(!response.ok)throw Error("ODDS_API_HTTP_"+response.status);
  const body=await response.json();
  const last=boundedInt(response.headers?.get?.("x-requests-last"),0,1000);
  const remaining=boundedInt(response.headers?.get?.("x-requests-remaining"),0,10000000);
  return {body,last,remaining};
 }finally{clearTimeout(timer)}
}
export function oddsURL(league,eventId,marketKeys){
 const sport=catalogFor(league)?.sport_key;
 if(!sport||!/^[a-zA-Z0-9]{8,80}$/.test(eventId))throw Error("Invalid event or league");
 if(!Array.isArray(marketKeys)||!marketKeys.length||marketKeys.length>7||
  marketKeys.some(k=>!isStandardPlayerMarket(league,k)))throw Error("Market keys are not allowed");
 const u=new URL(ODDS_HOST+"/v4/sports/"+sport+"/events/"+eventId+"/odds");
 u.searchParams.set("bookmakers",BOOKMAKERS.join(","));
 u.searchParams.set("markets",marketKeys.join(","));
 u.searchParams.set("oddsFormat","american");
 u.searchParams.set("includeMultipliers","false");
 return u;
}
export function eventsURL(league){
 const sport=catalogFor(league)?.sport_key;
 if(!sport)throw Error("Invalid league");
 return new URL(ODDS_HOST+"/v4/sports/"+sport+"/events");
}
async function recentAttempts(db,league,now){
 const since=iso(now-90*60000);
 const r=await db.prepare(
  "SELECT event_id, MAX(requested_at) AS latest FROM odds_api_attempts WHERE league=? AND requested_at>=? GROUP BY event_id"
 ).bind(league,since).all();
 return new Map((r?.results||[]).map(x=>[x.event_id,scoreTime(x.latest)]));
}
async function insertQuotes(db,records){
 if(records.length>1500)throw Error("Provider returned too many standard markets to store atomically");
 let count=0;
 const sql="INSERT OR IGNORE INTO odds_api_quotes("+
  "quote_key,league,event_id,event_start,home_team,away_team,bookmaker,market_key,player,player_key,"+
  "standard_line,over_price,under_price,price_type,market_observed_at,captured_at,source) "+
  "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)";
 for(let i=0;i<records.length;i+=25){
  const prepared=records.slice(i,i+25).map(p=>{
   const key=[p.league,p.event_id,p.bookmaker,p.market_key,p.player_key,p.line,p.market_observed_at].join("|");
   return db.prepare(sql).bind(key,p.league,p.event_id,p.event_start,p.home_team,p.away_team,p.bookmaker,
    p.market_key,p.player,p.player_key,p.line,p.over_price,p.under_price,p.price_type,
    p.market_observed_at,p.collected_at,p.source);
  });
  const out=await db.batch(prepared);
  count+=out.reduce((s,r)=>s+(Number(r?.meta?.changes)||0),0);
 }
 return count;
}
export async function collectOddsIfEnabled(env,{
 fetcher=fetch,now=Date.now(),leagueOrder=["NBA","NFL"]
}={}){
 if(!isCollectionEnabled(env))return {status:"disabled",paid_requests:0,reason:"no_owner_opt_in"};
 if(env.APP_STAGE!=="staging")return {status:"disabled",paid_requests:0,reason:"not_staging"};
 const monthly=Number(env.ODDS_API_MONTHLY_CREDIT_CAP),daily=Number(env.ODDS_API_DAILY_CREDIT_CAP);
 const db=env.DB;
 try{await db.prepare("SELECT month_utc FROM odds_api_budget LIMIT 1").all()}
 catch(_){return {status:"unavailable",paid_requests:0,reason:"odds_d1_schema_not_installed"}}
 for(const league of leagueOrder){
  if(!catalogFor(league))continue;
  // Events endpoint costs 0 credits; it does not expose player quotes.
  let events;
  try{events=(await fetchOddsJSON(fetcher,eventsURL(league),env.ODDS_API_KEY)).body}
  catch(_){continue}
  const prior=await recentAttempts(db,league,now);
  const event=chooseUpcomingEvent(events,now,prior);
  if(!event)continue;
  const keys=requestMarketKeys(league,env),max=keys.length;
  if(!await reserveCredits(db,now,max,monthly,daily))
   return {status:"budget_blocked",paid_requests:0,league};
  let charged=max,remaining=null,normalized=null,outcome="unknown_cost",note="",stored=0;
  try{
   const response=await fetchOddsJSON(fetcher,oddsURL(league,event.id,keys),env.ODDS_API_KEY);
   if(response.last!==null)charged=Math.min(max,response.last);
   remaining=response.remaining;
   if(response.last!==null&&response.last>max)throw Error("Provider quota anomaly");
   if(response.body?.id!==event.id)throw Error("Event identity mismatch");
   normalized=normalizeEventQuotes(response.body,{league,collectedAt:iso(Date.now())});
   if(normalized.records.length){
    stored=await insertQuotes(db,normalized.records);
    outcome="ok";
   }else outcome="empty";
  }catch(error){outcome="error";note=String(error?.message||"request failed").slice(0,120)}
  finally{
   try{await settleCredits(db,now,max,charged,remaining)}
   catch(_){return {status:"budget_settlement_error",paid_requests:1,league}}
   try{
    await db.prepare(
     "INSERT INTO odds_api_attempts(month_utc,league,event_id,requested_markets,bookmaker_group,requested_at,resolved_at,maximum_reserved,charged_credits,outcome,quotes_stored,provider_remaining,note) "+
     "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)"
    ).bind(utcMonth(now),league,event.id,keys.join(","),BOOKMAKERS.join(","),iso(now),iso(Date.now()),
      max,charged,outcome,stored,remaining,note).run();
   }catch(_){return {status:"attempt_log_failed",paid_requests:1,league}}
  }
  return {status:outcome,paid_requests:1,league,event_id:event.id,requested_markets:keys,
   credits_charged:charged,quotes_stored:stored};
 }
 return {status:"no_eligible_events",paid_requests:0};
}
