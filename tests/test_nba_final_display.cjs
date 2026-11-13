const assert=require('assert'),fs=require('fs');require('../docs/dames-picks/feeds.js');const m=globalThis.DamesPicksModel;
const g={sport:'NBA',state:'final',start:'2026-11-13T00:00:00Z',away:'DET',home:'WAS',players:[]};
const row={player:'Test',team:'WSH',opponent:'DET',date:'2026-11-12',source:'NBA_CDN_FINAL',source_game_id:'002',final_confirmed:true,MIN:1,PTS:0,REB:0,AST:0,PRA:0};
const attach=rows=>m.attachNBAFinals([g],{rows})[0];
assert.equal(attach([row]).players[0].stats.PTS,0);
for(const change of [{MIN:0},{final_confirmed:false},{date:'2026-11-11'},{opponent:'PHI'},{source:'MODEL'},{PTS:null}])assert.equal(attach([{...row,...change}]).players.length,0);
assert.equal(attach([row,row]).players.length,0);
assert.equal(attach([row,{...row,source_game_id:'other'}]).players.length,0);
assert.equal(m.attachNBAFinals([{...g,state:'in'}],{rows:[row]})[0].players.length,0);
const real=JSON.parse(fs.readFileSync('docs/verified_final_player_cache.json'));
const final= m.attachNBAFinals([g],real)[0];assert(final.players.length>10);assert(final.players.some(p=>p.player==='Cade Cunningham'));
console.log('Verified final display: exact day/teams, provenance, zero, DNP, conflicts and production DET/WAS cache pass');

const score=JSON.parse(fs.readFileSync("docs/nba_scoreboard_independent.json")),schedule=JSON.parse(fs.readFileSync("docs/nba_schedule.json"));
const catalog=m.attachNBAFinals(m.gameCatalog(null,null,schedule,null,Date.parse(score.generated_at),score),real);
assert(catalog.some(g=>g.finalBoxscore&&g.players.some(p=>p.player==="Cade Cunningham")),"Schedule full-name identity must preserve abbreviations");

assert.equal(attach([row,{...row,player:"Inactive",source:"ESPN_FINAL",source_game_id:"espn",MIN:null,dnp_final_verified:true}]).players.length,1,"DNP evidence from alternate official provider cannot suppress played boxscore");
