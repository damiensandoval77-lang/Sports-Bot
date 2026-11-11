// Live ESPN browser-direct behavioral contracts. All fixtures are original synthetic test data.
const test=require("node:test"),assert=require("node:assert/strict"),fs=require("node:fs"),vm=require("node:vm");
const ctx={Intl,Date,AbortController,setTimeout,clearTimeout};vm.createContext(ctx);
for(const f of ["feeds.js","live_direct.js"])vm.runInContext(fs.readFileSync("docs/dames-picks/"+f,"utf8"),ctx);
const m=ctx.DamesPicksModel,L=ctx.DamesPicksLive;
const plain=x=>JSON.parse(JSON.stringify(x));
const competitors=(away,home,a,h)=>[
 {homeAway:"away",team:{displayName:away},score:a},
 {homeAway:"home",team:{displayName:home},score:h}];
const event=(id,status,away,home,a,h)=>({id,
 status:{period:2,displayClock:"5:00",type:{state:status,shortDetail:"5:00 · 2nd"}},
 competitions:[{competitors:competitors(away,home,a,h)}]});
const summary=(away,home,team,rows)=>({
 header:{competitions:[{competitors:competitors(away,home)}]},
 boxscore:{players:[{team:{abbreviation:team},
  statistics:[{labels:["MIN","PTS","REB","AST"],athletes:rows}]}]}});
const player=(id,name,stats,extra={})=>({athlete:{id,displayName:name},stats,...extra});
const NOW=Date.parse("2026-11-11T01:10:00Z");
test("ESPN aliases attach Knicks, Jazz, Warriors, Pelicans, Spurs, Wizards to the correct ledger franchise",()=>{
 for(const [api,ledger] of [["NY","NYK"],["UTAH","UTA"],["GS","GSW"],["NO","NOP"],["SA","SAS"],["WSH","WAS"]])
  assert.equal(m.nbaTeam(api),m.nbaTeam(ledger));
 const {feed}=L.build(NOW,[event("1","in","Milwaukee Bucks","New York Knicks","34","58")],
  {"1":summary("Milwaukee Bucks","New York Knicks","NY",[player("9","Jalen Brunson",["20","14","2","6"])])});
 const [r]=m.attachLive([{sport:"NBA",player:"Jalen Brunson",team:"NYK",
  game:"Milwaukee Bucks @ New York Knicks",stat:"PRA"}],feed,null,NOW);
 assert.equal(r.live.actual,22);
 assert.equal(r.live.source,"ESPN direct (browser)");
});
test("DNP rows are excluded and mismatched game summaries never attach a player's totals",()=>{
 const {feed}=L.build(NOW,[event("1","in","A","B","1","2"),event("2","in","C","D","3","4")],
  {"1":summary("A","B","AAA",[player("1","Played",["10","4","1","1"]),player("2","Sat",[],{didNotPlay:true})]),
   "2":summary("X","Y","CCC",[player("3","Wrong",["9","9","9","9"])])});
 assert.deepEqual(plain(feed.games[0].player_rows.map(p=>p.player)),["Played"]);
 assert.deepEqual(plain(feed.errors.map(e=>e.reason)),["DIFFERENT_GAME"]);
});
test("Pregame scores do not masquerade as live; in and final scores are real observations",()=>{
 const {board}=L.build(NOW,[event("1","pre","A","B","0","0"),
  event("2","in","C","D","50","48"),event("3","post","E","F","101","99")],{});
 assert.deepEqual(plain(board.games.map(g=>[g.game,g.away_score,g.home_score,g.game_state])),
  [["C @ D",50,48,"in"],["E @ F",101,99,"post"]]);
});
test("Per-game newer genuine player observations supersede older and empty upstream cannot erase them",()=>{
 const snapshot={status:"OK",captured_at:"2026-11-11T01:08:00Z",games:[
  {game:"A @ B",state:"in",observed_at:"2026-11-11T01:08:00Z",player_rows:[{player:"Old"}]},
  {game:"C @ D",state:"in",observed_at:"2026-11-11T01:09:59Z",player_rows:[{player:"Keep"}]}]};
 const direct={captured_at:"2026-11-11T01:09:00Z",games:[
  {game:"A @ B",state:"in",observed_at:"2026-11-11T01:09:00Z",player_rows:[{player:"New"}]},
  {game:"C @ D",state:"in",observed_at:"2026-11-11T01:09:00Z",player_rows:[]}]};
 const result=L.mergeFeeds(snapshot,direct,NOW);
 assert.equal(result.games.find(g=>g.game==="A @ B").player_rows[0].player,"New");
 assert.equal(result.games.find(g=>g.game==="C @ D").player_rows[0].player,"Keep");
 assert.equal(result.games.length,2);
});
test("Direct scoreboard restores scores on actual merged live matchup cards even if snapshot is stale",()=>{
 const stale={generated_at:"2026-11-10T17:00:00Z",is_live_score_source:true,
  games:[{id:"7",game:"A @ B",game_state:"pre",away_score:null,home_score:null}]};
 const {feed,board}=L.build(NOW,[event("7","in","A","B","30","28")],
  {"7":summary("A","B","AAA",[player("1","P",["10","4","1","1"])])});
 const actual=m.gameCatalog(feed,null,null,null,NOW,L.mergeScores(stale,board,NOW));
 assert.equal(actual[0].awayScore,30);assert.equal(actual[0].homeScore,28);
 assert.equal(actual[0].players.length,1);
});
test("Fresh per-game score wins independently; stale or mismatched scores never overwrite good scores",()=>{
 const old={generated_at:"2026-11-11T01:06:00Z",is_live_score_source:true,
  games:[{id:"7",game:"A @ B",game_state:"in",away_score:30,home_score:28},
   {id:"8",game:"C @ D",game_state:"in",away_score:40,home_score:39}]};
 const fresh={generated_at:"2026-11-11T01:09:00Z",is_live_score_source:true,
  games:[{id:"7",game:"A @ B",game_state:"in",away_score:35,home_score:31}]};
 const merged=L.mergeScores(old,fresh,NOW);
 assert.equal(merged.games.find(g=>g.game==="A @ B").away_score,35);
 assert.equal(merged.games.find(g=>g.game==="C @ D").away_score,40);
 const failed=L.mergeScores(merged,null,NOW);
 assert.equal(failed.games.length,2);
});
test("ESPN network failure retains fallback: never invent success",async()=>{
 const result=await L.fetchNBA({now:NOW,fetch:async()=>({ok:false,status:403})});
 assert.equal(result,null);
});
