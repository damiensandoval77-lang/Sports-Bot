/* Read-only deterministic Odds API player-prop normalizer.
 * This is a MARKET QUOTE adapter, not a model probability, player statistic,
 * official PrizePicks feed or grading result.
 */
import {BOOKMAKERS,DFS_BOOKMAKERS,catalogFor,isStandardPlayerMarket} from "./odds-catalog.js";
const normalizeName=s=>String(s||"").normalize("NFKD").toLowerCase().replace(/[\u0300-\u036f]/g,"").replace(/[^a-z0-9]+/g,"");
const validText=(s,max=150)=>typeof s==="string"&&s.trim().length>1&&s.trim().length<=max;
const time=v=>typeof v==="string"&&Number.isFinite(Date.parse(v))?Date.parse(v):NaN;
const validLine=v=>typeof v==="number"&&Number.isFinite(v)&&v>=0&&v<=1000;
const validPrice=v=>typeof v==="number"&&Number.isFinite(v)&&Math.abs(v)>=100&&Math.abs(v)<=100000;
function defaultMultiplier(o){
 const m=o?.multiplier??o?.mult;
 return m===undefined||m===null||m===1||m===1.0||m==="1"||m==="1.0";
}
export function normalizeEventQuotes(payload,{league,collectedAt=new Date().toISOString()}={}){
 const catalog=catalogFor(league);
 if(!catalog)throw Error("Unsupported league");
 const now=time(collectedAt),start=time(payload?.commence_time);
 if(!Number.isFinite(now)||!Number.isFinite(start)||start<=now||
    now-start>120000||start-now>96*3600000||
    payload?.sport_key!==catalog.sport_key||
    !validText(payload?.id,80)||!validText(payload?.home_team,100)||!validText(payload?.away_team,100)||
    payload.home_team===payload.away_team)
  return {records:[],rejected:{invalid_event:1},providers:[]};
 const records=[],rejected=Object.create(null),providers=new Set();
 const drop=reason=>{rejected[reason]=(rejected[reason]||0)+1};
 for(const book of Array.isArray(payload.bookmakers)?payload.bookmakers:[]){
  if(!BOOKMAKERS.includes(book.key))continue;
  providers.add(book.key);
  for(const market of Array.isArray(book.markets)?book.markets:[]){
   if(!isStandardPlayerMarket(league,market.key)){drop("unsupported_or_alternate_market");continue}
   const observed=time(market.last_update);
   if(!Number.isFinite(observed)||observed>now+120000||observed>=start){
    drop("no_verified_pretip_market_timestamp");continue
   }
   // Provider outcome format: {name:'Over',description:'Player Name',point:NN.N,price:-110}
   const grouped=new Map();
   for(const outcome of Array.isArray(market.outcomes)?market.outcomes:[]){
    const side=String(outcome?.name||"").toLowerCase();
    if(!["over","under"].includes(side)||!validText(outcome?.description,120)||
       !validLine(outcome?.point)||!defaultMultiplier(outcome)){
      drop("unsupported_side_player_line_or_multiplier");continue
    }
    const player=outcome.description.trim().replace(/\s+/g," ");
    const key=normalizeName(player)+"|"+String(outcome.point);
    const old=grouped.get(key)||{player,point:outcome.point,over:[],under:[]};
    old[side].push(outcome);grouped.set(key,old);
   }
   for(const group of grouped.values()){
    // Multiple same-direction offers for identical player and line are ambiguous.
    if(group.over.length!==1||group.under.length!==1){
     drop("missing_or_ambiguous_two_sided_standard");continue;
    }
    const over=group.over[0],under=group.under[0];
    const dfs=DFS_BOOKMAKERS.includes(book.key);
    const os=validPrice(over.price)?over.price:null;
    const us=validPrice(under.price)?under.price:null;
    if(!dfs&&(os===null||us===null)){drop("missing_sportsbook_price");continue}
    records.push({
     source:"the_odds_api",
     league:catalog.league,
     event_id:String(payload.id),
     event_start:new Date(start).toISOString(),
     home_team:payload.home_team,
     away_team:payload.away_team,
     bookmaker:book.key,
     market_key:market.key,
     player:group.player,
     player_key:normalizeName(group.player),
     player_team:null,
     player_id:null,
     identity_verified:false,
     line:group.point,
     over_price:os,
     under_price:us,
     price_type:dfs?"indicative_dfs":"sportsbook_american",
     market_observed_at:new Date(observed).toISOString(),
     collected_at:new Date(now).toISOString(),
     market_tier:"standard",
     is_alternate:false,
     source_verified_by_response:true
    });
   }
  }
 }
 records.sort((a,b)=>a.bookmaker.localeCompare(b.bookmaker)||a.market_key.localeCompare(b.market_key)||a.player_key.localeCompare(b.player_key)||a.line-b.line);
 return {records,rejected,providers:[...providers].sort()};
}
export function matchableToFrozenForecast(quote,forecast){
 // A market quote may be used as a research comparison only after an actual
 // roster identity matcher has linked a canonical player+team+exact event.
 // This function NEVER merges or changes an already-frozen forecast.
 return Boolean(quote?.identity_verified===true&&forecast?.identity_verified===true&&
   quote?.player_id&&forecast?.playerId&&String(quote.player_id)===String(forecast.playerId)&&
   quote?.event_id&&quote.event_id===forecast?.provider_event_id&&
   quote?.market_tier==="standard"&&quote?.is_alternate===false&&
   quote?.bookmaker==="prizepicks"&&forecast?.sport===quote.league);
}
