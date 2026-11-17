import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import worker,{ensureOddsSchema} from "../src/worker.js";
import {MARKET_CATALOG,BOOKMAKERS,CORE_MARKET_KEYS,isStandardPlayerMarket} from "../src/odds-catalog.js";
import {normalizeEventQuotes,matchableToFrozenForecast} from "../src/odds-normalize.js";
import {isCollectionEnabled,requestMarketKeys,maximumCost,oddsURL,eventsURL,
 chooseUpcomingEvent,reserveCredits,settleCredits,fetchOddsJSON,collectOddsIfEnabled} from "../src/odds-collector.js";
import {readMarketBoard,readOddsBudget,readOddsCatalog,noVigMarketOverProbability} from "../src/odds-query.js";
import {BOOTSTRAP_0002_ODDS_SQL} from "../src/bootstrap-0002-odds.js";

const iso="2026-11-17T18:00:00Z",future="2026-11-17T21:00:00Z";
const fixture={
 id:"a512a48a58c4329048174217b2cc7ce0",sport_key:"basketball_nba",
 commence_time:future,home_team:"Boston Celtics",away_team:"New York Knicks",
 bookmakers:[
  {key:"prizepicks",markets:[
   {key:"player_points",last_update:"2026-11-17T17:50:00Z",outcomes:[
    {name:"Over",description:"Player Example",point:24.5,price:-110},
    {name:"Under",description:"Player Example",point:24.5,price:-110}
   ]},
   {key:"player_points_alternate",last_update:"2026-11-17T17:50:00Z",outcomes:[
    {name:"Over",description:"Player Example",point:19.5,price:-110},
    {name:"Under",description:"Player Example",point:19.5,price:-110}
   ]}
  ]},
  {key:"underdog",markets:[
   {key:"player_rebounds",last_update:"2026-11-17T17:52:00Z",outcomes:[
    {name:"Over",description:"Another Player",point:8.5,price:100},
    {name:"Under",description:"Another Player",point:8.5,price:-110}
   ]}
  ]},
  {key:"fanduel",markets:[
   {key:"player_assists",last_update:"2026-11-17T17:55:00Z",outcomes:[
    {name:"Over",description:"Third Player",point:5.5,price:-120},
    {name:"Under",description:"Third Player",point:5.5,price:100}
   ]}
  ]}
 ]
};

