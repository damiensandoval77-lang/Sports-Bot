const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
const ctx={Intl,Date};vm.createContext(ctx);vm.runInContext(fs.readFileSync('docs/dames-picks/feeds.js','utf8'),ctx);
const m=ctx.DamesPicksModel;
test('NBA and NFL pace use verified regulation clock without modifying forecasts',()=>{
 assert.equal(m.livePace(10,'NBA',2,'12:00').value,40);
 assert.equal(m.livePace(10,'NBA',2,'PT12M00.00S').value,40);
 assert.equal(m.livePace(50,'NFL',2,'15:00').value,200);
 assert.equal(m.livePace(0,'NBA',2,720).value,0);
});
test('no unsupported pace from missing clock, early game, overtime or final clock',()=>{
 for(const [p,c] of [[1,'11:00'],[2,null],[2,'12:99'],[2,true],[5,'3:00'],[4,'0:00']])
  assert.equal(m.livePace(8,'NBA',p,c),null);
});
test('team then known position then player ordering, unknown positions last, input unchanged',()=>{
 const rows=[{team:'WAS',player:'W',position:'PG'},{team:'DET',player:'C',position:'C'},{team:'DET',player:'U'},{team:'DET',player:'G',position:'PG'}];
 assert.equal(m.sortByTeamPosition(rows).map(p=>p.player).join(','),'G,C,U,W');
 assert.equal(rows[0].player,'W');
});
test('fresh exact player observation attaches position and pace without changing frozen projection',()=>{
 const now=Date.parse('2026-11-13T00:45:00Z');
 const p={sport:'NBA',player:'P',team:'WAS',game:'A @ B',stat:'PTS',projection:12};
 const feed={status:'OBSERVED',captured_at:new Date(now).toISOString(),games:[{game:'A @ B',state:'in',period:2,displayClock:'12:00',player_rows:[{player:'P',team:'WSH',position:'PG',PTS:10}]}]};
 const [result]=m.attachLive([p],feed,null,now);assert.equal(result.position,'PG');assert.equal(result.live.pace.value,40);assert.equal(result.projection,12);assert.equal(p.live,undefined);
 assert.equal(m.attachLive([p],feed,null,now+21*60000)[0].live,null);
});
