const test=require('node:test'),assert=require('node:assert/strict');
require('../docs/dames-picks/feeds.js');const M=globalThis.DamesPicksModel;
const game=(name,start,state='scheduled')=>({game:name,start,state});
test('nearer NFL kickoffs precede alphabetically earlier next-week games',()=>{
 const rows=[game('ARI @ KC','2026-11-22T18:00Z'),game('NE @ DET','2026-11-15T14:30Z'),game('BUF @ NYJ','2026-11-15T18:00Z')];
 assert.deepEqual(M.sortLiveGames(rows).map(x=>x.game),['NE @ DET','BUF @ NYJ','ARI @ KC']);assert.equal(rows[0].game,'ARI @ KC');
});
test('live state priority preserved, invalid starts last and ties deterministic',()=>{
 const rows=[game('A','bad'),game('Z','2026-11-15T18:00Z'),game('B','2026-11-15T18:00Z'),game('LIVE','2026-11-22T18:00Z','in')];
 assert.deepEqual(M.sortLiveGames(rows).map(x=>x.game),['LIVE','B','Z','A']);
});
test('renderer uses tested game ordering',()=>{assert.match(require('node:fs').readFileSync(require('node:path').join(__dirname,'../docs/dames-picks/index.html'),'utf8'),/const games=m\.sortLiveGames\(slate\.filter/)});
