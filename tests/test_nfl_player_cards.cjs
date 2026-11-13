// The former NFL page is now a redirect. Exercise the unified production renderer.
require('../iphone_bot/tests/test_dames_picks_vE.cjs');
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const html=fs.readFileSync('docs/nfl/index.html','utf8');
for (const [search,hash] of [['',''],['?sport=NFL','#live']]) {
 test('legacy NFL URL preserves navigation '+search+hash,()=>{
  const scripts=[...html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/g)];
  assert.equal(scripts.length,1);
  let destination;
  vm.runInNewContext(scripts[0][1],{location:{search,hash,replace:url=>{destination=url}}},{timeout:1000});
  assert.equal(destination,'../dames-picks/'+search+hash);
  assert.ok(html.includes('content="0; url=../dames-picks/"'));
  assert.ok(html.includes('href="../dames-picks/"'));
 });
}
