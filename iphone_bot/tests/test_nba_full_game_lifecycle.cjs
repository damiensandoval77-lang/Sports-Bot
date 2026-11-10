"use strict";
// OFFLINE E2E lifecycle gate. No sportsbook requests and no real wager creation.
// Simulates before-tip capture, disappearance from next provider fetch,
// start of all eight games, live stat observations and final outcomes.
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs");
const L=require("../../docs/live-prop-tracker.js");

const games=[
 ["Cleveland Cavaliers @ Charlotte Hornets","CLE","CHA"],
 ["Los Angeles Lakers @ Atlanta Hawks","LAL","ATL"],
 ["Washington Wizards @ Detroit Pistons","WAS","DET"],
 ["Memphis Grizzlies @ Toronto Raptors","MEM","TOR"],
 ["Indiana Pacers @ Dallas Mavericks","IND","DAL"],
 ["Denver Nuggets @ Houston Rockets","DEN","HOU"],
 ["San Antonio Spurs @ Phoenix Suns","SAS","PHX"],
 ["New Orleans Pelicans @ Golden State Warriors","NOP","GSW"]
];
const start="2026-11-10T00:00:00Z";
const pretip="2026-11-09T23:58:00Z";
const quoteTime="2026-11-09T23:54:00Z";
const liveTime=Date.parse("2026-11-10T00:16:00Z");
function quote(game,team,i,stat,line){
 return {id:"pp_test_"+i+"_"+stat,player:"Player "+i,team,game,stat,
  line,starts_at:start,observed_at:quoteTime,source_generated_at:pretip,
  source:"independent_prizepicksapi_com",is_demo:false,
  tier:"standard",more_tier:"standard",less_tier:"standard"};
}
function forecast(game,team,i,stat,projection,line=null){
 return {player:"Player "+i,player_id:"test_"+i,team,game,stat,start,
  projection,combined_projection:projection,line,is_pregame_prediction:true,
  captured_at:"2026-11-09T23:40:00Z",
  board_generated_at:"2026-11-09T23:40:00Z"};
}
const archive={status:"VERIFIED_PRETIP_PRIZEPICKS_QUOTES_ARCHIVE",
 quotes:games.flatMap(([game,team],i)=>[
  quote(game,team,i,"PTS",15.5+i),quote(game,team,i,"REB",4.5),
  quote(game,team,i,"AST",2.5),quote(game,team,i,"PRA",22.5+i)
 ])};
test("all eight synthetic games: pretip source survives provider outage and tipoff",()=>{
 const seen=new Set();
 for(const [game,team,,i] of games.map((g,i)=>[...g,i])){
  // One real frozen market, one archived AI-only market and two verified
  // line-only markets must ALL survive the same live-game transition.
  const priced=forecast(game,team,i,"PTS",20,15.5+i);
  const noLine=forecast(game,team,i,"REB",5.4);
  const mixed=L.mergeLiveForecasts([priced],[noLine],game);
  const extra=L.quoteOnlyLiveRows(archive,game,mixed,liveTime);
  const cards=[...mixed,...extra];
  assert.equal(cards.length,4,game);
  assert.deepEqual(cards.map(x=>x.stat).sort(),["AST","PRA","PTS","REB"],game);
  assert.equal(cards.find(x=>x.stat==="PTS").line,15.5+i);
  assert.equal(cards.find(x=>x.stat==="REB").line,null);
  assert.equal(cards.find(x=>x.stat==="AST").projection,null);
  assert.equal(cards.find(x=>x.stat==="PRA").projection,null);
  for(const card of cards){
   const observed=L.archivedPregameLine(card,archive);
   assert.equal(observed?.status,"OBSERVED_PRETIP_QUOTE_NOT_FROZEN_PICK");
   assert.equal(observed?.source,"independent_prizepicksapi_com");
   assert.ok(observed.line>0,game+" "+card.stat);
   seen.add(game+"|"+card.stat);
   const players=[{player:card.player,team,stats:{PTS:10,REB:3,AST:2,PRA:15}}];
   const matched=L.matchPlayer(players,card);
   assert.ok(matched,game+" "+card.stat);
  }
 }
 assert.equal(seen.size,32);
});
test("a later missing or post-tip provider board must not invent or erase a frozen line",()=>{
 const [game,team]=games[0],original=forecast(game,team,0,"PTS",20,15.5);
 const historical=L.archivedPregameLine(original,archive);
 assert.equal(historical.line,15.5);
 const freshPostTip={status:"LIVE_THIRD_PARTY_PRIZEPICKS_LINES",
  source:"independent_prizepicksapi_com",
  generated_at:"2026-11-10T00:10:00Z",
  board_offers:[{...archive.quotes[0],observed_at:"2026-11-10T00:09:00Z",line:28.5}]};
 assert.equal(L.observedPregameLine(original,freshPostTip),null);
 assert.equal(L.archivedPregameLine(original,archive).line,15.5);
 assert.equal(original.line,15.5);
});
test("final grading is separate from source quotes and refuses missing stats",()=>{
 const [game,team]=games[0];
 const priced=forecast(game,team,0,"PTS",20,15.5);
 const live={status:{type:{state:"in"},period:3,displayClock:"6:00"}};
 const finished={status:{type:{state:"post"},period:4,displayClock:"0:00"}};
 assert.equal(L.evaluate(priced,10,live).label,"ON_PACE");
 assert.equal(L.evaluate(priced,20,finished).label,"FINAL_HIT");
 assert.equal(L.evaluate(priced,12,finished).label,"FINAL_MISS");
 assert.equal(L.evaluate(priced,null,finished).label,"STATS_UNAVAILABLE");
 const quoteOnly=L.quoteOnlyLiveRows(archive,game,[],liveTime)[0];
 assert.equal(quoteOnly.projection,null);
 assert.equal(quoteOnly.line,null);
 assert.equal(L.isFrozenForecast(quoteOnly),false);
 assert.equal(L.evaluate(quoteOnly,10,finished).label,"NO_MODEL_LEAN");
});
test("production saved pretip quote archive is internally consistent",()=>{
 const p=JSON.parse(fs.readFileSync("docs/prizepicks_pregame_line_archive.json","utf8"));
 assert.equal(p.status,"VERIFIED_PRETIP_PRIZEPICKS_QUOTES_ARCHIVE");
 assert.equal(p.count,p.quotes.length);
 assert.ok(p.count>0);
 for(const q of p.quotes){
  assert.equal(q.source,"independent_prizepicksapi_com");
  assert.equal(q.is_demo,false);
  assert.equal(q.tier,q.more_tier);
  assert.equal(q.tier,q.less_tier);
  assert.ok(Date.parse(q.observed_at)<=Date.parse(q.source_generated_at));
  assert.ok(Date.parse(q.source_generated_at)<Date.parse(q.starts_at));
 }
});
