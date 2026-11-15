const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
require('../../docs/dames-picks/feeds.js');
const f=globalThis.DamesPicksQuoteFreshness.notice,now=Date.parse('2026-11-14T23:32:00Z');
const source=(age)=>({status:'LIVE_THIRD_PARTY_PRIZEPICKS_LINES',generated_at:new Date(now-age).toISOString()});
test('before and at sixty minutes quiet, after warns without changing source',()=>{for(const age of[0,3599999,3600000])assert.equal(f(source(age),'NBA','board',now),'');const x=source(3600001),saved=structuredClone(x);assert.match(f(x,'NBA','board',now),/over 60 minutes old/);assert.deepEqual(x,saved)});
test('missing malformed future and failed snapshots warn',()=>{for(const x of[null,{},source(-1),{status:'FAILED',generated_at:source(1).generated_at},{status:'LIVE_NATIVE_PRIZEPICKS_LINES',generated_at:'2026-11-14T23:00:00'}])assert.match(f(x,'NBA','saved',now),/freshness is unavailable/)});
test('native verified source supported and no Tennis or tracker warning',()=>{assert.equal(f({...source(1),status:'LIVE_NATIVE_PRIZEPICKS_LINES'},'NBA','board',now),'');for(const league of['TENNIS'])assert.equal(f(null,league,'board',now),'');for(const mode of['tracker','live'])assert.equal(f(null,'NBA',mode,now),'')});
test('notice is visible, separate from coverage, ages automatically and source is fetched',()=>{const html=fs.readFileSync(path.join(__dirname,'../../docs/dames-picks/index.html'),'utf8');assert.match(html,/id="nba-quote-freshness" class="coverage" role="status"/);assert.match(html,/getJSON\("prizepicks.json"\)/);assert.match(html,/setInterval\(refreshNBAQuoteNotice,5000\)/);assert.match(html,/function render\(\)\{\s*refreshNBAQuoteNotice\(\)/);assert.match(html,/id="coverage"/)});

// NFL capture-time contract participates in the same CI suite.
require('../../tests/test_quote_freshness.cjs');
