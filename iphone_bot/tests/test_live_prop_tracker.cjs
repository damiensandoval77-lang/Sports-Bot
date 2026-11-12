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

test("duplicate same-team display names resolve only on a verified shared athlete ID",()=>{
 const rows=[
  {player:"Alex Smith",team:"GS",athlete_id:"100",stats:{PTS:10}},
  {player:"Alex Smith",team:"GS",athlete_id:"200",stats:{PTS:20}}
 ];
 assert.equal(L.matchDiagnostics(rows,{player:"Alex Smith",team:"GSW",player_id:"200"}).matched.stats.PTS,20);
 assert.equal(L.matchDiagnostics(rows,{player:"Alex Smith",team:"GSW",player_id:"999"}).reason,"DUPLICATE_PLAYER");
 assert.equal(L.matchDiagnostics(rows,{player:"Alex Smith",team:"ORL",player_id:"200"}).reason,"TEAM_MISMATCH");
});

test("AJ Dybantsa previously observed standard and Demon lines are shown as non-bet quotes",()=>{
 const game="Washington Wizards @ Detroit Pistons",start="2026-11-10T00:00:00Z";
 const src={status:"LIVE_THIRD_PARTY_PRIZEPICKS_LINES",
   source:"independent_prizepicksapi_com",generated_at:"2026-11-09T23:58:23.454418+00:00",
   board_offers:[
    {id:"pp_pts",player:"AJ Dybantsa",team:"WAS",game,stat:"PTS",line:15.5,
     starts_at:start,observed_at:"2026-11-09T23:54:28.212Z",is_demo:false,
     source:"independent_prizepicksapi_com",more_tier:"standard",less_tier:"standard"},
    {id:"pp_reb",player:"AJ Dybantsa",team:"WAS",game,stat:"REB",line:5,
     starts_at:start,observed_at:"2026-11-09T23:54:00.836Z",is_demo:false,
     source:"independent_prizepicksapi_com",more_tier:"standard",less_tier:"standard"},
    {id:"pp_pra",player:"AJ Dybantsa",team:"WAS",game,stat:"PRA",line:23.5,
     starts_at:start,observed_at:"2026-11-09T23:54:00.836Z",is_demo:false,
     source:"independent_prizepicksapi_com",more_tier:"standard",less_tier:"standard"},
    {id:"pp_ast",player:"AJ Dybantsa",team:"WAS",game,stat:"AST",line:2.5,
     starts_at:start,observed_at:"2026-11-09T23:54:00.836Z",is_demo:false,
     source:"independent_prizepicksapi_com",more_tier:"demon",less_tier:"demon"}
   ]};
 for(const [stat,value,tier] of [["PTS",15.5,"standard"],["REB",5,"standard"],
                                  ["PRA",23.5,"standard"],["AST",2.5,"demon"]]){
  const row={player:"AJ Dybantsa",team:"WAS",game,start,stat,projection:11.2,line:null};
  const quote=L.observedPregameLine(row,src);
  assert.equal(quote?.line,value);
  assert.equal(quote?.tier,tier);
  assert.equal(quote?.status,"OBSERVED_PRETIP_QUOTE_NOT_FROZEN_PICK");
  assert.equal(row.line,null,"The original AI-only prediction must remain unchanged");
 }
});
test("Observed pretip line never guessed from post-tip, stale, one-sided or conflicting quotes",()=>{
 const game="Washington Wizards @ Detroit Pistons",start="2026-11-10T00:00:00Z";
 const row={player:"AJ Dybantsa",team:"WAS",game,start,stat:"PTS",line:null,projection:16.6};
 const quote={player:"AJ Dybantsa",team:"WAS",game,stat:"PTS",line:15.5,
  starts_at:start,observed_at:"2026-11-09T23:54:00Z",
  more_tier:"standard",less_tier:"standard",is_demo:false,
  source:"independent_prizepicksapi_com"};
 const source={status:"LIVE_THIRD_PARTY_PRIZEPICKS_LINES",
   source:"independent_prizepicksapi_com",generated_at:"2026-11-09T23:58:00Z",
   board_offers:[quote]};
 const read=(patch={},offers=[quote])=>L.observedPregameLine(row,{...source,...patch,board_offers:offers});
 assert.equal(read({generated_at:"2026-11-10T00:01:00Z"}),null);
 assert.equal(read({generated_at:"2026-11-09T16:00:00Z"}),null);
 assert.equal(read({},[{...quote,observed_at:"2026-11-10T00:01:00Z"}]),null);
 assert.equal(read({},[{...quote,less_tier:null}]),null);
 assert.equal(read({},[{...quote,team:"DET"}]),null);
 assert.equal(read({},[{...quote,player:"Another Player"}]),null);
 assert.equal(read({},[{...quote,is_demo:true}]),null);
 assert.equal(read({},[quote,{...quote,line:16.5}]),null);
 assert.equal(read({},[{...quote,source:"unverified"}]),null);
});

