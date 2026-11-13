const test=require('node:test'),assert=require('node:assert/strict');
const {validateActivation,verifyLiveObservation}=require('../scripts/integration_live_night.cjs');
const calls='L.mergeScores(a,b); liveTick();';
test('accepts the deployed cache-busted live script',()=>{
 for(const src of ['live_direct.js','live_direct.js?bundle=release-r20'])
  assert.doesNotThrow(()=>validateActivation(`<script src="${src}"></script>${calls}`));
});
test('still rejects missing polling or a different live script',()=>{
 assert.throws(()=>validateActivation(`<script src="old/live_direct.js"></script>${calls}`));
 assert.throws(()=>validateActivation('<script src="live_direct.js?bundle=x"></script>'));
});
test('missing summary cannot pass through zero eligible-player counts',()=>{
 const row={espn_score:'30-32',fixed_card_score:'30-32',fixed_live_attached:0,picks_with_player_in_box:0};
 assert.equal(verifyLiveObservation({game:'A @ B'},null,row).length,1);
 assert.deepEqual(verifyLiveObservation({game:'A @ B'},{player_rows:[{}]},row),[]);
});
test('requires exact verified score and every eligible player attachment',()=>{
 const row={espn_score:'30-32',fixed_card_score:'29-32',fixed_live_attached:2,picks_with_player_in_box:3};
 assert.equal(verifyLiveObservation({game:'A @ B'},{player_rows:[{}]},row).length,2);
});
