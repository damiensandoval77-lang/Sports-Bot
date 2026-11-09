const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const html=fs.readFileSync("docs/index.html","utf8");
const from=html.indexOf("function verifiedQuickPrizePicksJoins(");
const to=html.indexOf("function groupAI(rows){",from);
assert.ok(from>=0&&to>from,"Join function in dashboard");
const now=Date.parse("2026-11-09T01:00:00Z");
const norm=s=>String(s||"").toLowerCase().replace(/[^a-z0-9]/g,"");
const isRecent=(stamp,hours)=>Date.parse(stamp)<=now+600000&&now-Date.parse(stamp)<hours*3600000;
const join=new Function("norm","isRecent","Date",html.slice(from,to)+";return verifiedQuickPrizePicksJoins;")(norm,isRecent,Date);
const nowTime="2026-11-09T00:40:00Z",start="2026-11-09T02:00:00Z";
const player={player:"Cooper Flagg",player_id:"5041939",team:"DAL"};
const forecast={status:"PREGAME_PROJECTIONS_NO_LINES",generated_at:"2026-11-09T00:50:00Z",
 predictions:[{...player,game:"Brooklyn Nets @ Dallas Mavericks",stat:"PTS",start,projection:24.6,is_pregame_prediction:true}]};
const offer={id:"prize-7",player:"Cooper Flagg",team:"DAL",game:"Brooklyn Nets @ Dallas Mavericks",
 stat:"PTS",starts_at:start,observed_at:nowTime,line:22.5,more_tier:"standard",
 less_tier:"standard",source:"independent_prizepicksapi_com",is_demo:false};
const source={status:"LIVE_THIRD_PARTY_PRIZEPICKS_LINES",provider_status:"fresh",
 generated_at:nowTime,board_offers:[offer]};
function quick(a=source,b=forecast,r=[player],t=now){return join(a,b,r,t)}
test("only genuine matched offer produces honest raw direction",()=>{
 const rows=quick();
 assert.equal(rows.length,1);
 assert.equal(rows[0].line,22.5);
 assert.equal(rows[0].projection,24.6);
 assert.equal(rows[0].combined_difference,2.1);
 assert.equal(rows[0].quick_research_only,true);
 assert.equal(rows[0].reliability_screen.status,"PASS");
 assert.equal(rows[0].combined_simulation,undefined);
});
test("missing lines, stale provider, or already tipped fixture yields no cards",()=>{
 assert.deepEqual(quick({...source,board_offers:[]}),[]);
 assert.deepEqual(quick({...source,generated_at:"2026-11-08T05:00:00Z"}),[]);
 assert.deepEqual(quick(source,forecast,[player],Date.parse("2026-11-09T03:00:00Z")),[]);
});
test("reject mismatched player, teams, source and stat, and fabricated prices",()=>{
 for(const changes of [
  {player:"Another Player"},{team:"BKN"},{game:"Another Game"},{stat:"REB"},
  {source:"demo"},{is_demo:true},{line:null},{line:NaN},
  {observed_at:"2026-11-08T02:00:00Z"},{starts_at:"2026-11-09T03:00:00Z"}]){
  assert.deepEqual(quick({...source,board_offers:[{...offer,...changes}]}),[]);
 }
});
test("reject unmatched current-season roster, conflicting duplicate identity",()=>{
 assert.deepEqual(quick(source,forecast,[{...player,player_id:"wrong"}]),[]);
 assert.deepEqual(quick(source,forecast,[player,player]),[]);
});
test("reject after-tipoff model and missing pretip capture",()=>{
 assert.deepEqual(quick(source,{...forecast,generated_at:"2026-11-09T03:00:00Z"}),[]);
});

const publishedStart=html.indexOf("function verifiedPublishedPrizePicksJoins(");
const publishedEnd=html.indexOf("function groupAI(rows){",publishedStart);
assert.ok(publishedStart>=0&&publishedEnd>publishedStart,"Published join function available");
const published=new Function("norm","isRecent","Date",html.slice(publishedStart,publishedEnd)+
 ";return verifiedPublishedPrizePicksJoins;")(norm,isRecent,Date);
const publishedRow={
 player:"Cooper Flagg",player_id:"5041939",team:"DAL",opponent:"BKN",
 game:"Brooklyn Nets @ Dallas Mavericks",stat:"PTS",start,
 line:22.5,projection:24.6,difference:2.1,source:"independent_prizepicksapi_com",
 observed_at:nowTime,model_generated_at:forecast.generated_at,
 provider_projection_id:"prize-7",research_only:true,
 more_tier:"standard",less_tier:"standard"
};
const publishedBoard={
 status:"FRESH_RESEARCH_ONLY_PRIZEPICKS_AI_COMPARISONS",
 research_only:true,generated_at:nowTime,
 provider_generated_at:nowTime,model_generated_at:forecast.generated_at,
 comparisons:[publishedRow]
};
test("real published quick-join converts to PrizePicks card without invented probabilities",()=>{
 const result=published(publishedBoard,[player],now);
 assert.equal(result.length,1);
 assert.equal(result[0].sportsbook,"PrizePicks");
 assert.equal(result[0].line,22.5);
 assert.equal(result[0].projection,24.6);
 assert.equal(result[0].combined_simulation,undefined);
 assert.equal(result[0].confidence_percent,null);
 assert.equal(result[0].reliability_screen.validated,false);
});
test("published joins reject stale offer, started game, bad roster and stale aggregate",()=>{
 assert.deepEqual(published({...publishedBoard,generated_at:"2026-11-08T00:00:00Z"},[player],now),[]);
 assert.deepEqual(published({...publishedBoard,comparisons:[{...publishedRow,observed_at:"2026-11-08T00:00:00Z"}]},[player],now),[]);
 assert.deepEqual(published(publishedBoard,[{...player,player_id:"wrong"}],now),[]);
 assert.deepEqual(published(publishedBoard,[player],Date.parse("2026-11-09T03:00:00Z")),[]);
});
test("dashboard fetches published quick join before trying to reconstruct manually",()=>{
 assert.ok(html.includes('fetchJSON("ai_prizepicks_quick_join.json")'));
 const publishedUse=html.indexOf("verifiedPublishedPrizePicksJoins(publishedQuick.value,form)");
 const rebuildUse=html.indexOf("verifiedQuickPrizePicksJoins(pp.value,noLineForecast,form)");
 assert.ok(publishedUse>0&&rebuildUse>publishedUse);
});
