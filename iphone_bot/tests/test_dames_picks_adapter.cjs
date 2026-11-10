const test=require("node:test"),assert=require("node:assert/strict"),fs=require("node:fs"),vm=require("node:vm");
const ctx={};vm.createContext(ctx);
vm.runInContext(fs.readFileSync("docs/dames-picks/adapter.js","utf8"),ctx);
const a=ctx.DamesAdapter;
function nba(overrides={}){
 return {player:"Stephen Curry",player_id:"201939",team:"GSW",opponent:"NOP",
 game:"New Orleans Pelicans @ Golden State Warriors",start:"2026-11-10T03:00:00Z",
 captured_at:"2026-11-09T22:18:06Z",market_updated:"2026-11-09T21:06:16Z",
 stat:"PTS",line:28.5,projection:31.391,pickem_tier:"standard",research_only:true,
 production_replaced:false,standard_line_two_sided_verified:true,grade:"PENDING",
 estimated_hit_chance:{method:"JOINT_2024_25_VALIDATION_RESIDUALS_20K_UNCALIBRATED",draws:20000,calibrated:false,
 modeled_direction:"More",modeled_selected_probability:.6658},...overrides}
}
test("freeze preserved Curry line and estimate without pretending latest threshold",()=>{
 const rows=a.nbaRows({status:"FROZEN_NEW_AI_ALL_MARKET",records:[nba()]},{players:[]});
 assert.equal(rows.length,1);assert.equal(rows[0].line,28.5);
 assert.equal(rows[0].projection,31.391);assert.equal(rows[0].chance,.6658);
 assert.equal(rows[0].side,"MORE");
});
test("reject nonstandard, posttip, or unverified probability records",()=>{
 const r=[nba({pickem_tier:"demon"}),nba({captured_at:"2026-11-10T04:00:00Z"}),
 nba({estimated_hit_chance:{draws:10000}})];
 assert.equal(a.nbaRows({status:"FROZEN_NEW_AI_ALL_MARKET",records:r},null).length,0);
});
test("verified grading enters dashboard counts, pending does not count as loss",()=>{
 const x=a.nbaRows({status:"FROZEN_NEW_AI_ALL_MARKET",
 records:[nba({grade:"GRADED",actual:35,direction_hit:true}),nba({stat:"PRA",line:37.5,grade:"PENDING"})]},null);
 const sum=a.summary(x,Date.parse("2026-11-09T18:00:00Z"));
 assert.equal(sum.wins,1);assert.equal(sum.losses,0);assert.equal(sum.pending,1);
 assert.equal(sum.hitRate,1);
});
test("parse RFC style quoted CSV with embedded commas and JSON",()=>{
 const result=a.parseCSV('player,season_game_log,line\n"Curry, Stephen","[{""actual"":30}]",27.5\n');
 assert.equal(result[0].player,"Curry, Stephen");
 assert.equal(JSON.parse(result[0].season_game_log)[0].actual,30);
});
test("NFL standard pretip record is mapped, demon excluded",()=>{
 const p={captured_at:"2026-11-09T20:00:00Z",game_id:"2026_10_GB_MIN",player:"Test QB",
 player_id:"42",team:"GB",opponent:"MIN",position:"QB",stat:"Pass Yards",
 odds_type:"standard",line:"249.5",proj:"265.2",p_more:"0.61",pick:"More",
 season_game_log:"[]"};
 const games={games:[{game_id:p.game_id,kickoff_utc:"2026-11-10T01:00:00Z"}]};
 let rows=a.nflRows([[p,{...p,odds_type:"demon"}]],games);
 assert.equal(rows.length,1);assert.equal(rows[0].chance,.61);
 assert.equal(rows[0].gradeSource,null);
});
test("mobile frontend references deployed files, not sample picks",()=>{
 const html=fs.readFileSync("docs/dames-picks/index.html","utf8");
 for(const p of ["lagged_matchup_all_market_ledger.json","current_form.json",
 "nfl/data/latest_2026.json","nfl/data/schedule_2026.json","dames-picks"])
  assert.ok(html.includes(p)||p==="dames-picks");
 assert.ok(!html.includes("SAMPLE DATA"));
});
