const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
const ctx={Intl,Date};vm.createContext(ctx);vm.runInContext(fs.readFileSync('docs/dames-picks/feeds.js','utf8'),ctx);
const m=ctx.DamesPicksModel;
const row=(player,rate,start='2026-11-15T00:00:00Z')=>({player,sport:'NBA',start,matchupPreview:rate===undefined?null:{rate}});
test('highest displayed hit estimate first across start times, missing last',()=>{
 const rows=[row('early',.55,'2026-11-14T00:00:00Z'),row('none'),row('high',.8),row('mid',.65),row('zero',0)];
 assert.equal(m.sortByHitEstimate(rows).map(p=>p.player).join(','),'high,mid,early,zero,none');
 assert.equal(rows[0].player,'early');
});
test('invalid preview and legacy probabilities cannot rank as available',()=>{
 const rows=[row('nan',NaN),row('string','0.99'),row('over',1.1),{...row('legacy'),model_pct:99,p_more:.99},row('valid',.6)];
 assert.equal(m.sortByHitEstimate(rows)[0].player,'valid');
 for(const p of rows.slice(0,4))assert.equal(m.displayedHitRate(p),null);
});
test('ties use start time then deterministic identity',()=>{
 assert.equal(m.sortByHitEstimate([row('Z',.6),row('A',.6),row('early',.6,'2026-11-14T00:00:00Z')]).map(p=>p.player).join(','),'early,A,Z');
});
test('board and saved picks use estimate sorting but tracker keeps team-position sorting',()=>{
 const html=fs.readFileSync('docs/dames-picks/index.html','utf8');
 assert.match(html,/if\(state.mode==="tracker"\)return m.sortByTeamPosition\(data\);\s*return m.sortByHitEstimate\(data\);/);
});