test("all eight matchups retain both frozen and AI-only markets per player/stat",()=>{
 const games=["Cleveland Cavaliers @ Charlotte Hornets",
 "Los Angeles Lakers @ Atlanta Hawks","Washington Wizards @ Detroit Pistons",
 "Memphis Grizzlies @ Toronto Raptors","Indiana Pacers @ Dallas Mavericks",
 "Denver Nuggets @ Houston Rockets","San Antonio Spurs @ Phoenix Suns",
 "New Orleans Pelicans @ Golden State Warriors"];
 for(const [i,game] of games.entries()){
  const start="2026-11-10T00:00:00Z",captured="2026-11-09T23:40:00Z";
  const priced={player:"Frozen Player",player_id:String(i+1),team:"WAS",
   game,start,stat:"PTS",projection:20,line:19.5,combined_projection:20,
   board_generated_at:captured};
  const standalone={player:"No Line Player",player_id:String(i+101),team:"WAS",
   game,start,stat:"AST",projection:5.2,line:null,
   is_pregame_prediction:true,captured_at:captured};
  const result=L.mergeLiveForecasts([priced],[standalone],game);
  assert.equal(result.length,2);
  assert.ok(result.some(p=>p.player==="Frozen Player"&&p.line===19.5));
  assert.ok(result.some(p=>p.player==="No Line Player"&&p.line===null));
 }
});
test("a line-backed market suppresses only matching AI-only stat, not the rest",()=>{
 const start="2026-11-10T00:00:00Z",captured="2026-11-09T23:40:00Z",
       game="Washington Wizards @ Detroit Pistons";
 const a={player:"AJ Dybantsa",player_id:"1643407",team:"WAS",game,start,
   stat:"PTS",line:15.5,combined_projection:16.6,board_generated_at:captured};
 const p={player:"AJ Dybantsa",player_id:"1643407",team:"WAS",game,start,
   is_pregame_prediction:true,line:null,captured_at:captured};
 const x=L.mergeLiveForecasts([a],[{...p,stat:"PTS",projection:16.6},
     {...p,stat:"REB",projection:5}],game);
 assert.equal(x.length,2);
 assert.equal(x.filter(q=>q.stat==="PTS").length,1);
 assert.equal(x.find(q=>q.stat==="PTS").line,15.5);
 assert.equal(x.find(q=>q.stat==="REB").line,null);
});
test("full-slate historical archive displays exact pretip quote after provider snapshot rolls over",()=>{
 const game="Washington Wizards @ Detroit Pistons",start="2026-11-10T00:00:00Z";
 const forecast={player:"AJ Dybantsa",team:"WAS",game,stat:"PRA",start,projection:24.5,line:null};
 const q={id:"pp_test",player:"AJ Dybantsa",team:"WAS",game,stat:"PRA",
   starts_at:start,observed_at:"2026-11-09T23:54:00Z",
   source_generated_at:"2026-11-09T23:58:00Z",line:23.5,tier:"standard",
   more_tier:"standard",less_tier:"standard",is_demo:false,
   source:"independent_prizepicksapi_com"};
 const archive={status:"VERIFIED_PRETIP_PRIZEPICKS_QUOTES_ARCHIVE",quotes:[q]};
 assert.deepEqual(L.archivedPregameLine(forecast,archive),{
   line:23.5,tier:"standard",observed_at:q.observed_at,
   provider_projection_id:"pp_test",source:"independent_prizepicksapi_com",
   status:"OBSERVED_PRETIP_QUOTE_NOT_FROZEN_PICK"});
 assert.equal(L.archivedPregameLine({...forecast,team:"DET"},archive),null);
 assert.equal(L.archivedPregameLine(forecast,{...archive,quotes:[{...q,
   source_generated_at:"2026-11-10T00:01:00Z"}]}),null);
});

