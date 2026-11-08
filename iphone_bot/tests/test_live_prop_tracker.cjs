"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const L=require("../../docs/live-prop-tracker.js");
const GAME="Denver Nuggets @ Indiana Pacers";
const EVENT={
 id:"401888888",date:"2026-11-08T00:00:00Z",
 competitions:[{competitors:[
  {homeAway:"away",team:{displayName:"Denver Nuggets"}},
  {homeAway:"home",team:{displayName:"Indiana Pacers"}}]}],
 status:{type:{state:"in"},period:3,displayClock:"6:00"}
};
const SUMMARY={
 header:{competitions:[{competitors:[
  {homeAway:"away",team:{displayName:"Denver Nuggets"}},
  {homeAway:"home",team:{displayName:"Indiana Pacers"}}]}]},
 boxscore:{players:[
  {team:{abbreviation:"DEN"},statistics:[{labels:[
   "MIN","FG","3PT","FT","OREB","DREB","REB","AST","STL","BLK","TO","PF","+/-","PTS"],
   athletes:[{athlete:{id:"3112335",displayName:"Nikola Jokic"},
    stats:["25","7-14","1-3","4-4","2","5","7","9","1","0","2","1","+12","19"]}]}]},
  {team:{abbreviation:"IND"},statistics:[{labels:["MIN","REB","AST","PTS"],
   athletes:[{athlete:{id:"other",displayName:"Nikola Jokic"},
      stats:["10","3","1","5"]}]}]}
 ]}
};
function frozen(overrides={}){
 return {board_generated_at:"2026-11-07T21:00:00Z",
  player:"Nikola Jokić",player_id:"203999",team:"DEN",game:GAME,
  start:"2026-11-08T00:00:00Z",stat:"PRA",line:33.5,
  combined_projection:39.0,...overrides};
}
test("ESPN ID located by exact away/home, not odds provider ID",()=>{
 assert.equal(L.identifyGame([EVENT],GAME)?.id,"401888888");
 assert.equal(L.identifyGame([EVENT], "Indiana Pacers @ Denver Nuggets"),null);
 assert.equal(L.identifyGame([EVENT,EVENT],GAME),null);
 assert.equal(L.gameStatus(EVENT),"in");
});
test("only exact header matchup is accepted",()=>{
 assert.equal(L.summaryGameMatch(SUMMARY,GAME),true);
 assert.equal(L.summaryGameMatch(SUMMARY,"Phoenix Suns @ Indiana Pacers"),false);
 assert.equal(L.summaryGameMatch({boxscore:SUMMARY.boxscore},GAME),false);
});
test("ESPN boxscore combines PRA correctly and matches Jokic accents on DEN",()=>{
 const rows=L.athleteRows(SUMMARY);
 assert.equal(rows.length,2);
 const matched=L.matchPlayer(rows,frozen());
 assert.deepEqual(matched.stats,{PTS:19,REB:7,AST:9,PRA:35});
 assert.equal(L.matchPlayer(rows,{...frozen(),team:"NYK"}),null);
 assert.equal(L.matchPlayer([...rows,rows[0]],frozen()),null);
});
test("DNP and missing stat never interpreted as zero",()=>{
 const bad=structuredClone(SUMMARY);
 bad.boxscore.players[0].statistics[0].athletes[0].stats[13]="—";
 assert.equal(L.athleteRows(bad)[0].stats.PTS,null);
 assert.equal(L.athleteRows(bad)[0].stats.PRA,null);
 bad.boxscore.players[0].statistics[0].athletes[0].didNotPlay=true;
 assert.equal(L.athleteRows(bad).length,1);
});
test("must have truly frozen same-game pretip quote",()=>{
 assert.equal(L.isFrozenForecast(frozen()),true);
 assert.equal(L.isFrozenForecast(frozen({board_generated_at:"2026-11-08T00:01:00Z"})),false);
 assert.equal(L.isFrozenForecast(frozen({line:null})),false);
 assert.equal(L.isFrozenForecast(frozen({combined_projection:null,projection:null})),false);
 assert.equal(L.isFrozenForecast(frozen({stat:"BLK"})),false);
});
test("doesn't backfill picks or count duplicated sportsbook rows",()=>{
 assert.equal(L.pickRows([frozen(),frozen(),frozen({stat:"AST",line:8.5})],GAME).length,2);
 assert.equal(L.pickRows([frozen()], "Orlando Magic @ Golden State Warriors").length,0);
});
test("pace is explicitly heuristic, never final grading during game",()=>{
 const outcome=L.evaluate(frozen(),35,EVENT);
 assert.equal(outcome.side,"OVER");
 assert.equal(outcome.label,"OVER_ALREADY_CLEARED");
 const under=L.evaluate(frozen({combined_projection:25,line:29.5}),35,EVENT);
 assert.equal(under.label,"UNDER_ALREADY_LOST");
 const behind=L.evaluate(frozen({line:48.5,combined_projection:55}),35,EVENT);
 assert.equal(behind.label,"ON_PACE");
 assert.equal(behind.pace,56);
 const early={...EVENT,status:{type:{state:"in"},period:1,displayClock:"10:30"}};
 assert.equal(L.evaluate(frozen({line:48.5}),2,early).label,"PACE_UNAVAILABLE_OR_EARLY");
});
test("final grades exactly, including push, with no made-up results",()=>{
 const final={...EVENT,status:{type:{state:"post"},period:4,displayClock:"0:00"}};
 assert.equal(L.evaluate(frozen(),40,final).label,"FINAL_HIT");
 assert.equal(L.evaluate(frozen(),32,final).label,"FINAL_MISS");
 assert.equal(L.evaluate(frozen({line:35}),35,final).label,"PUSH");
 assert.equal(L.evaluate(frozen(),null,final).label,"STATS_UNAVAILABLE");
});
test("overtime isn't treated as fifth 12-minute quarter",()=>{
 const overtime={...EVENT,status:{type:{state:"in"},period:5,displayClock:"2:00"}};
 assert.equal(L.gameFraction(overtime),null);
 assert.equal(L.evaluate(frozen({line:50}),25,overtime).label,"PACE_UNAVAILABLE_OR_EARLY");
});

