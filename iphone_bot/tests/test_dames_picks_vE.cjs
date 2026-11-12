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
test("ESPN NBA team aliases match only the correct player's canonical franchise",()=>{
 const now=Date.parse("2026-11-11T01:05:00Z");
 const aliases=[["NYK","NY"],["GSW","GS"],["NOP","NO"],["SAS","SA"],["UTA","UTAH"],["WAS","WSH"]];
 for(const [ledgerTeam,espnTeam] of aliases){
  const player={sport:"NBA",player:"Test Player",team:ledgerTeam,
   game:"Test Away @ Test Home",stat:"PTS",line:20.5,projection:24.3};
  const live={status:"OK",captured_at:"2026-11-11T01:04:00Z",games:[{
   game:player.game,state:"in",observed_at:"2026-11-11T01:04:00Z",
   player_rows:[{player:"Test Player",team:espnTeam,PTS:13},
                {player:"Test Player",team:"BOS",PTS:47}]}]};
  const joined=m.attachLive([player],live,null,now)[0];
  assert.equal(joined.live?.actual,13,ledgerTeam+" should match "+espnTeam);
  const rival=m.attachLive([{...player,team:"BOS"}],live,null,now)[0];
  assert.equal(rival.live?.actual,47,ledgerTeam+" should not inherit opponent stat");
 }
});
test("Ambiguous normalized NBA player identities cannot inherit live stats",()=>{
 const now=Date.parse("2026-11-11T01:05:00Z");
 const player={sport:"NBA",player:"Test Player",team:"NYK",
               game:"Test Away @ Test Home",stat:"PTS"};
 const feed={status:"OK",captured_at:"2026-11-11T01:04:00Z",games:[{
  game:player.game,state:"in",observed_at:"2026-11-11T01:04:00Z",
  player_rows:[{player:"Test Player",team:"NY",PTS:13},
               {player:"Test Player",team:"NYK",PTS:15}]}]};
 assert.equal(m.attachLive([player],feed,null,now)[0].live,null);
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

test("Verified official NBA injury matches only same player team and eastern game date",()=>{
 const rows=m.nba({status:"FROZEN_NEW_AI_ALL_MARKET",records:[pt]},{players:[]});
 const issued="2026-11-09T21:00:00Z";
 const report={status:"OFFICIAL_NBA_REPORT_VERIFIED",injury_data_verified:true,
  report_issued_at:issued,generated_at:"2026-11-09T21:10:00Z",
  players:[{player_id:pt.player_id,team:"GSW",game_date:"2026-11-09",status:"Questionable"},
   {player_id:pt.player_id,team:"BOS",game_date:"2026-11-09",status:"Out"}]};
 const out=m.attachInjuries(rows,report);
 assert.equal(out[0].injury.status,"Questionable");
 assert.equal(out[0].projection,31.391);
 assert.equal(m.attachInjuries(rows,{...report,injury_data_verified:false})[0].injury,undefined);
 assert.equal(m.attachInjuries(rows,{...report,players:[{...report.players[0],game_date:"2026-11-10"}]})[0].injury,null);
});
test("NFL source historical line results and depth context are retained without recalculation",()=>{
 const p={captured_at:"2026-11-09T20:00:00Z",game_id:"2026_10_WAS_NYG",player:"Test RB",
 player_id:"123",team:"WAS",opponent:"NYG",position:"RB",stat:"Rush Yards",target:"RUSH_YDS",
 odds_type:"standard",line:"75.5",proj:"82.0",p_more:".6",pick:"More",
 season_avg:"70.2",season_games:"8",season_over:"4",season_under:"4",season_push:"0",
 season_last5_over:"2",season_last5_under:"3",depth_role:"Starter",depth_rank:"1",
 depth_asof:"2026-11-09T17:00:00Z",snap_pct_l3:"0.75"};
 const r=m.nfl([[p]],{games:[{game_id:p.game_id,kickoff_utc:"2026-11-10T01:00:00Z"}]})[0];
 assert.equal(r.form.over,4);assert.equal(r.form.last5Under,3);
 assert.equal(r.depth.role,"Starter");assert.equal(r.depth.snapPct,.75);
 assert.equal(r.line,75.5);
});

test("Every unmatched verified standard NBA quote is visible as explicitly unmodeled",()=>{
 const frozen=m.nba({status:"FROZEN_NEW_AI_ALL_MARKET",records:[pt]},null);
 const same={id:"1",player:pt.player,team:pt.team,game:pt.game,stat:pt.stat,
  starts_at:pt.start,observed_at:"2026-11-09T23:00:00Z",line:28.5,
  tier:"standard",more_tier:"standard",less_tier:"standard",is_demo:false};
 const other={...same,id:"2",line:27.5,observed_at:"2026-11-09T23:03:00Z"};
 const noModel={...same,id:"3",player:"Example Player",line:13.5};
 const rows=m.includeArchivedStandard(frozen,{quotes:[same,other,noModel,
  {...noModel,id:"4",tier:"demon"},
  {...noModel,id:"5",observed_at:"2026-11-10T04:00:00Z"}]});
 assert.equal(rows.length,3);
 assert.equal(rows.filter(x=>x.quoteOnly).length,2);
 assert.equal(rows.filter(x=>x.quoteOnly&&x.projection===null&&x.chance===null&&x.direction===null).length,2);
 assert.equal(rows.filter(x=>x.quoteOnly&&x.grade==="UNMODELED").length,2);
 assert.equal(rows[0].projection,31.391);
});
test("Published standard quote archive coverage is not silently lost in the combined dashboard",()=>{
 const archive=JSON.parse(fs.readFileSync("docs/prizepicks_pregame_line_archive.json","utf8"));
 const ledger=JSON.parse(fs.readFileSync("docs/lagged_matchup_all_market_ledger.json","utf8"));
 const form=JSON.parse(fs.readFileSync("docs/current_form.json","utf8"));
 const rows=m.includeArchivedStandard(m.nba(ledger,form),archive);
 const valid=archive.quotes.filter(q=>q.tier==="standard"&&q.more_tier==="standard"&&
 q.less_tier==="standard"&&q.is_demo===false&&Date.parse(q.observed_at)<Date.parse(q.starts_at)&&
 ["PTS","REB","AST","PRA"].includes(q.stat));
 const norm=x=>String(x).toLowerCase().replace(/[^a-z0-9]/g,"");
 const k=x=>[norm(x.player),x.team,x.game,x.stat,Number(x.line)].join("|");
 const offered=new Set(valid.map(k)),shown=new Set(rows.map(k));
 for(const key of offered)assert.ok(shown.has(key),"Missing archived standard prop "+key);
 const page=fs.readFileSync("docs/dames-picks/index.html","utf8");
 assert.ok(!page.includes(".slice(0,240)"),"Silently truncated player cards");
 assert.ok(page.includes("prizepicks_pregame_line_archive.json"));
 console.log("Standard source markets",offered.size,"all represented; total cards",rows.length);
});

test("Retained stale NBA backup observations never display as live even with fresh wrapper timestamp",()=>{
 const saved=m.nba({status:"FROZEN_NEW_AI_ALL_MARKET",records:[pt]},{players:[]});
 const now=Date.parse("2026-11-10T03:15:00Z");
 const base={status:"OBSERVED_ESPN_LIVE_BOX_SCORES_SERVER_FALLBACK",captured_at:"2026-11-10T03:14:00Z",
 games:[{game:pt.game,state:"in",stale:true,observed_at:"2026-11-10T03:00:00Z",
 player_rows:[{player:pt.player,team:pt.team,PTS:12}]}]};
 assert.equal(m.attachLive(saved,base,null,now)[0].live,null);
 const nonFlagged={...base,games:[{...base.games[0],stale:false,observed_at:"2026-11-10T02:30:00Z"}]};
 assert.equal(m.attachLive(saved,nonFlagged,null,now)[0].live,null);
 const fresh={...base,games:[{...base.games[0],stale:false,observed_at:"2026-11-10T03:14:00Z"}]};
 assert.equal(m.attachLive(saved,fresh,null,now)[0].live.actual,12);
});

test("NFL published grader's actual lowercase 'graded' result is recognized exactly",()=>{
 const p={sport:"NFL",gameId:"2026_10_BUF_MIA",playerId:"42",stat:"Pass Yards",
  line:248.5,captured:"2026-11-09T18:00:00Z",grade:"PENDING",hit:null,actual:null};
 const row={game_id:p.gameId,player_id:p.playerId,stat:p.stat,
 line:String(p.line),captured_at:p.captured,odds_type:"standard",actual:"251",
 won:"1",grade_status:"graded"};
 const result=m.attachNFLGrades([p],[row])[0];
 assert.equal(result.grade,"GRADED");
 assert.equal(result.hit,true);
 assert.equal(result.actual,251);
 assert.equal(m.attachNFLGrades([p],[{...row,grade_status:"boxscore_unverified"}])[0].grade,"PENDING");
});


test("Game visibility never depends on an eligible saved prop",()=>{
 const now=Date.parse("2026-11-10T04:00:00Z");
 const nba={captured_at:"2026-11-10T03:59:00Z",games:[
  {game:"New Orleans Pelicans @ Golden State Warriors",event_id:"4019",state:"in",
   observed_at:"2026-11-10T03:59:00Z",player_rows:[{player:"Example",team:"GSW",PTS:12}]},
  {game:"San Antonio Spurs @ Phoenix Suns",event_id:"4020",state:"post",
   observed_at:"2026-11-10T03:58:00Z",player_rows:[]}]};
 const nfl={checked_at:"2026-11-10T03:59:00Z",games:[
  {game_id:"2026_09_BUF_MIN",status:"in",away:"BUF",home:"MIN",
   players:[{player:"Josh Allen",team:"BUF",stats:{PASS_YDS:220}}]}]};
 const games=m.liveGames(nba,nfl,now);
 assert.equal(games.length,3);
 assert.deepEqual([...games.map(g=>g.sport)],["NBA","NBA","NFL"]);
 assert.equal(games[0].state,"in");
 assert.equal(games[1].state,"final");
 assert.equal(games[2].state,"in");
 assert.equal(games[2].players[0].stats.PASS_YDS,220);
});
test("Stale NFL and NBA scoreboards remain discoverable but cannot claim live-now",()=>{
 const now=Date.parse("2026-11-10T04:30:00Z");
 const nba={captured_at:"2026-11-10T03:00:00Z",games:[
  {game:"NOP @ GSW",state:"in",observed_at:"2026-11-10T03:00:00Z",player_rows:[]}]};
 const nfl={checked_at:"2026-11-10T03:00:00Z",games:[
  {game_id:"2026_09_BUF_MIN",status:"in",away:"BUF",home:"MIN",players:[]}]};
 const games=m.liveGames(nba,nfl,now);
 assert.equal(games.length,2);
 assert.ok(games.every(g=>g.state==="stale"&&!g.fresh));
 assert.ok(games.every(g=>g.statusText.includes("Last observed")));
});
test("Real published scoreboard game count is independent of model records",()=>{
 const nba=JSON.parse(fs.readFileSync("docs/live_player_tracking.json","utf8"));
 const nfl=JSON.parse(fs.readFileSync("docs/nfl/data/live_2026.json","utf8"));
 const games=m.liveGames(nba,nfl,Date.parse("2026-11-10T04:00:00Z"));
 assert.equal(games.filter(g=>g.sport==="NBA").length,nba.games.length);
 assert.equal(games.filter(g=>g.sport==="NFL").length,nfl.games.length);
 const page=fs.readFileSync("docs/dames-picks/index.html","utf8");
 assert.ok(page.includes("renderLiveGames()"));
 assert.ok(page.includes("function openGame(game)"));
 assert.ok(page.includes("No verified pregame standard quotes were archived for this game. Its scoreboard and box score remain visible."));
});

test("Every game detail exposes original locked model, observed actual, ungraded state and full box score",()=>{
 const html=fs.readFileSync("docs/dames-picks/index.html","utf8");
 for(const text of ["FROZEN LINE","FROZEN PROJ","ACTUAL","LIVE · NOT GRADED",
 "Full published player box score","Scoreboard","data-prop","Actual unavailable",
 "No verified pregame standard quotes were archived for this game"])assert.ok(html.includes(text),text);
 assert.ok(html.includes('g.sport==="NFL"?p.target:p.stat'),"NFL uses exact target stat");
 assert.ok(html.includes('normalize(x.player)===normalize(p.player)'),"Exact player-name guard");
 assert.ok(html.includes('matches.length!==1'),"Ambiguous matches not fabricated");
});

test("Empty NBA live player feed still exposes every verified scheduled game",()=>{
 const schedule=JSON.parse(fs.readFileSync("docs/nba_schedule.json","utf8"));
 const now=Date.parse("2026-11-10T11:00:00Z");
 const games=m.gameCatalog({games:[],captured_at:"2026-11-10T10:35:00Z"},
   {games:[],checked_at:"2026-11-10T10:40:00Z"},schedule,{games:[]},now);
 assert.equal(games.filter(g=>g.sport==="NBA").length,schedule.games.length);
 assert.ok(games.filter(g=>g.sport==="NBA").every(g=>g.fresh===false&&g.players.length===0));
 assert.ok(games.filter(g=>g.sport==="NBA"&&g.start&&Date.parse(g.start)<now)
   .every(g=>g.state==="unknown"),"Schedule-only started games cannot claim LIVE");
});
test("NFL schedule fallback includes near-term fixtures, not entire season, and preserves verified scores",()=>{
 const schedule=JSON.parse(fs.readFileSync("docs/nfl/data/schedule_2026.json","utf8"));
 const now=Date.parse("2026-11-10T11:00:00Z");
 const games=m.gameCatalog({games:[]},{games:[]},null,schedule,now);
 const nfl=games.filter(g=>g.sport==="NFL");
 assert.ok(nfl.length>0);
 assert.ok(nfl.length<schedule.games.length);
 assert.ok(nfl.every(g=>g.start&&Date.parse(g.start)>=now-48*3600000&&Date.parse(g.start)<=now+8*86400000));
 assert.ok(nfl.filter(g=>g.state==="scheduled").every(g=>g.awayScore===null&&g.homeScore===null));
});
test("Observed ESPN game wins over schedule-only fallback and is not duplicated",()=>{
 const now=Date.parse("2026-11-10T03:40:00Z");
 const nba={captured_at:"2026-11-10T03:39:00Z",games:[
 {game:"NOP @ GSW",event_id:"401",state:"in",observed_at:"2026-11-10T03:39:00Z",
 player_rows:[{player:"Stephen Curry",team:"GSW",PTS:25}]}]};
 const schedule={dates_eastern:["2026-11-09"],games:[{
 id:"401",game:"NOP @ GSW",date_eastern:"2026-11-09",
 away:"NOP",home:"GSW",start:"2026-11-10T03:00:00Z",game_state:"pre"}]};
 const out=m.gameCatalog(nba,{games:[]},schedule,{games:[]},now);
 assert.equal(out.length,1);assert.equal(out[0].state,"in");
 assert.equal(out[0].players[0].stats.PTS,25);
});

test("Historic AI-only backlog persists even if today's grade report says zero",()=>{
 const audit=JSON.parse(fs.readFileSync("docs/ai_forecast_coverage_audit.json","utf8"));
 const now=Date.parse(audit.checked_at);
 const previous=m.gradingAuditSummary(audit,now);
 assert.ok(previous,"A permanent prior-day audit must remain available");
 const counts=audit.days[previous.day];
 assert.equal(previous.captured,counts.captured);
 assert.equal(previous.graded,counts.graded);
 assert.equal(previous.pending,counts.pending);
 assert.equal(previous.voided,counts.void_dnp+counts.excluded_nonparticipant);
 assert.equal(previous.stale,false);
 const page=fs.readFileSync("docs/dames-picks/index.html","utf8");
 assert.ok(page.includes("ai_forecast_coverage_audit.json"));
 assert.ok(page.includes("NBA AI-only: "));
 assert.ok(!page.includes('+" AI-only forecasts still ungraded"'));
});
test("Bad grading math and stale audit never look healthy",()=>{
 const now=Date.parse("2026-11-10T12:00:00Z");
 const valid={checked_at:"2026-11-10T11:59:00Z",days:{
 "2026-11-09":{captured:10,graded:7,pending:3,void_dnp:0,
 excluded_nonparticipant:0,accounted_for:7}}};
 assert.equal(m.gradingAuditSummary(valid,now).pending,3);
 assert.equal(m.gradingAuditSummary({...valid,checked_at:"2026-11-09T10:00:00Z"},now).stale,true);
 assert.equal(m.gradingAuditSummary({...valid,days:{"2026-11-09":{...valid.days["2026-11-09"],pending:0}}},now),null);
});

test("Production NFL grades in immutable archive all join Tracker, including older frozen prices",()=>{
 const root="docs/nfl/data/";
 const manifest=JSON.parse(fs.readFileSync(root+"latest_2026.json","utf8"));
 const schedule=JSON.parse(fs.readFileSync(root+"schedule_2026.json","utf8"));
 const latest=m.nfl(manifest.files.map(file=>m.csv(fs.readFileSync(root+file,"utf8"))),schedule);
 const graded=m.csv(fs.readFileSync(root+"pp_graded_2026.csv","utf8"));
 const pending=m.csv(fs.readFileSync(root+"pp_grading_pending_2026.csv","utf8"));
 const rows=m.reconcileNFLSettlementCards(latest,graded,pending,schedule);
 const health=JSON.parse(fs.readFileSync(root+"grading_health_2026.json","utf8"));
 const directional=rows.filter(p=>p.grade==="GRADED"&&typeof p.hit==="boolean");
 const winners=directional.filter(p=>p.hit).length;
 assert.equal(directional.length,health.standard_settled,"A published standard NFL win/loss was hidden in the player UI");
 assert.equal(winners,health.standard_wins);
 assert.ok(rows.some(p=>p.frozenSettlementArchive===true&&p.captured==="2026-11-09T19:58:51.614124+00:00"&&p.player==="Ray Davis"&&p.grade==="GRADED"),
   "Historic Ray Davis standard prop not retained after latest snapshot rolled");
 const pendingCards=rows.filter(p=>p.grade==="PENDING"&&p.frozenSettlementArchive===true&&p.pendingReason);
 assert.equal(pendingCards.length,health.pending_picks,
   "Every published NFL pending record must be represented by a pending reason, without inventing missing players");
 console.log("NFL standard outcomes rendered",directional.length,"wins",winners,"pending",rows.filter(p=>p.pendingReason).length);
});
test("Source-mismatched final prop is never attached as a real grade",()=>{
 const schedule={games:[{game_id:"2026_09_BUF_MIN",status:"final",
  kickoff_utc:"2026-11-10T01:15:00Z",home_score:6,away_score:23}]};
 const current=[{sport:"NFL",gameId:"2026_09_BUF_MIN",playerId:"123",player:"Player A",team:"BUF",
   stat:"Rush Yards",line:30.5,captured:"2026-11-10T00:30:00Z",projection:40,
   direction:"MORE",grade:"PENDING"}];
 const fake={game_id:"2026_09_BUF_MIN",player_id:"123",player:"Player A",team:"BUF",
  stat:"Rush Yards",line:"30.5",captured_at:"2026-11-10T00:30:00Z",
  odds_type:"standard",proj:"60",pick:"More",actual:"49",result:"More",won:"1",grade_status:"graded"};
 const result=m.reconcileNFLSettlementCards(current,[fake],[],schedule);
 assert.equal(result[0].grade,"PENDING");
 assert.equal(result.length,1);
});

test("Dame's Take immediately follows Dame's projection in expanded player details",()=>{
 const html=fs.readFileSync("docs/dames-picks/index.html","utf8");
 const projection=html.indexOf("<h2>Dame’s projection</h2>");
 const take=html.indexOf("<strong>Dame’s Take</strong>");
 const games=html.indexOf("<h2>Last games</h2>",projection);
 assert.ok(projection>=0&&take>projection&&games>take,"Take must follow projection before last games");
 const between=html.slice(projection,take);
 assert.ok(between.includes("</section>"),"Projection panel must be closed before take bubble");
 assert.ok(!between.includes("<h2>Last games</h2>")&&!between.includes("<h2>Matchup</h2>"));
 assert.equal(html.split("<strong>Dame’s Take</strong>").length-1,1);
});

test("Unified top-picks board excludes quote-only records without a frozen model",()=>{
 const html=fs.readFileSync("docs/dames-picks/index.html","utf8");
 assert.ok(html.includes('timestamp(x.start)>now&&!x.quoteOnly&&x.projection!==null&&x.direction!==null'));
 assert.ok(html.includes('state.mode==="tracker"'));
 assert.ok(html.includes('No sample data is substituted'));
});


test("Official verified DNP is a VOID, never an unresolved NBA pending or lost pick",()=>{
 const final={...pt,grade:"EXCLUDED_VERIFIED_DNP",actual:null,direction_hit:null,
    final_source:"VERIFIED_FINAL_BOXSCORE_DNP_CROSSCHECKED"};
 const rows=m.nba({status:"FROZEN_NEW_AI_ALL_MARKET",records:[final]},{players:[]});
 assert.equal(rows.length,1);
 assert.equal(rows[0].grade,"EXCLUDED_VERIFIED_DNP");
 assert.equal(rows[0].hit,null);
 assert.equal(rows[0].actual,null);
 const summary=m.summarize(rows,null,Date.parse("2026-11-11T06:00:00Z"));
 assert.equal(summary.pending,0);
 assert.equal(summary.graded,0);
 assert.equal(summary.hitRate,null);
 const html=fs.readFileSync("docs/dames-picks/index.html","utf8");
 assert.ok(html.includes('"DNP · VOID"'));
 assert.ok(html.includes('"VERIFIED DNP · VOID"'));
});


test("Merged dashboard shows independently verified pick-settlement health, not every quote as a failed pick",()=>{
 const html=fs.readFileSync("docs/dames-picks/index.html","utf8");
 assert.ok(html.includes('getJSON("dames-picks/published_pick_settlement.json")'));
 assert.ok(html.includes('NBA published picks awaiting verified settlement'));
 assert.ok(html.includes('provider standard markets withheld from AI picks'));
 assert.ok(!html.includes('errors.push("NBA capture incomplete")'));
 assert.ok(html.includes('Official DNP verified · void'));
});


test("Fresh verified NBA scoreboard scores join live cards without inventing player totals",()=>{
 const now=Date.parse("2026-11-11T00:55:00Z");
 const game="Milwaukee Bucks @ New York Knicks";
 const schedule={dates_eastern:["2026-11-10"],
   games:[{id:"0022600211",game,date_eastern:"2026-11-10",
           start:"2026-11-11T00:30:00Z",away:"Milwaukee Bucks",home:"New York Knicks"}]};
 const scores={generated_at:"2026-11-11T00:50:00Z",is_live_score_source:true,
   games:[{id:"0022600211",game,game_state:"in",away_score:42,home_score:47}]};
 const games=m.gameCatalog({games:[]},{games:[]},schedule,null,now,scores);
 const observed=games.find(g=>g.game===game);
 assert.equal(observed.awayScore,42);
 assert.equal(observed.homeScore,47);
 assert.equal(observed.state,"in");
 assert.equal(observed.scoreFresh,true);
 assert.equal(observed.fresh,false);
 assert.equal(observed.players.length,0);
});
test("Old or mismatched NBA score source cannot pose as live matchup",()=>{
 const now=Date.parse("2026-11-11T00:55:00Z");
 const game="Milwaukee Bucks @ New York Knicks";
 const schedule={dates_eastern:["2026-11-10"],
   games:[{id:"0022600211",game,date_eastern:"2026-11-10",
           start:"2026-11-11T00:30:00Z"}]};
 const stale={generated_at:"2026-11-10T17:00:00Z",is_live_score_source:true,
   games:[{id:"0022600211",game,game_state:"in",away_score:42,home_score:47}]};
 const old=m.gameCatalog({games:[]},{games:[]},schedule,null,now,stale)[0];
 assert.equal(old.awayScore,null);
 assert.equal(old.homeScore,null);
 const wrong={...stale,generated_at:"2026-11-11T00:54:00Z",
   games:[{id:"0022600211",game:"Other @ Other",game_state:"in",
           away_score:60,home_score:60}]};
 const mismatch=m.gameCatalog({games:[]},{games:[]},schedule,null,now,wrong)[0];
 assert.equal(mismatch.awayScore,null);
 const pre={...stale,generated_at:"2026-11-11T00:54:00Z",
   games:[{id:"0022600211",game,game_state:"pre",away_score:0,home_score:0}]};
 const pregame=m.gameCatalog({games:[]},{games:[]},schedule,null,now,pre)[0];
 assert.equal(pregame.state,"unknown");
 assert.equal(pregame.awayScore,null);
});
test("Merged app loads separate official score and player feeds",()=>{
 const html=fs.readFileSync("docs/dames-picks/index.html","utf8");
 assert.ok(html.includes('getJSON("nba_scoreboard_independent.json")'));
 assert.ok(html.includes('nbaScores:nbaScores.status==="fulfilled"?nbaScores.value:null'));
 assert.ok(html.includes('L.mergeScores(state.raw.nbaScores,state.direct?.board)'));
 assert.match(html, /<script src="live_direct[.]js[?]bundle=[^"]+"><[/]script>/);
});


test("Fresh independent NBA player rows rescue missing stale legacy live tracker",()=>{
 const now=Date.parse("2026-11-11T01:33:00Z");
 const game="Milwaukee Bucks @ New York Knicks";
 const legacy={status:"OK",captured_at:"2026-11-11T00:39:00Z",games:[]};
 const independent={status:"OBSERVED_NBA_LIVEDATA_PLAYER_BOXSCORES",
   captured_at:"2026-11-11T01:27:00Z",games:[{
     game,state:"in",observed_at:"2026-11-11T01:27:00Z",
     player_rows:[{player:"Test Player",team:"NY",PTS:17,REB:4,AST:2,PRA:23}]}]};
 const selected=m.preferredNBALiveFeed(legacy,independent,now);
 assert.equal(selected.games.length,1);
 assert.equal(selected.games[0].player_rows.length,1);
 const saved=[{sport:"NBA",player:"Test Player",team:"NYK",game,
  stat:"PRA",line:20.5,projection:24.5}];
 const joined=m.attachLive(saved,selected,null,now);
 assert.equal(joined[0].live.actual,23);
 const catalog=m.gameCatalog(selected,null,null,null,now);
 assert.equal(catalog[0].players.length,1);
});
test("Newer verified per-game NBA player rows replace older, empty snapshots never erase",()=>{
 const now=Date.parse("2026-11-11T01:33:00Z");
 const game="Milwaukee Bucks @ New York Knicks";
 const old={status:"OK",captured_at:"2026-11-11T01:22:00Z",
   games:[{game,state:"in",observed_at:"2026-11-11T01:22:00Z",
     player_rows:[{player:"Test Player",team:"NY",PTS:5}]}]};
 const newOne={status:"OBSERVED_NBA_LIVEDATA_PLAYER_BOXSCORES",
   captured_at:"2026-11-11T01:27:00Z",
   games:[{game,state:"in",observed_at:"2026-11-11T01:27:00Z",
     player_rows:[{player:"Test Player",team:"NY",PTS:14}]}]};
 assert.equal(m.preferredNBALiveFeed(old,newOne,now).games[0].player_rows[0].PTS,14);
 newOne.games[0].player_rows=[];
 assert.equal(m.preferredNBALiveFeed(old,newOne,now).games[0].player_rows[0].PTS,5);
});
test("Stale independent NBA player feed never looks live and never changes frozen pick",()=>{
 const now=Date.parse("2026-11-11T01:33:00Z");
 const stale={status:"OBSERVED_NBA_LIVEDATA_PLAYER_BOXSCORES",
   captured_at:"2026-11-11T00:39:00Z",
   games:[{game:"Milwaukee Bucks @ New York Knicks",state:"in",
     player_rows:[{player:"Test Player",team:"NY",PTS:80}]}]};
 const selected=m.preferredNBALiveFeed(null,stale,now);
 assert.equal(selected.games.length,0);
 const saved={sport:"NBA",player:"Test Player",team:"NYK",
  game:"Milwaukee Bucks @ New York Knicks",stat:"PTS",line:25.5,projection:26.0};
 const joined=m.attachLive([saved],selected,null,now)[0];
 assert.equal(joined.live,null);
 assert.equal(joined.line,25.5);
 assert.equal(joined.projection,26);
});
test("Merged page includes independent source not just old empty NBA tracker",()=>{
 const html=fs.readFileSync("docs/dames-picks/index.html","utf8");
 assert.ok(html.includes('getJSON("nba_player_tracking_independent.json")'));
 assert.ok(html.includes('m.preferredNBALiveFeed('));
});


test("Current live cards show one latest pretip standard line, not yesterday and today versions",()=>{
 const start="2026-11-11T01:00:00Z";
 const older={...pt,sport:"NBA",game:"Boston Celtics @ Philadelphia 76ers",start,
  player:"Jayson Tatum",player_id:"1628369",playerId:"1628369",team:"BOS",
  stat:"PTS",line:21.5,captured:"2026-11-09T22:18:06Z",
  projection:24.2,quoteOnly:false,grade:"PENDING"};
 const newer={...older,line:22.5,captured:"2026-11-10T23:23:53Z",projection:24.6};
 const anotherStat={...older,stat:"REB",line:7.5};
 const nextGame={...older,game:"Boston Celtics @ Miami Heat",
  gameId:"Boston Celtics @ Miami Heat",start:"2026-11-12T01:00:00Z",
  captured:"2026-11-10T23:40:00Z"};
 const display=m.displayCurrentPicks([older,newer,anotherStat,nextGame],
  Date.parse("2026-11-11T02:00:00Z"));
 assert.equal(display.length,3);
 assert.equal(display.find(x=>x.game===older.game&&x.stat==="PTS").line,22.5);
 assert.equal(display.filter(x=>x.stat==="REB").length,1);
 assert.equal(display.filter(x=>x.game===nextGame.game).length,1);
});
test("Current tracker excludes previous slate without deleting historical grade entries",()=>{
 const now=Date.parse("2026-11-11T02:00:00Z"); // 9 PM eastern Nov 10
 const today={sport:"NBA",player:"Test Player",playerId:"10",team:"BOS",
  game:"Boston Celtics @ Philadelphia 76ers",gameId:"BOS @ PHI",
  stat:"AST",line:6.5,projection:7.2,start:"2026-11-11T01:00:00Z",
  captured:"2026-11-10T20:00:00Z",grade:"PENDING"};
 const yesterday={...today,game:"Boston Celtics @ Brooklyn Nets",
  gameId:"BOS @ BKN",start:"2026-11-10T01:00:00Z",
  captured:"2026-11-09T20:00:00Z",grade:"GRADED",actual:7};
 const raw=[today,yesterday];
 const visible=m.displayCurrentPicks(raw,now,true);
 assert.equal(visible.length,1);
 assert.equal(visible[0].game,today.game);
 assert.equal(raw.length,2);
 assert.equal(raw[1].grade,"GRADED");
 const html=fs.readFileSync("docs/dames-picks/index.html","utf8");
 assert.ok(html.includes('m.displayCurrentPicks(data,now,state.mode==="tracker")'));
 assert.ok(html.includes('m.displayCurrentPicks(rows().filter(p=>(p.gameId===g.gameId||p.game===g.game)&&!p.quoteOnly))'));
});
test("NFL tracker on a Tuesday shows only the most recent NFL slate, never mixed dates",()=>{
 const now=Date.parse("2026-11-11T02:08:00Z");
 const monday={sport:"NFL",player:"Receiver A",playerId:"nfl-1",team:"BUF",
  game:"BUF @ MIN",gameId:"2026_10_BUF_MIN",stat:"Rec Yards",
  line:55.5,projection:60,captured:"2026-11-09T17:00:00Z",
  start:"2026-11-10T01:15:00Z",grade:"GRADED"};
 const sunday={...monday,game:"BUF @ MIA",gameId:"2026_09_BUF_MIA",
  start:"2026-11-08T18:00:00Z",captured:"2026-11-08T15:00:00Z"};
 const shown=m.displayCurrentPicks([monday,sunday],now,true);
 assert.equal(shown.length,1);
 assert.equal(shown[0].gameId,monday.gameId);
});
test("Unmodeled quote-only research never duplicates the model's published saved card",()=>{
 const p={sport:"NBA",player:"Test Player",playerId:"90",team:"NYK",
  game:"Milwaukee Bucks @ New York Knicks",gameId:"Milwaukee Bucks @ New York Knicks",
  start:"2026-11-11T01:00:00Z",stat:"PRA",line:37.5,
  captured:"2026-11-10T20:00:00Z",projection:38.5,quoteOnly:false};
 const research={...p,playerId:"",line:38.5,
  captured:"2026-11-10T23:00:00Z",projection:null,quoteOnly:true};
 const display=m.displayCurrentPicks([p,research],Date.parse("2026-11-11T02:00:00Z"));
 assert.equal(display.length,1);
 assert.equal(display[0].line,37.5);
 assert.equal(display[0].quoteOnly,false);
});
test("Latest saved line is keyed by player, game and stat, never merged with other players",()=>{
 const now=Date.parse("2026-11-11T02:00:00Z");
 const p={sport:"NBA",player:"One",playerId:"1",team:"BOS",game:"BOS @ PHI",
  gameId:"BOS @ PHI",start:"2026-11-11T01:00:00Z",stat:"PTS",
  line:21.5,captured:"2026-11-10T20:00:00Z",projection:24.0};
 const other={...p,player:"Two",playerId:"2",line:18.5};
 assert.equal(m.displayCurrentPicks([p,other],now).length,2);
});

function verifiedMatchupEstimate(p){
 const factors=Object.fromEntries(["opponent_position_defense","projected_minutes",
 "usage_opportunities","teammate_availability","depth_role","pace_possessions"]
 .map(name=>[name,{source:"pregame verified data",observed_at:"2026-11-10T18:00:00Z",
 baseline:10,matchup:11}]));
 return {method:"PREGAME_MATCHUP_CONDITIONED_V1",research_only:false,
  opponent_aware_verified:true,model_id:"research-validated-v1",
  original_line:p.line,direction:p.direction,
  modeled_selected_probability:.73,captured_at:p.captured,factors};
}
test("HIT EST rejects generic historical residual model even with high odds",()=>{
 const p={sport:"NBA",line:20.5,projection:24.3,direction:"MORE",quoteOnly:false,
  chance:.97,chanceMethod:"JOINT_2024_25_VALIDATION_RESIDUALS_20K_UNCALIBRATED",
  chanceDraws:20000,chanceCalibrated:false,
  captured:"2026-11-10T20:00:00Z",start:"2026-11-11T01:00:00Z"};
 assert.equal(m.hitEstimate(p),null);
 const verified={...p,matchupEstimate:verifiedMatchupEstimate(p)};
 assert.equal(m.hitEstimate(verified).rate,.73);
 assert.equal(m.hitEstimate({...verified,form:{over:10,under:0}}).rate,.73);
 assert.equal(m.hitEstimate({...verified,chance:.22}).rate,.73);
});
test("HIT EST requires matching original standard line, pick side and six pretip factors",()=>{
 const p={sport:"NBA",line:21.5,projection:25,direction:"MORE",chance:.71,
 captured:"2026-11-10T20:00:00Z",start:"2026-11-11T01:00:00Z"};
 const x=verifiedMatchupEstimate(p);
 assert.equal(m.hitEstimate({...p,matchupEstimate:x}).rate,.73);
 assert.equal(m.hitEstimate({...p,matchupEstimate:{...x,original_line:25.5}}),null);
 assert.equal(m.hitEstimate({...p,matchupEstimate:{...x,direction:"LESS"}}),null);
 assert.equal(m.hitEstimate({...p,matchupEstimate:{...x,research_only:true}}),null);
 assert.equal(m.hitEstimate({...p,matchupEstimate:{...x,opponent_aware_verified:false}}),null);
 assert.equal(m.hitEstimate({...p,matchupEstimate:{...x,model_id:""}}),null);
 assert.equal(m.hitEstimate({...p,matchupEstimate:{...x,captured_at:"2026-11-10T21:00:00Z"}}),null);
 assert.equal(m.hitEstimate({...p,matchupEstimate:{...x,modeled_selected_probability:1.5}}),null);
 for(const name of Object.keys(x.factors)){
  const factors={...x.factors};delete factors[name];
  assert.equal(m.hitEstimate({...p,matchupEstimate:{...x,factors}}),null);
  const future={...x.factors,[name]:{...x.factors[name],observed_at:"2026-11-10T21:00:00Z"}};
  assert.equal(m.hitEstimate({...p,matchupEstimate:{...x,factors:future}}),null);
 }
});
test("App shows model HIT EST, separates past games and does not misrepresent calibration",()=>{
 const html=fs.readFileSync("docs/dames-picks/index.html","utf8");
 assert.ok(html.includes("<small>Hit est.</small>"));
 assert.ok(html.includes("<label>HIT EST.</label>"));
 assert.ok(html.includes("m.hitEstimate(p)"));
 assert.ok(html.includes("Matchup-conditioned estimate for "));
 assert.ok(html.includes("not a calibrated future probability.")||html.includes("Not yet calibrated"));
 assert.ok(!html.includes("SIM EST."));
 assert.ok(!html.includes("TEST · uncalibrated"));
 assert.ok(!html.includes("RESEARCH · NOT CALIBRATED"));
 assert.ok(!html.includes("Sim est."));
 assert.ok(!html.includes("pct(p.chance)"));
 assert.ok(!html.includes("history.hits+' hits across '"));
});


test("Live player and scoreboard observations bypass delayed Pages using verified raw Github snapshots",()=>{
 const html=fs.readFileSync("docs/dames-picks/index.html","utf8");
 for(const name of ["live_player_tracking.json","nba_scoreboard_independent.json",
                    "nba_player_tracking_independent.json"])
   assert.ok(html.includes('"'+name+'"'));
 assert.ok(html.includes("raw.githubusercontent.com/damiensandoval77-lang/Sports-Bot/main/docs/"));
 assert.ok(html.includes("validLiveJSON"));
 assert.ok(html.includes("liveStamp(candidate)"));
 assert.ok(html.includes("next>before"));
 assert.ok(html.includes("Promise.allSettled(["));
 assert.ok(html.includes("if(changed)applyLive()"));
 assert.ok(!html.includes("state.nba=predict("));
});


test("Matchup probability preview attaches to exact original standard line without modifying grades",()=>{
 const original={...pt,start:"2026-11-12T02:30:00+00:00",
   market_updated:"2026-11-11T18:00:00Z",captured_at:"2026-11-11T19:00:00Z",
   grade:"PENDING"};
 const cards=m.nba({status:"FROZEN_NEW_AI_ALL_MARKET",records:[original]},null);
 const row={player_id:"201939",team:"GSW",opponent:"NOP",stat:"PTS",
    start:original.start,line:28.5,original_side:"MORE",
    captured_at:"2026-11-11T21:00:00Z",listed_position:"PG",
    matchup_projection:32.1,original_projection:31.391,
    estimated_hit_chance:{method:"POSITION_V_POSITION_DEF_RATING_RESEARCH_ANALYTIC_V1",
       modeled_selected_probability:.64,calibrated:false,research_only:true,
       verified_betting_edge:false,opponent_aware_inputs_sourced:true,
       opponent_adjustment_validated:false,
       source_provenance:{position_observed_at:"2026-11-11T20:30:00Z",
       player_observed_at:"2026-11-11T20:30:00Z",
       rating_observed_at:"2026-11-11T20:30:00Z",
       minutes_snapshot_at:"2026-11-11T20:30:00Z"}}};
 const feed={status:"POSITION_MATCHUP_RESEARCH_ONLY_PROBABILITY",production_approved:false,
   calibrated:false,captured_at:"2026-11-11T21:01:00Z",
   presentation_policy:"EXPERIMENTAL_MATCHUP_PREVIEW_NOT_CERTIFIED_HIT_EST",
   records:[row]};
 const added=m.attachMatchupPreview(cards,feed,Date.parse("2026-11-11T21:05:00Z"));
 assert.equal(added[0].matchupPreview.rate,.64);
 assert.equal(added[0].matchupPreview.projection,32.1);
 assert.equal(added[0].line,cards[0].line);
 assert.equal(added[0].projection,cards[0].projection);
 assert.equal(added[0].grade,cards[0].grade);
 assert.equal(m.hitEstimate(added[0]),null);
 assert.equal(added[0].position,"PG");
 const wrongLine={...feed,records:[{...row,line:29.5}]};
 assert.equal(m.attachMatchupPreview(cards,wrongLine,Date.parse("2026-11-11T21:05:00Z"))[0].matchupPreview,undefined);
 const futureSource={...feed,records:[{...row,estimated_hit_chance:{
    ...row.estimated_hit_chance,source_provenance:{
    ...row.estimated_hit_chance.source_provenance,rating_observed_at:"2026-11-11T23:00:00Z"}}}]};
 assert.equal(m.attachMatchupPreview(cards,futureSource,Date.parse("2026-11-11T21:05:00Z"))[0].matchupPreview,undefined);
 const fakeCalibration={...feed,records:[{...row,estimated_hit_chance:{...row.estimated_hit_chance,calibrated:true}}]};
 assert.equal(m.attachMatchupPreview(cards,fakeCalibration,Date.parse("2026-11-11T21:05:00Z"))[0].matchupPreview,undefined);
});
test("Hit estimate displays only the percentage without a redundant label underneath",()=>{
 const html=fs.readFileSync("docs/dames-picks/index.html","utf8");
 assert.ok(!html.includes("<small>Matchup model</small>"));
 assert.ok(html.includes("Accuracy and probability calibration are being tracked prospectively"));
 assert.ok(html.includes("getMatchupResearch()"));
 assert.ok(html.includes("attachMatchupPreview"));
 assert.ok(html.includes("RAW_LIVE_BASE+name"));
 assert.ok(!html.includes("SIM EST."));
 assert.ok(!html.includes("TEST · uncalibrated"));
 assert.ok(!html.includes("RESEARCH · NOT CALIBRATED"));
});


test("Public board hides internal diagnostics; opt-in page retains full release verifier",()=>{
 const html=fs.readFileSync("docs/dames-picks/index.html","utf8");
 assert.ok(html.includes('<details id="diagnostics" class="stamp" style="display:none;'));
 assert.ok(html.includes('<summary>Diagnostics</summary>'));
 assert.ok(html.includes('new URLSearchParams(window.location.search).get("diagnostics")==="1"'));
 assert.ok(html.includes('if(DIAGNOSTICS_ENABLED)$("diagnostics").style.display="block"'));
 assert.ok(html.includes('id="verify-app"'));
 assert.ok(html.includes('id="verify-result"'));
 assert.ok(html.includes('id="status"'));
 assert.ok(html.includes('$("verify-app").onclick=async()=>'));
 // All health warnings and app identities are inside the hidden disclosure.
 const diagnosticOpen=html.indexOf('<details id="diagnostics"');
 const diagnosticClose=html.indexOf("</details>",diagnosticOpen);
 for(const target of ['id="status"','id="app-build"','id="verify-app"','id="verify-result"']){
   const offset=html.indexOf(target);
   assert.ok(offset>diagnosticOpen&&offset<diagnosticClose,target+" leaked into public board");
 }
 assert.ok(html.indexOf('id="cards"')>diagnosticClose);
 assert.ok(!html.includes('style="display:block" id="diagnostics"'));
});

test("Closed developer diagnostic disclosure hides all child controls on mobile",()=>{
 const html=fs.readFileSync("docs/dames-picks/index.html","utf8");
 assert.ok(html.includes("#diagnostics:not([open]) > :not(summary){display:none!important}"));
});

test("Live game detail includes real archived standard quotes even when no AI pick exists",()=>{
 const html=fs.readFileSync("docs/dames-picks/index.html","utf8");
 assert.match(html,/gameId===g\.gameId\|\|p\.game===g\.game\)\)\)/);
 assert.ok(html.includes("const related=m.displayCurrentPicks(rows().filter(p=>(p.gameId===g.gameId||p.game===g.game)));"));
 assert.ok(html.includes('SAVED STANDARD LINE · NO AI'));
 assert.ok(html.includes('SAVED PRETIP LINE'));
 assert.ok(html.includes('NO AI FORECAST'));
 assert.ok(html.includes('Quote-only lines are never graded as model picks.'));
 const archive=JSON.parse(fs.readFileSync("docs/prizepicks_pregame_line_archive.json","utf8"));
 for(const game of ["Brooklyn Nets @ New Orleans Pelicans","Los Angeles Lakers @ Milwaukee Bucks","San Antonio Spurs @ Chicago Bulls"]){
  assert.ok(archive.quotes.some(q=>q.game===game&&q.tier==="standard"&&Date.parse(q.observed_at)<Date.parse(q.starts_at)),game);
 }
});