test("all eight started NBA games can show authentic line-only player markets",()=>{
 const games=["Cleveland Cavaliers @ Charlotte Hornets",
 "Los Angeles Lakers @ Atlanta Hawks","Washington Wizards @ Detroit Pistons",
 "Memphis Grizzlies @ Toronto Raptors","Indiana Pacers @ Dallas Mavericks",
 "Denver Nuggets @ Houston Rockets","San Antonio Spurs @ Phoenix Suns",
 "New Orleans Pelicans @ Golden State Warriors"];
 const start="2026-11-10T00:00:00Z",observed="2026-11-09T23:54:00Z",
       captured="2026-11-09T23:58:00Z";
 const quotes=games.map((game,i)=>({id:"pp_"+i,player:"Line Only Player "+i,
   team:"WAS",game,stat:"PTS",line:15.5+i,starts_at:start,
   observed_at:observed,source_generated_at:captured,source:"independent_prizepicksapi_com",
   is_demo:false,tier:"standard",more_tier:"standard",less_tier:"standard"}));
 const archive={status:"VERIFIED_PRETIP_PRIZEPICKS_QUOTES_ARCHIVE",quotes};
 for(const game of games){
  const cards=L.quoteOnlyLiveRows(archive,game,[],Date.parse("2026-11-10T00:15:00Z"));
  assert.equal(cards.length,1,game);
  assert.equal(cards[0].quote_only,true);
  assert.equal(cards[0].projection,null);
  assert.equal(cards[0].line,null);
  assert.ok(L.archivedPregameLine(cards[0],archive)?.line>0);
 }
});
test("frozen or AI-only market is not duplicated by quote-only tracker fallback",()=>{
 const game="Los Angeles Lakers @ Atlanta Hawks",start="2026-11-10T00:00:00Z";
 const q={id:"pp_1",player:"Tracked Player",team:"LAL",game,stat:"AST",line:4.5,
  starts_at:start,observed_at:"2026-11-09T23:54:00Z",
  source_generated_at:"2026-11-09T23:58:00Z",source:"independent_prizepicksapi_com",
  is_demo:false,tier:"standard",more_tier:"standard",less_tier:"standard"};
 const a={status:"VERIFIED_PRETIP_PRIZEPICKS_QUOTES_ARCHIVE",quotes:[q]};
 const existing={player:"Tracked Player",team:"LAL",game,stat:"AST",
  start,projection:4.1,line:null};
 assert.equal(L.quoteOnlyLiveRows(a,game,[existing],Date.parse("2026-11-10T00:30:00Z")).length,0);
 assert.equal(L.quoteOnlyLiveRows(a,game,[],Date.parse("2026-11-09T23:30:00Z")).length,0);
 assert.equal(L.quoteOnlyLiveRows(a,game,[],Date.parse("2026-11-10T00:30:00Z")).length,1);
});
test("combined app never turns a quote-only standard line into an AI projection",()=>{
 const fs=require("node:fs");
 const model=fs.readFileSync("docs/dames-picks/feeds.js","utf8");
 const app=fs.readFileSync("docs/dames-picks/index.html","utf8");
 assert.ok(model.includes("function includeArchivedStandard(rows,archive)"));
 assert.ok(model.includes("projection:null,direction:null,chance:null"));
 assert.ok(model.includes("quoteOnly:true"));
 assert.ok(app.includes('p.quoteOnly?"NO AI"'));
 assert.ok(app.includes('p.quoteOnly?"NO AI"')); // quote-only identity remains labeled on card badge; footer is OVER/UNDER only
});
