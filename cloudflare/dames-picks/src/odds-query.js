/* Small, read-only D1 views for the Cloudflare staging market explorer.
 * Never retrieves provider odds on page visits. Missing data is unavailable,
 * not zero, "live", a model prediction, or a final settlement.
 */
import {catalogFor,apiCatalog} from "./odds-catalog.js";
import {creditBudget} from "./odds-collector.js";

export async function readMarketBoard(db,{league="NBA",limit=60,now=Date.now()}={}){
 const cat=catalogFor(league);
 if(!cat)return {status:"invalid_league",quotes:[],source:"the_odds_api"};
 if(typeof db?.prepare!=="function")
  return {status:"database_not_connected",quotes:[],source:"the_odds_api"};
 const max=Math.max(1,Math.min(100,Number.isSafeInteger(limit)?limit:60));
 const future=new Date(now).toISOString();
 // Historical odds quotes remain immutable; never label yesterday's line live.
 const earliest=new Date(now-90*60000).toISOString();
 try{
  const result=await db.prepare(
   "SELECT league,event_id,event_start,home_team,away_team,bookmaker,market_key,player,standard_line,"+
   "over_price,under_price,price_type,market_observed_at,captured_at,previous_line FROM ("+
   " SELECT league,event_id,event_start,home_team,away_team,bookmaker,market_key,player,player_key,standard_line,"+
   " over_price,under_price,price_type,market_observed_at,captured_at,"+
   " ROW_NUMBER() OVER (PARTITION BY league,event_id,bookmaker,market_key,player_key ORDER BY market_observed_at DESC,captured_at DESC) AS rnk,"+
   " LAG(standard_line) OVER (PARTITION BY league,event_id,bookmaker,market_key,player_key ORDER BY market_observed_at ASC,captured_at ASC) AS previous_line"+
   " FROM odds_api_quotes WHERE league=? AND event_start>? AND market_observed_at>?)"+
   " WHERE rnk=1 ORDER BY event_start ASC, bookmaker ASC, player ASC LIMIT ?"
  ).bind(cat.league,future,earliest,max).all();
  const quotes=(result?.results||[]).map(p=>({
   league:p.league,event_id:p.event_id,event_start:p.event_start,
   matchup:p.away_team+" @ "+p.home_team,
   bookmaker:p.bookmaker,market_key:p.market_key,player:p.player,
   line:p.standard_line,
   over_price:p.price_type==="indicative_dfs"?null:p.over_price,
   under_price:p.price_type==="indicative_dfs"?null:p.under_price,
   bookmaker_price_type:p.price_type,
   previous_line:p.previous_line,
   line_change:p.previous_line===null?null:Number((p.standard_line-p.previous_line).toFixed(2)),
   observed_at:p.market_observed_at,captured_at:p.captured_at,
   player_identity_verified:false,model_projection:null,hit_estimate:null,
   grade:null,is_standard:true
  }));
  return {status:quotes.length?"available":"no_recent_standard_lines",source:"the_odds_api",
    verified_data:"provider_market_quotes_only",limit:max,quotes,
    footnote:"No AI probabilities or player stats are inferred from bookmaker odds."};
 }catch(_){
  return {status:"market_schema_unavailable",quotes:[],source:"the_odds_api"};
 }
}
export async function readOddsBudget(db,env={},now=Date.now()){
 const config=creditBudget(env),month=new Date(now).toISOString().slice(0,7);
 if(typeof db?.prepare!=="function")
  return {status:"database_not_connected",config,usage:null};
 try{
  const row=await db.prepare(
   "SELECT month_utc,day_utc,used_credits,reserved_credits,daily_used,daily_reserved,provider_remaining,updated_at "+
   "FROM odds_api_budget WHERE month_utc=?"
  ).bind(month).first();
  return {status:"ok",config,usage:row||{
   month_utc:month,used_credits:0,reserved_credits:0,
   daily_used:0,daily_reserved:0,provider_remaining:null
  },independently_verified_provider_balance:row?.provider_remaining!==null};
 }catch(_){
  return {status:"market_schema_unavailable",config,usage:null};
 }
}
export function readOddsCatalog(){
 return {...apiCatalog(),
  limits:{default_paid_api_enabled:false,archived_alternates_supported:false,
   automatic_grading:false,player_stats_included:false,
   multi_bookmaker_group_max:4,
   markets_requested_per_event_max:7}};
}
