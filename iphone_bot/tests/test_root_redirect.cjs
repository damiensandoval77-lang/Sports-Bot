const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const html=fs.readFileSync('docs/index.html','utf8');
const scripts=[...html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/g)];
for(const [search,hash] of [['',''],['?sport=NFL','#live']]) {
  test('root opens unified app preserving '+JSON.stringify({search,hash}),()=>{
    assert.equal(scripts.length,1);
    let destination=null;
    vm.runInNewContext(scripts[0][1],{location:{search,hash,replace:url=>{destination=url}}},{timeout:1000});
    assert.equal(destination,'./dames-picks/'+search+hash);
    assert.match(html,/<meta http-equiv="refresh" content="0; url=\.\/dames-picks\/">/);
    assert.match(html,/<a href="\.\/dames-picks\/">/);
    assert.doesNotMatch(html,/live-prop-tracker\.js/);
  });
}
