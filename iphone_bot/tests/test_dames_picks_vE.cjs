const test=require("node:test"),assert=require("node:assert/strict"),fs=require("node:fs"),vm=require("node:vm");
const ctx={};vm.createContext(ctx);vm.runInContext(fs.readFileSync("docs/dames-picks/feeds.js","utf8"),ctx);
const m=ctx.DamesPicksModel;
const pt={player:"Stephen Curry",player_id:"201939",team:"GSW",opponent:"NOP",
 game:"New Orleans Pelicans @ Golden State Warriors",start:"2026-11-10T03:00:00+00:00",
 stat:"PTS",line:28.5,projection:31.391,market_updated:"2026-11-09T21:06:16Z",
 captured_at:"2026-11-09T22:18:06Z",pickem_tier:"standard",
 standard_line_two_sided_verified:true,research_only:true,production_replaced:false,
 grade:"PENDING",estimated_hit_chance:{method:"JOINT_2024_25_VALIDATION_RESIDUALS_20K_UNCALIBRATED",
 draws:20000,calibrated:false,modeled_direction:"More",modeled_selected_probability:.6658}};
test("NBA records match original frozen player line, projection, and uncertainty",()=>{
 const r=m.nba({status:"FROZEN_NEW_AI_ALL_MARKET",records:[pt]},{players:[]});
 assert.equal(r.length,1);assert.equal(r[0].line,28.5);
 assert.equal(r[0].projection,31.391);assert.equal(r[0].direction,"MORE");
 assert.equal(r[0].chance,.6658);assert.equal(r[0].grade,"PENDING");
});
test("Reject alternate, invalid, posttip, and undocumented probability feeds",()=>{
 const invalid=[{...pt,pickem_tier:"demon"},{...pt,captured_at:"2026-11-10T04:00:00Z"},
 {...pt,estimated_hit_chance:{draws:10000}},{...pt,standard_line_two_sided_verified:false}];
 assert.equal(m.nba({status:"FROZEN_NEW_AI_ALL_MARKET",records:invalid},null).length,0);
});
test("Only final verified directional grades affect displayed win-loss",()=>{
 const r=m.nba({status:"FROZEN_NEW_AI_ALL_MARKET",records:[
 {...pt,grade:"GRADED",actual:35,direction_hit:true},
 {...pt,stat:"PRA",line:37.5,grade:"PENDING"},
 {...pt,stat:"AST",line:5.5,grade:"GRADED",actual:5,direction_hit:false}]},null);
 const s=m.summarize(r,null,Date.parse("2026-11-09T22:00:00Z"));
 assert.equal(s.wins,1);assert.equal(s.losses,1);assert.equal(s.pending,1);assert.equal(s.hitRate,.5);
});
test("NFL manifest CSV parsing retains comma-containing nested historical logs",()=>{
 const rows=m.csv('player,season_game_log,line\n"Player, Jr.","[{""week"":9,""actual"":22}]",24.5\n');
 assert.equal(rows.length,1);assert.equal(rows[0].player,"Player, Jr.");
 assert.equal(JSON.parse(rows[0].season_game_log)[0].actual,22);
});
test("NFL uses only verified pretip standard offers and avoids false final grades",()=>{
 const p={captured_at:"2026-11-09T20:00:00Z",game_id:"2026_10_WAS_NYG",player:"Rachaad White",
 player_id:"00-0037256",team:"WAS",opponent:"NYG",position:"RB",stat:"Rush Attempts",
 odds_type:"standard",line:"18.5",proj:"9.5",p_more:".03",pick:"Less",
 season_avg:"7.71",season_games:"7",season_game_log:'[{"week":9,"actual":7}]'};
 const schedule={games:[{game_id:p.game_id,kickoff_utc:"2026-11-10T01:00:00Z"}]};
 const r=m.nfl([[p,{...p,odds_type:"demon"},{...p,captured_at:"2026-11-11T01:00:00Z"}]],schedule);
 assert.equal(r.length,1);assert.ok(Math.abs(r[0].chance-.97)<.000001);
 assert.equal(r[0].direction,"LESS");assert.equal(r[0].grade,"PENDING");
 assert.equal(r[0].logs[0].actual,7);
});
test("No demo fixture, hardcoded sample player, or automatic grades in UI",()=>{
 const html=fs.readFileSync("docs/dames-picks/index.html","utf8");
 for(const p of ["lagged_matchup_all_market_ledger.json","nfl/data/latest_2026.json",
 "current_form.json","nfl/data/grading_health_2026.json","nfl/data/schedule_2026.json"])
 assert.ok(html.includes(p));
 assert.ok(!html.includes("SAMPLE DATA"));
 assert.ok(html.includes("No sample data is substituted"));
});
test("Version E design primitives and sport navigation exist",()=>{
 const html=fs.readFileSync("docs/dames-picks/index.html","utf8");
 for(const p of ["--lime:#c5fa29","--pink:#fa70b5","--mint:#72efc3",
 'data-league="NBA"','data-league="NFL"','data-view="live"','data-view="tracker"','id="markets"'])
  assert.ok(html.includes(p),p);
});


