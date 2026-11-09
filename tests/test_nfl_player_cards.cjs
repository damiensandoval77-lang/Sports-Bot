// Browser-free regression checks for the NFL player-card renderer.
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const html = fs.readFileSync('docs/nfl/index.html', 'utf8');
const start = html.indexOf('function groupPlayerMarkets(');
const end = html.indexOf('function render(){', start);
assert(start >= 0 && end > start, 'Player grouping must be defined before render');
const source = html.slice(start, end);
assert(html.includes('groupPlayerMarkets(view.slice(0,180)).map(playerMarketCard)'), 'Board must render grouped players');
const context = {
  Map,
  esc: x => String(x),
  seasonRecord: r => '<div class="seasonbar">history-' + r.target + '</div>',
  card: r => '<article class="prop"><div class="head">duplicate-player-header</div><div class="pickbar">' + r.target + ':' + r.line + ':' + r.proj + ':' + r.model_pct + ':' + r.pick + '</div>' + '<div class="seasonbar">history-' + r.target + '</div><details><summary>Reasoning</summary><div class="detailbody">detail-' + r.target + '</div></details></article>'
};
vm.createContext(context);
vm.runInContext(source, context);
const lines = [
  { game_id:'g1', player_id:'p1', player:'Justin Jefferson', team:'MIN', opponent:'BUF', week:'9', target:'REC', line:'6.5', proj:'4.8', model_pct:'82.4', pick:'Less' },
  { game_id:'g1', player_id:'p1', player:'Justin Jefferson', team:'MIN', opponent:'BUF', week:'9', target:'TGT', line:'9.5', proj:'7.9', model_pct:'77.9', pick:'Less' },
  { game_id:'g2', player_id:'p1', player:'Justin Jefferson', team:'MIN', opponent:'GB', week:'10', target:'REC', line:'7.5', proj:'7.0', model_pct:'58.0', pick:'More' },
  { game_id:'g1', player_id:'p2', player:'Other Player', team:'MIN', opponent:'BUF', week:'9', target:'REC', line:'3.5', proj:'3.8', model_pct:'54', pick:'More' },
];
const groups = context.groupPlayerMarkets(lines);
assert.equal(groups.length,3, 'Group by game and player, not player alone');
assert.equal(groups[0].length,2, 'Two Jefferson markets must be in one game card');
const output = context.playerMarketCard(groups[0]);
assert(output.includes('2 markets'));
for(const row of lines.slice(0,2)) {
  assert(output.includes(row.target+':'+row.line+':'+row.proj+':'+row.model_pct+':'+row.pick), 'Market data preserved');
  assert(output.includes('history-'+row.target), 'Market-specific season history preserved');
  assert(output.includes('detail-'+row.target), 'Market-specific reasoning preserved');
}
assert.equal((output.match(/class="market-entry"/g)||[]).length,2, 'One market entry per quote');
assert.equal((output.match(/class="seasonbar"/g)||[]).length,2, 'No duplicate history');
assert.deepEqual(lines.map(x=>x.line),['6.5','9.5','7.5','3.5'], 'Input data remains unchanged');
console.log('NFL player grouping UI smoke tests passed');

const healthStart=html.indexOf('function boardHealth(');
const healthEnd=html.indexOf('async function init(){',healthStart);
assert(healthStart>0 && healthEnd>healthStart,'Health state controller must exist');
vm.runInContext(html.slice(healthStart,healthEnd),context);
const h=options=>context.boardHealth(options);
const base={loaded:true,scheduleReady:true,snapshotAgeHours:2,
  gradingLoaded:true,gradeHealth:{expected_final_picks:0,graded_picks:0,
  pending_picks:0,pending_reasons:{}},hasPartialSnapshot:false};
assert.equal(h(base).label,'SAVED PROPS');
assert.equal(h({...base,snapshotAgeHours:8}).label,'STALE PROPS');
assert.equal(h({...base,gradingLoaded:false}).label,'PARTIAL DATA');
assert.equal(h({...base,scheduleReady:false}).label,'PARTIAL DATA');
assert.equal(h({...base,loaded:false,scheduleReady:false}).label,'DATA UNAVAILABLE');
assert.equal(h({...base,loaded:false}).label,'PARTIAL DATA');
assert.equal(h({...base,gradeHealth:{expected_final_picks:2,graded_picks:0,
 pending_picks:2,pending_reasons:{boxscore_not_yet_published:2}}}).label,'GRADING DELAY');
assert.equal(h({...base,gradeHealth:{expected_final_picks:2,graded_picks:0,
 pending_picks:2,pending_reasons:{unsupported_exact_fantasy_scoring:2}}}).label,'SAVED PROPS');
assert(html.includes('--player-head:#050608') && html.includes('--player-name:#b4d3ff') && html.includes('player-group>.mainline .head strong'),
 'Player name color must remain distinct from market text');
console.log('NFL health states and player header styling checks passed');

const uStart=html.indexOf('function usageModelState(');
const uEnd=html.indexOf('function pctOrUnknown(',uStart);
assert(uStart>=0&&uEnd>uStart,'Usage feature activation disclosure must exist');
vm.runInContext(html.slice(uStart,uEnd),context);
assert.equal(context.usageModelState({usage_model_active:'True'}),'Included in trained model');
assert.equal(context.usageModelState({usage_model_active:'False'}),'Not all included in saved model');
assert.equal(context.usageModelState({}),'Not verified for this frozen prediction');
assert(html.includes('Usage model inputs'),'Market-level usage provenance not visible');
console.log('NFL feature provenance card checks passed');
