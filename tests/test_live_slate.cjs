const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
const ctx={Intl,Date};vm.createContext(ctx);vm.runInContext(fs.readFileSync('docs/dames-picks/feeds.js','utf8'),ctx);
const m=ctx.DamesPicksModel,now=Date.parse('2026-11-13T00:35:00Z');
const game=(id,start)=>({sport:'NBA',gameId:id,start,state:'scheduled',sourceState:'schedule'});
test('live view separates tonight from tomorrow across UTC midnight',()=>{
 const games=[game('tonight','2026-11-13T00:00:00Z'),game('late','2026-11-13T02:00:00Z'),game('tomorrow','2026-11-14T00:00:00Z')];
 assert.equal(m.currentSlateGames(games,'NBA',now).map(g=>g.gameId).join(','),'tonight,late');
 assert.equal(games.length,3,'full schedule is not changed');
});
test('fresh live game survives Eastern midnight',()=>{
 const games=[{...game('late','2026-11-13T03:30:00Z'),state:'in',fresh:true},game('next','2026-11-14T00:00:00Z')];
 assert.equal(m.currentSlateGames(games,'NBA',Date.parse('2026-11-13T05:15:00Z')).length,2);
});
test('NFL retains its weekly upcoming view',()=>{
 assert.equal(m.currentSlateGames([{sport:'NFL',gameId:'nfl'}],'NFL',now).length,1);
});
test('observed game acquires exact schedule start without losing players',()=>{
 const feed={captured_at:new Date(now).toISOString(),games:[{event_id:'espn1',game:'A @ B',state:'in',player_rows:[{player:'P',team:'A',PTS:3}]}]};
 const schedule={games:[{id:'nba1',game:'A @ B',start:'2026-11-13T00:00:00Z'}]};
 const out=m.gameCatalog(feed,null,schedule,null,now);
 assert.equal(out.length,1);assert.equal(out[0].start,schedule.games[0].start);assert.equal(out[0].players[0].stats.PTS,3);
});
