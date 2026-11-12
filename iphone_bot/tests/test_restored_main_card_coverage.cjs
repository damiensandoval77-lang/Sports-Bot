"use strict";
const test=require("node:test"),assert=require("node:assert/strict"),fs=require("node:fs"),vm=require("node:vm");
const ctx={};vm.createContext(ctx);
vm.runInContext(fs.readFileSync("docs/dames-picks/feeds.js","utf8"),ctx);
const m=ctx.DamesPicksModel;
const html=fs.readFileSync("docs/dames-picks/index.html","utf8");
const redirect=fs.readFileSync("docs/index.html","utf8");
const games=[
 "Cleveland Cavaliers @ Charlotte Hornets",
 "Los Angeles Lakers @ Atlanta Hawks",
 "Washington Wizards @ Detroit Pistons",
 "Memphis Grizzlies @ Toronto Raptors",
 "Denver Nuggets @ Houston Rockets",
 "Indiana Pacers @ Dallas Mavericks",
 "San Antonio Spurs @ Phoenix Suns",
 "New Orleans Pelicans @ Golden State Warriors",
];
const starts=games.map((_,i)=>i===4?"2026-11-10T01:30:00Z":"2026-11-10T00:00:00Z");
const archiveFor=(g,i)=>({
 id:"pp_"+i,player:"Player "+i,team:"CLE",game:g,stat:"PTS",line:20.5,
 starts_at:starts[i],observed_at:"2026-11-09T23:00:00Z",
 tier:"standard",more_tier:"standard",less_tier:"standard",is_demo:false
});
const modelBase={player:"Stephen Curry",player_id:"201939",team:"GSW",
 game:games[7],start:starts[7],stat:"PTS",line:28.5,projection:31.2,
 market_updated:"2026-11-09T21:00:00Z",captured_at:"2026-11-09T22:00:00Z",
 pickem_tier:"standard",standard_line_two_sided_verified:true,
 research_only:true,production_replaced:false,grade:"PENDING",
 estimated_hit_chance:{method:"JOINT_2024_25_VALIDATION_RESIDUALS_20K_UNCALIBRATED",draws:20000,calibrated:false,modeled_direction:"More",modeled_selected_probability:.65}};
test("combined app is the only linked dashboard",()=>{
 assert.ok(redirect.includes("url=./dames-picks/"));
 assert.ok(html.includes('Dame\'s Picks'));
});
test("all eight games keep authentic original standard quotes without fake model data",()=>{
 const result=m.includeArchivedStandard([],{quotes:games.map(archiveFor)});
 assert.equal(result.length,8);
 assert.equal(new Set(result.map(x=>x.game)).size,8);
 assert.ok(result.every(x=>x.quoteOnly===true&&x.projection===null&&x.chance===null&&x.direction===null));
});
test("alternate, demo, posttip, and one-sided quotes do not become predictions",()=>{
 const q=archiveFor(games[0],0);
 const bad=[{...q,tier:"goblin"},{...q,tier:"demon"},{...q,is_demo:true},
  {...q,less_tier:"goblin"},{...q,observed_at:"2026-11-10T01:00:00Z"},
  {...q,stat:"NOT_A_MARKET"}];
 assert.equal(m.includeArchivedStandard([],{quotes:bad}).length,0);
});
test("newest valid standard observation wins without duplicating the original market",()=>{
 const q=archiveFor(games[0],0);
 const latest={...q,observed_at:"2026-11-09T23:10:00Z"};
 const result=m.includeArchivedStandard([],{quotes:[q,latest]});
 assert.equal(result.length,1);
 assert.equal(result[0].captured,latest.observed_at);
});
test("existing line-backed model forecast suppresses duplicate quote-only record",()=>{
 const quote=archiveFor(games[0],0);
 const modeled={sport:"NBA",player:quote.player,team:quote.team,game:quote.game,stat:quote.stat,
                start:quote.starts_at,line:quote.line,projection:23.5,quoteOnly:false};
 const result=m.includeArchivedStandard([modeled],{quotes:[quote]});
 assert.equal(result.length,1);
 assert.equal(result[0].projection,23.5);
});
test("separate dates of the same matchup keep independent snapshots",()=>{
 const q=archiveFor(games[0],0);
 const next={...q,id:"pp_next",starts_at:"2026-11-11T00:00:00Z",
              observed_at:"2026-11-10T23:00:00Z"};
 const result=m.includeArchivedStandard([],{quotes:[q,next]});
 assert.equal(result.length,2);
 assert.notEqual(result[0].start,result[1].start);
});
test("frozen model remains immutable when quote-only fallback is merged",()=>{
 const original=m.nba({status:"FROZEN_NEW_AI_ALL_MARKET",records:[modelBase]},null);
 assert.equal(original.length,1);
 const merged=m.includeArchivedStandard(original,{quotes:[archiveFor(games[0],0)]});
 assert.equal(merged.length,2);
 const curry=merged.find(x=>x.player==="Stephen Curry");
 assert.equal(curry.line,28.5);
 assert.equal(curry.projection,31.2);
 assert.equal(curry.grade,"PENDING");
});
test("verified final grades are not confused with pending and DNP",()=>{
 const records=[
 {...modelBase,grade:"GRADED",actual:35,direction_hit:true},
 {...modelBase,stat:"REB",line:6.5,grade:"PENDING"},
 {...modelBase,stat:"AST",line:4.5,grade:"EXCLUDED_VERIFIED_DNP",actual:null}
 ];
 const rows=m.nba({status:"FROZEN_NEW_AI_ALL_MARKET",records},null);
 const summary=m.summarize(rows,null,Date.parse("2026-11-09T22:00:00Z"),"NBA");
 assert.equal(summary.wins,1);
 assert.equal(summary.losses,0);
 assert.equal(summary.pending,1);
});
test("public interface identifies frozen, unmodeled, and DNP status without synthetic wins",()=>{
 assert.ok(html.includes('p.quoteOnly?"NO AI"'));
 assert.ok(html.includes('p.grade==="EXCLUDED_VERIFIED_DNP"'));
 assert.ok(html.includes('Verified standard line · missing frozen AI model'));
 assert.ok(html.includes('No sample data is substituted'));
});
