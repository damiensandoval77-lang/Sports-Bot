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

test("verified fresh PrizePicks takes priority over nonempty legacy AI sportsbook cards",()=>{
 assert.ok(html.includes('if(publishedQuick.status==="fulfilled"&&formFresh){'));
 assert.ok(!html.includes('if(ai.length===0&&publishedQuick.status==="fulfilled"&&formFresh){'));
 const load=html.indexOf('if(publishedQuick.status==="fulfilled"&&formFresh){');
 const display=html.indexOf('ai=groupAI(joined);',load);
 const check=html.indexOf('if(joined.length){',load);
 assert.ok(check>load&&display>check,"Only actual verified joined rows replace legacy board");
 assert.ok(html.indexOf('if(ai.length===0&&pp.status==="fulfilled"&&formFresh){',display)>display,
           "Browser-side quote matching is still final fallback");
 assert.ok(html.includes('aiMetadata={is_prizepicks:true,no_sportsbook_prices:true,'));
 assert.ok(html.includes('quick_independent_join:true,research_only:true'));
});

test("iPhone default board prioritizes today's real matched lines, not tomorrow's AI-only wall",()=>{
 const from=html.indexOf("function renderAI(){");
 const to=html.indexOf("function groupOdds(",from);
 assert.ok(from>=0&&to>from);
 const view=html.slice(from,to);
 assert.ok(view.includes("const todayBoard=allBoard.filter(p=>easternGameDay(p.start)===today)"));
 assert.ok(view.includes("const board=gameFilter?allBoard:todayBoard;"));
 assert.ok(view.includes("easternGameDay(p.start)===today:p.game===gameFilter"));
 const noLine=html.slice(html.indexOf("function renderNoLineForecast(){"),from);
 assert.ok(noLine.includes("const active=false"));
});
test("iPhone polls free published JSON every 90 seconds and on refocus",()=>{
 assert.ok(html.includes("setInterval(refreshPublishedModels,90000)"));
 assert.ok(html.includes("dashboardLastReload>45000"));
});
test("the raw MORE/LESS line comparison isn't mislabeled as a validated model pass",()=>{
 assert.ok(html.includes('screen.status==="RESEARCH_ONLY"?"UNVALIDATED RESEARCH'));
 assert.ok(html.includes('side==="OVER"?"↑ MORE":side==="UNDER"?"↓ LESS"'));
});

test("a genuine trained 20K PrizePicks board is never replaced by no-sim lightweight fallback",()=>{
 assert.ok(html.includes("const trainedPrizePicksWithSim=aiMetadata?.is_prizepicks===true&&"));
 assert.ok(html.includes("ai.some(p=>combinedSimAvailable(p))"));
 assert.ok(html.includes('if(publishedQuick.status==="fulfilled"&&formFresh){'));
 assert.ok(html.includes('if(trainedPrizePicksWithSim){'));
 assert.ok(html.includes('sim?.simulation_count===20000'));
 assert.ok(html.includes('sim?.calibrated===false'));
});
test("default AI Board never displays tomorrow when today's published PrizePicks quotes are absent",()=>{
 assert.ok(html.includes("const board=gameFilter?allBoard:todayBoard;"));
 assert.ok(html.includes("const todayBoard=allBoard.filter(p=>easternGameDay(p.start)===today)"));
 assert.ok(html.includes('(!gameFilter?easternGameDay(p.start)===today:p.game===gameFilter)'));
});

test("full PrizePicks simulations survive while quick published cards fill absent scheduled games",()=>{
 assert.ok(html.includes("if(trainedPrizePicksWithSim){"));
 assert.ok(html.includes("const trainedGames=new Set(ai.map(p=>p.game))"));
 assert.ok(html.includes("const uncovered=joined.filter(p=>!trainedGames.has(p.game))"));
 assert.ok(html.includes("if(uncovered.length)ai=[...ai,...groupAI(uncovered)]"));
 assert.ok(html.includes('if(p.quick_research_only){'));
 assert.ok(html.includes('if(p.quick_research_only)'));
});