test("published market catalog explicitly excludes alternate markets and distinguishes market data from stats",()=>{
 assert.equal(MARKET_CATALOG.NBA.markets.length>=15,true);
 assert.equal(MARKET_CATALOG.NFL.markets.length>=15,true);
 assert.equal(CORE_MARKET_KEYS.NBA.length,4);
 assert.equal(CORE_MARKET_KEYS.NFL.length,5);
 assert.equal(isStandardPlayerMarket("NBA","player_points"),true);
 assert.equal(isStandardPlayerMarket("NBA","player_points_alternate"),false);
 assert.equal(isStandardPlayerMarket("NBA","player_anytime_td"),false);
 assert.equal(readOddsCatalog().limits.player_stats_included,false);
});
test("new player props, combined lines and existing core markets are catalogued separately",()=>{
 for(const x of ["player_points","player_threes","player_steals","player_blocks","player_turnovers",
  "player_points_rebounds","player_points_assists","player_rebounds_assists"])
  assert.ok(MARKET_CATALOG.NBA.markets.some(p=>p.key===x),x);
 for(const x of ["player_receptions","player_reception_yds","player_rush_yds","player_pass_yds",
  "player_pass_attempts","player_pass_completions","player_rush_reception_yds"])
  assert.ok(MARKET_CATALOG.NFL.markets.some(p=>p.key===x),x);
});
test("the exact two-sided standard PrizePicks, Underdog and FanDuel lines are parsed without fantasy alternative prices",()=>{
 const out=normalizeEventQuotes(fixture,{league:"NBA",collectedAt:iso});
 assert.equal(out.records.length,3);
 assert.deepEqual(out.providers,["fanduel","prizepicks","underdog"]);
 assert.ok(out.records.every(p=>p.market_tier==="standard"&&p.is_alternate===false));
 assert.equal(out.rejected.unsupported_or_alternate_market,1);
 const prize=out.records.find(x=>x.bookmaker==="prizepicks");
 assert.equal(prize.line,24.5);
 assert.equal(prize.player_id,null);
 assert.equal(prize.identity_verified,false);
 assert.equal(prize.price_type,"indicative_dfs");
 assert.equal(out.records.find(x=>x.bookmaker==="fanduel").price_type,"sportsbook_american");
});
test("one-sided, duplicated, non-default multiplier, and mismatched lines never become standard quotes",()=>{
 const edit=structuredClone(fixture);
 edit.bookmakers=[{key:"prizepicks",markets:[{key:"player_points",last_update:"2026-11-17T17:50:00Z",outcomes:[
  {name:"Over",description:"Player Example",point:24.5,price:-110},
  {name:"Over",description:"Player Example",point:24.5,price:-110},
  {name:"Under",description:"Player Example",point:24.5,price:-110},
  {name:"Over",description:"Different Player",point:20.5,multiplier:1.5},
  {name:"Under",description:"Another Player",point:22.5}
 ]}]}];
 const r=normalizeEventQuotes(edit,{league:"NBA",collectedAt:iso});
 assert.equal(r.records.length,0);
 assert.ok(r.rejected.missing_or_ambiguous_two_sided_standard>=2);
 assert.ok(r.rejected.unsupported_side_player_line_or_multiplier>=1);
});
test("stale, in-play, mismatched sport, or post-tip market data cannot be marked pregame",()=>{
 for(const e of [
  {...fixture,sport_key:"americanfootball_nfl"},
  {...fixture,commence_time:"2026-11-17T17:59:59Z"},
  {...fixture,home_team:"New York Knicks"}
 ]){
  assert.equal(normalizeEventQuotes(e,{league:"NBA",collectedAt:iso}).records.length,0);
 }
 const late=structuredClone(fixture);
 late.bookmakers[0].markets[0].last_update="2026-11-17T22:00:00Z";
 assert.equal(normalizeEventQuotes(late,{league:"NBA",collectedAt:iso}).records.find(x=>x.bookmaker==="prizepicks"),undefined);
});
test("a market record cannot silently overwrite a frozen AI prediction without verified player and event identities",()=>{
 const q=normalizeEventQuotes(fixture,{league:"NBA",collectedAt:iso}).records.find(x=>x.bookmaker==="prizepicks");
 const f={sport:"NBA",playerId:"123",provider_event_id:q.event_id,identity_verified:true};
 assert.equal(matchableToFrozenForecast(q,f),false);
 assert.equal(matchableToFrozenForecast({...q,identity_verified:true,player_id:"123"},f),true);
});
test("collector defaults to no paid API access even if D1 and a secret exist",async()=>{
 const env={APP_STAGE:"staging",DB:{prepare(){throw Error("D1 should not be queried")}},
  ODDS_API_KEY:"test_key_at_least_12chars",PAID_PROVIDER_REQUESTS:"disabled",
  ODDS_API_COLLECTION:"enabled",ODDS_API_MONTHLY_CREDIT_CAP:"100",ODDS_API_DAILY_CREDIT_CAP:"10"};
 assert.equal(isCollectionEnabled(env),false);
 const result=await collectOddsIfEnabled(env,{fetcher(){throw Error("NO NETWORK")},now:Date.parse(iso)});
 assert.deepEqual(result,{status:"disabled",paid_requests:0,reason:"no_owner_opt_in"});
 assert.equal(isCollectionEnabled({...env,PAID_PROVIDER_REQUESTS:"enabled",ODDS_API_COLLECTION:"disabled"}),false);
 assert.equal(isCollectionEnabled({...env,PAID_PROVIDER_REQUESTS:"enabled",ODDS_API_COLLECTION:"enabled",ODDS_API_KEY:""}),false);
});
test("market requests have 4 providers, only one billed bookmaker group, and zero alternate markets",()=>{
 assert.deepEqual(BOOKMAKERS,["prizepicks","underdog","fanduel","draftkings"]);
 const markets=requestMarketKeys("NBA",{ODDS_API_EXTRA_MARKETS:"player_threes,player_turnovers,player_steals,player_points_alternate"});
 assert.equal(markets.length,6);
 assert.ok(!markets.some(x=>x.includes("alternate")));
 assert.equal(maximumCost("NBA"),4);
 const url=oddsURL("NBA",fixture.id,markets);
 assert.equal(url.searchParams.get("bookmakers"),"prizepicks,underdog,fanduel,draftkings");
 assert.equal(url.searchParams.get("includeMultipliers"),"false");
 assert.equal(url.searchParams.has("apiKey"),false);
 assert.equal(eventsURL("NFL").pathname,"/v4/sports/americanfootball_nfl/events");
});
test("free discovery picks only eligible upcoming games and throttles repeated event requests",()=>{
 const now=Date.parse(iso),events=[{id:fixture.id,commence_time:future},
  {id:"1234567890abcdef",commence_time:"2026-11-17T18:05:00Z"},
  {id:"fedcba0987654321",commence_time:"2026-11-17T20:00:00Z"}];
 assert.equal(chooseUpcomingEvent(events,now)?.id,"fedcba0987654321");
 assert.equal(chooseUpcomingEvent(events,now,new Map([["fedcba0987654321",now]]))?.id,fixture.id);
});
test("provider auth stays in a header, and absent quota headers are UNKNOWN rather than zero cost",async()=>{
 let urlSeen,headers;
 const mocked=async(u,args)=>{urlSeen=u;headers=args.headers;return {
  ok:true,headers:new Headers(),async json(){return fixture}
 }};
 const result=await fetchOddsJSON(mocked,oddsURL("NBA",fixture.id,CORE_MARKET_KEYS.NBA),"my_own_secret");
 assert.equal(headers["x-api-key"],"my_own_secret");
 assert.ok(!urlSeen.includes("my_own_secret"));
 assert.equal(result.last,null);
 assert.equal(result.remaining,null);
});
test("credit reservation uses one conditional D1 UPDATE; no successful change means zero provider requests",async()=>{
 let changes=0,calls=[];
 const db={prepare(sql){return{bind(...args){calls.push([sql,args]);return this},async run(){return{meta:{changes:sql.startsWith("UPDATE")?changes:1}}}}}};
 assert.equal(await reserveCredits(db,Date.parse(iso),4,100,12),false);
 changes=1;
 assert.equal(await reserveCredits(db,Date.parse(iso),4,100,12),true);
 assert.ok(calls.some(([sql,args])=>sql.includes("used_credits+reserved_credits")&&args.includes(100)));
 assert.equal(await reserveCredits(db,Date.parse(iso),8,100,12),false,"Run cannot request more than 7 markets");
});
test("credit settlement charges last reported amount, or maximum on unknown/network outcome",async()=>{
 let values;
 const db={prepare(sql){return{bind(...args){values=args;return this},async run(){return{meta:{changes:1}}}}}};
 assert.equal(await settleCredits(db,Date.parse(iso),4,2,400),2);
 assert.equal(values[0],2);
 assert.equal(await settleCredits(db,Date.parse(iso),4,null,null),4);
 assert.equal(values[0],4);
});
test("no-vig bookmaker probabilities are LABELLED MARKET IMPLIED, not a model hit rate",()=>{
 assert.equal(noVigMarketOverProbability(-110,-110),0.5);
 assert.equal(noVigMarketOverProbability(null,-110),null);
 const db={prepare(){return{bind(){return this},async all(){return{results:[{
  league:"NBA",event_id:fixture.id,event_start:future,
  home_team:"Boston Celtics",away_team:"New York Knicks",
  bookmaker:"fanduel",market_key:"player_points",player:"Player Example",standard_line:24.5,
  over_price:-110,under_price:-110,price_type:"sportsbook_american",
  market_observed_at:"2026-11-17T17:55:00Z",captured_at:iso,previous_line:25.5
 }]}}}}};
 return readMarketBoard(db,{league:"NBA",now:Date.parse(iso)}).then(r=>{
  assert.equal(r.status,"available");assert.equal(r.quotes[0].sportsbook_no_vig_over,0.5);
  assert.equal(r.quotes[0].line_change,-1);
  assert.equal(r.quotes[0].hit_estimate,null);
  assert.equal(r.quotes[0].model_projection,null);
 });
});
test("market explorer catalog is public, but browsing never consumes paid credits",async()=>{
 const r=await worker.fetch(new Request("https://stage.example/api/v1/odds/catalog"),{});
 assert.equal(r.status,200);
 assert.equal((await r.json()).limits.player_stats_included,false);
 const b=await worker.fetch(new Request("https://stage.example/api/v1/odds/board"),{});
 assert.equal(b.status,503);
 const d=await worker.fetch(new Request("https://stage.example/api/v1/odds/budget"),{});
 assert.equal(d.status,503);
});
test("versioned odds migration is an exact copy and does not edit original stored model grades",()=>{
 const sql=readFileSync(new URL("../migrations/0002_odds_markets.sql",import.meta.url),"utf8");
 assert.equal(sql,BOOTSTRAP_0002_ODDS_SQL);
 assert.match(sql,/CREATE TABLE IF NOT EXISTS odds_api_quotes/);
 assert.ok(!sql.includes("DELETE FROM"));
 assert.ok(!sql.includes("DROP TABLE"));
 assert.ok(!sql.includes("UPDATE lagged_matchup"));
});
test("bookmaker quote collector never runs if it is not explicitly enabled for staging",async()=>{
 const e={APP_STAGE:"production",DB:{prepare(){throw Error("Should never query")}},
  ODDS_API_KEY:"test_key_long_string",PAID_PROVIDER_REQUESTS:"enabled",
  ODDS_API_COLLECTION:"enabled",ODDS_API_MONTHLY_CREDIT_CAP:"100",ODDS_API_DAILY_CREDIT_CAP:"30"};
 const r=await collectOddsIfEnabled(e,{fetcher:()=>{throw Error("NO")},now:Date.parse(iso)});
 assert.deepEqual(r,{status:"disabled",paid_requests:0,reason:"not_staging"});
});