test("actual ESPN Warriors GS abbreviations match GSW model names and real boxscore stats",()=>{
 const observed=[
  {player:"Draymond Green",team:"GS",athlete_id:"6589",stats:{PTS:8,REB:3,AST:5,PRA:16}},
  {player:"Yaxel Lendeborg",team:"GS",athlete_id:"5175737",stats:{PTS:6,REB:1,AST:0,PRA:7}},
  {player:"Brandin Podziemski",team:"GS",athlete_id:"4709138",stats:{PTS:2,REB:0,AST:1,PRA:3}},
  {player:"Franz Wagner",team:"ORL",athlete_id:"4566434",stats:{PTS:6,REB:2,AST:1,PRA:9}}
 ];
 const game="Orlando Magic @ Golden State Warriors";
 const frozen=(player,stat)=>({player,team:"GSW",game,stat,
   start:"2026-11-08T03:00:00Z",board_generated_at:"2026-11-08T00:00:00Z",
   combined_projection:10,line:8.5});
 assert.equal(L.canonicalTeam("GS"),"GSW");
 assert.equal(L.matchPlayer(observed,frozen("Draymond Green","AST"))?.stats.AST,5);
 assert.equal(L.matchPlayer(observed,frozen("Yaxel Lendeborg","REB"))?.stats.REB,1);
 assert.equal(L.matchPlayer(observed,frozen("Yaxel Lendeborg","PRA"))?.stats.PRA,7);
 assert.equal(L.matchPlayer(observed,frozen("Brandin Podziemski","REB"))?.stats.REB,0);
 assert.equal(L.matchPlayer(observed,{...frozen("Franz Wagner","PTS"),team:"GSW"}),null);
 assert.equal(L.matchPlayer(observed,{...frozen("Draymond Green","AST"),team:"ORL"}),null);
});
test("ESPN nonstandard team aliases match only their canonical NBA team",()=>{
 for(const [espn,model] of [["GS","GSW"],["NY","NYK"],["WSH","WAS"],["SA","SAS"],
    ["NO","NOP"],["UT","UTA"],["PHO","PHX"],["BRK","BKN"]]){
  assert.equal(L.canonicalTeam(espn),model);
  assert.equal(L.matchPlayer([{player:"Test Player",team:espn,stats:{PTS:12}}],
    {player:"Test Player",team:model})?.stats.PTS,12);
 }
 assert.equal(L.matchPlayer([{player:"Test Player",team:"NY",stats:{PTS:12}}],
   {player:"Test Player",team:"BKN"}),null);
 assert.equal(L.matchPlayer([
  {player:"Same Player",team:"GS",stats:{PTS:5}},
  {player:"Same Player",team:"GSW",stats:{PTS:7}}
 ],{player:"Same Player",team:"GSW"}),null);
});

test("all 30 NBA franchise codes and ESPN aliases resolve deterministically",()=>{
 const teams="ATL BOS BKN CHA CHI CLE DAL DEN DET GSW HOU IND LAC LAL MEM MIA MIL MIN NOP NYK OKC ORL PHI PHX POR SAC SAS TOR UTA WAS".split(" ");
 for(const code of teams){
  assert.equal(L.canonicalTeam(code),code);
  const player={player:"Sample Player",team:code};
  const row={player:"Sample Player",team:code,stats:{PTS:12,REB:3,AST:4,PRA:19}};
  assert.deepEqual(L.matchDiagnostics([row],player),{matched:row,reason:null});
 }
 for(const [espn,official] of Object.entries({GS:"GSW",NY:"NYK",WSH:"WAS",SA:"SAS",NO:"NOP",UT:"UTA",PHO:"PHX",BRK:"BKN",BK:"BKN"})){
  assert.equal(L.canonicalTeam(espn),official);
  assert.equal(L.matchPlayer([{player:"Sample Player",team:espn}],{player:"Sample Player",team:official})?.team,espn);
 }
});
test("live player diagnostics distinguish other-team identity from unavailable player",()=>{
 const rows=[{player:"Draymond Green",team:"GS",stats:{AST:5}},{player:"Franz Wagner",team:"ORL",stats:{PTS:6}}];
 assert.equal(L.matchDiagnostics(rows,{player:"Franz Wagner",team:"GSW"}).reason,"TEAM_MISMATCH");
 assert.equal(L.matchDiagnostics(rows,{player:"Missing Player",team:"GSW"}).reason,"PLAYER_NOT_IN_VERIFIED_BOXSCORE");
 assert.equal(L.matchDiagnostics([...rows,rows[0]],{player:"Draymond Green",team:"GSW"}).reason,"DUPLICATE_PLAYER");
 assert.equal(L.matchDiagnostics(rows,{player:"Draymond Green",team:"GSW"}).matched.stats.AST,5);
});