test("Real published NBA and NFL artifacts both produce nonempty integrated player props",()=>{
 const root="docs/";
 const ledger=JSON.parse(fs.readFileSync(root+"lagged_matchup_all_market_ledger.json","utf8"));
 const form=JSON.parse(fs.readFileSync(root+"current_form.json","utf8"));
 const a=m.nba(ledger,form);
 assert.ok(a.length>0,"Published NBA ledger yields zero eligible player props");
 assert.ok(a.every(x=>x.player&&Number.isFinite(x.line)&&Number.isFinite(x.projection)));
 const manifest=JSON.parse(fs.readFileSync(root+"nfl/data/latest_2026.json","utf8"));
 const schedule=JSON.parse(fs.readFileSync(root+"nfl/data/schedule_2026.json","utf8"));
 const parts=manifest.files.map(name=>m.csv(fs.readFileSync(root+"nfl/data/"+name,"utf8")));
 const b=m.nfl(parts,schedule);
 assert.ok(b.length>0,"Published NFL model yielded zero eligible standard player props");
 assert.ok(b.every(x=>x.player&&Number.isFinite(x.line)&&Number.isFinite(x.projection)));
 console.log("Live contract counts: NBA",a.length,"NFL",b.length);
});

test("Live NBA snapshot overlays only matched named player, same team and matchup",()=>{
 const saved=m.nba({status:"FROZEN_NEW_AI_ALL_MARKET",records:[pt]},{players:[]});
 const at=Date.parse("2026-11-10T03:15:00Z");
 const live={status:"OK",captured_at:"2026-11-10T03:14:00Z",games:[{
 game:pt.game,state:"in",period:1,shortDetail:"9:00 - 1st",observed_at:"2026-11-10T03:14:00Z",
 player_rows:[{player:"Stephen Curry",team:"GSW",PTS:9},{player:"Stephen Curry",team:"NOP",PTS:22}]}]};
 const fresh=m.attachLive(saved,live,null,at);
 assert.equal(fresh[0].live.actual,9);
 assert.equal(fresh[0].projection,31.391);assert.equal(fresh[0].line,28.5);
 assert.equal(m.attachLive(saved,{...live,captured_at:"2026-11-10T02:00:00Z"},null,at)[0].live,null);
 assert.equal(m.attachLive(saved,{...live,games:[{...live.games[0],state:"post"}]},null,at)[0].live,null);
});
test("NFL live join uses original stat target and matches exact game/player",()=>{
 const row={sport:"NFL",player:"Josh Allen",team:"BUF",gameId:"2026_09_BUF_MIN",target:"PASS_YDS",line:240.5,projection:265,stat:"Pass Yards"};
 const now=Date.parse("2026-11-10T03:15:00Z");
 const live={status:"ok",checked_at:"2026-11-10T03:14:00Z",games:[{
 game_id:row.gameId,status:"in",status_text:"3rd",players:[
 {player:"Josh Allen",team:"BUF",stats:{PASS_YDS:150}},
 {player:"Josh Allen",team:"MIN",stats:{PASS_YDS:400}}]}]};
 const rows=m.attachLive([row],null,live,now);
 assert.equal(rows[0].live.actual,150);assert.equal(rows[0].line,240.5);
 assert.equal(m.attachLive([row],null,{...live,checked_at:"2026-11-09T01:00:00Z"},now)[0].live,null);
});
test("NFL confirmed result joins only the exact original captured line",()=>{
 const row={sport:"NFL",gameId:"2026_09_BUF_MIN",playerId:"42",stat:"Pass Yards",
 line:240.5,captured:"2026-11-09T18:00:00Z",grade:"PENDING",hit:null,actual:null};
 const verified={game_id:row.gameId,player_id:row.playerId,stat:row.stat,line:"240.5",
 captured_at:row.captured,odds_type:"standard",actual:"250",won:"true",grade_status:"GRADED"};
 const graded=m.attachNFLGrades([row],[verified])[0];
 assert.equal(graded.grade,"GRADED");assert.equal(graded.hit,true);assert.equal(graded.actual,250);
 assert.equal(m.attachNFLGrades([row],[{...verified,line:"245.5"}])[0].grade,"PENDING");
 assert.equal(m.attachNFLGrades([row],[{...verified,grade_status:"PENDING"}])[0].grade,"PENDING");
 assert.equal(m.attachNFLGrades([row],[verified,verified])[0].grade,"PENDING");
});
test("NFL missing grades cannot inherit NBA hit-rate stats",()=>{
 const s=m.summarize([], {standard_settled:0,standard_wins:0,pending_picks:0},Date.now(),"NFL");
 assert.equal(s.hitRate,null);assert.equal(s.graded,0);
});
test("Production source feeds keep expected real stat keys and health flags",()=>{
 const liveNBA=JSON.parse(fs.readFileSync("docs/live_player_tracking.json","utf8"));
 const liveNFL=JSON.parse(fs.readFileSync("docs/nfl/data/live_2026.json","utf8"));
 const nba=JSON.parse(fs.readFileSync("docs/tonight_capture_gradeability.json","utf8"));
 assert.ok(Array.isArray(liveNBA.games));
 assert.ok(Array.isArray(liveNFL.games));
 assert.ok(nba.summary&&typeof nba.summary.total_standard_markets_without_frozen_model==="number");
 const page=fs.readFileSync("docs/dames-picks/index.html","utf8");
 for(const name of ["live_player_tracking.json","nfl/data/live_2026.json","pp_graded_2026.csv",
 "tonight_capture_gradeability.json","ai_forecast_today_grade_status.json","dames-picks-bookmarks-v1"])
 assert.ok(page.includes(name),name);
});

test("Different saved thresholds or observation times never share one player card identity",()=>{
 const base={sport:"NBA",playerId:"201939",game:"NOP @ GSW",start:"2026-11-10T03:00:00Z",
 stat:"PTS",line:27.5,captured:"2026-11-09T21:00:00Z"};
 assert.notEqual(m.key(base),m.key({...base,line:28.5}));
 assert.notEqual(m.key(base),m.key({...base,captured:"2026-11-09T21:01:00Z"}));
});