test("with explicit staging opt-in, exactly one paid event request is made and charged by provider headers",async()=>{
 const now=Date.now(),start=new Date(now+3*3600000).toISOString();
 const observed=new Date(now-60000).toISOString();
 const event={...fixture,commence_time:start,bookmakers:[{
  key:"prizepicks",markets:[{key:"player_points",last_update:observed,outcomes:[
   {name:"Over",description:"Player Example",point:24.5,price:-110},
   {name:"Under",description:"Player Example",point:24.5,price:-110}
  ]}]
 }]};
 let paidRequests=0,freeRequests=0,saved=0,attempts=0,settled;
 const db={
  prepare(sql){
   const statement={bind(...args){statement.args=args;return statement},
    async all(){return{results:[]}},
    async run(){
     if(sql.includes("UPDATE odds_api_budget SET used_credits"))settled=statement.args;
     if(sql.startsWith("INSERT INTO odds_api_attempts"))attempts++;
     return {meta:{changes:1}};
    }};
   return statement;
  },
  async batch(statements){saved+=statements.length;return statements.map(()=>({meta:{changes:1}}))}
 };
 const env={APP_STAGE:"staging",DB:db,PAID_PROVIDER_REQUESTS:"enabled",
  ODDS_API_COLLECTION:"enabled",ODDS_API_KEY:"a_valid_test_only_key",
  ODDS_API_MONTHLY_CREDIT_CAP:"100",ODDS_API_DAILY_CREDIT_CAP:"20"};
 const mock=async(url,opts)=>{
  assert.equal(opts.headers["x-api-key"],env.ODDS_API_KEY);
  assert.ok(!url.includes(env.ODDS_API_KEY));
  if(url.endsWith("/events")){freeRequests++;return{
   ok:true,headers:new Headers({"x-requests-last":"0"}),json:async()=>[{id:event.id,commence_time:start}]};}
  paidRequests++;
  assert.equal(new URL(url).searchParams.get("bookmakers"),"prizepicks,underdog,fanduel,draftkings");
  assert.equal(new URL(url).searchParams.get("markets"),CORE_MARKET_KEYS.NBA.join(","));
  return {ok:true,headers:new Headers({"x-requests-last":"1","x-requests-remaining":"499"}),
   json:async()=>event};
 };
 const result=await collectOddsIfEnabled(env,{fetcher:mock,now,leagueOrder:["NBA"]});
 assert.equal(result.status,"ok");
 assert.equal(result.paid_requests,1);
 assert.equal(result.credits_charged,1);
 assert.equal(result.quotes_stored,1);
 assert.equal(freeRequests,1);
 assert.equal(paidRequests,1);
 assert.equal(saved,1);
 assert.equal(attempts,1);
 assert.equal(settled[0],1,"D1 settlement must use actual header cost, not 4 reserved credits");
});
test("the monthly or daily D1 credit ceiling blocks every paid request after free event discovery",async()=>{
 const now=Date.now(),start=new Date(now+3*3600000).toISOString();
 let requests=0;
 const db={
  prepare(sql){return{bind(){return this},async all(){return{results:[]}},
   async run(){return {meta:{changes:sql.startsWith("UPDATE odds_api_budget")?0:1}}}}}
 };
 const env={APP_STAGE:"staging",DB:db,PAID_PROVIDER_REQUESTS:"enabled",
  ODDS_API_COLLECTION:"enabled",ODDS_API_KEY:"another_test_key_12",
  ODDS_API_MONTHLY_CREDIT_CAP:"8",ODDS_API_DAILY_CREDIT_CAP:"5"};
 const mock=async(url)=>{requests++;assert.ok(url.endsWith("/events"),"A blocked budget must not send a paid request");
  return{ok:true,headers:new Headers(),json:async()=>[{id:fixture.id,commence_time:start}]}};
 const r=await collectOddsIfEnabled(env,{fetcher:mock,now,leagueOrder:["NBA"]});
 assert.equal(r.status,"budget_blocked");assert.equal(r.paid_requests,0);assert.equal(requests,1);
});
