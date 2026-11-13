"use strict";
const test=require("node:test"),assert=require("node:assert/strict"),fs=require("node:fs"),vm=require("node:vm");
const app=fs.readFileSync("docs/dames-picks/index.html","utf8");
const feed=fs.readFileSync("docs/dames-picks/feeds.js","utf8");
const landing=fs.readFileSync("docs/index.html","utf8");
const ctx={};vm.createContext(ctx);vm.runInContext(feed,ctx);
const m=ctx.DamesPicksModel;
const start="2026-11-09T02:00:00Z",capture="2026-11-09T00:40:00Z";
const quote={id:"prize-7",player:"Cooper Flagg",team:"DAL",game:"Brooklyn Nets @ Dallas Mavericks",
 stat:"PTS",starts_at:start,observed_at:capture,line:22.5,tier:"standard",more_tier:"standard",
 less_tier:"standard",source:"independent_prizepicksapi_com",is_demo:false};
test("combined Dame's Picks replaces retired legacy board",()=>{
 assert.ok(landing.includes("url=./dames-picks/"));
 assert.ok(app.includes('Dame\'s Picks'));
});
test("one original third-party quote appears only as an unmodeled standard receipt",()=>{
 const rows=m.includeArchivedStandard([],{quotes:[quote]});
 assert.equal(rows.length,1);
 assert.equal(rows[0].line,22.5);
 assert.equal(rows[0].quoteOnly,true);
 assert.equal(rows[0].projection,null);
 assert.equal(rows[0].chance,null);
 assert.equal(rows[0].direction,null);
});
test("goblin, demon, one-sided, demo, malformed and after-tip quotes are rejected",()=>{
 const bad=[
 {...quote,tier:"goblin"},{...quote,tier:"demon"},
 {...quote,more_tier:"demon"},{...quote,less_tier:"goblin"},
 {...quote,less_tier:null},{...quote,is_demo:true},
 {...quote,line:null},{...quote,observed_at:"2026-11-09T03:00:00Z"},
 {...quote,stat:"FAKE"}];
 assert.equal(m.includeArchivedStandard([],{quotes:bad}).length,0);
});
test("verified duplicate quote is not counted twice and later observation wins",()=>{
 const newer={...quote,observed_at:"2026-11-09T00:50:00Z"};
 const rows=m.includeArchivedStandard([],{quotes:[quote,newer]});
 assert.equal(rows.length,1);
 assert.equal(rows[0].captured,newer.observed_at);
});
test("consecutive games for same player and matchup retain separate observed identities",()=>{
 const next={...quote,id:"prize-8",observed_at:"2026-11-10T00:40:00Z",starts_at:"2026-11-10T02:00:00Z"};
 const rows=m.includeArchivedStandard([],{quotes:[quote,next]});
 assert.equal(rows.length,2);
 assert.notEqual(rows[0].start,rows[1].start);
});
test("archive cannot overwrite valid already-frozen AI forecast",()=>{
 const saved={sport:"NBA",player:quote.player,team:quote.team,game:quote.game,stat:quote.stat,
 start:quote.starts_at,line:quote.line,projection:24.6,direction:"MORE",chance:.6,quoteOnly:false};
 const rows=m.includeArchivedStandard([saved],{quotes:[quote]});
 assert.equal(rows.length,1);
 assert.equal(rows[0].projection,24.6);
});
test("active browser does not turn unsupported quick-join research into validated hit picks",()=>{
 assert.ok(app.includes('p.quoteOnly?"NO AI"'));
 assert.ok(app.includes('p.quoteOnly?"NO AI"'));
 assert.ok(app.includes('!x.quoteOnly&&x.projection!==null&&x.direction!==null'));
 assert.ok(app.includes('No sample data is substituted'));
 assert.ok(!app.includes("verifiedQuickPrizePicksJoins("));
});
test("site refreshes frozen outputs independently of 30-second live ESPN player observations",()=>{
 assert.ok(app.includes("setInterval(()=>{if(!document.hidden)refresh().catch(()=>{})},120000)"));
 assert.ok(app.includes("setInterval(()=>{if(!document.hidden)liveTick().catch(()=>{})},30000)"));
 assert.ok(app.includes("getJSON(\"nba_player_tracking_independent.json\")"));
});
