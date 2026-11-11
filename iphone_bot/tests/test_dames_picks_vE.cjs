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
 assert.ok(page.includes("No frozen props saved for this game. Its scoreboard and box score remain visible."));
});

test("Every game detail exposes original locked model, observed actual, ungraded state and full box score",()=>{
 const html=fs.readFileSync("docs/dames-picks/index.html","utf8");
 for(const text of ["FROZEN LINE","FROZEN PROJ","ACTUAL","LIVE · NOT GRADED",
 "Full published player box score","Scoreboard","data-prop","Actual unavailable",
 "No frozen props saved for this game"])assert.ok(html.includes(text),text);
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
 assert.ok(html.includes('Date.now(),nbaScores.status==="fulfilled"?nbaScores.value:null'));
});
