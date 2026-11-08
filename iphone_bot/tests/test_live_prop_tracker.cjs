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
 assert.equal(L.gameFraction(overtime),1);
 assert.equal(L.evaluate(frozen({line:50}),25,overtime).label,"PACE_UNAVAILABLE_OR_EARLY");
});
