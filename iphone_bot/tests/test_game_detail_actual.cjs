const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const html=fs.readFileSync(path.join(__dirname,'../../docs/dames-picks/classic.html'),'utf8');
const render=html.slice(html.indexOf('function renderGameDetail(){'));
const actualBlock=render.slice(render.indexOf(' const normalize='),render.indexOf(' const watched='));
function actual(g,p){return vm.runInNewContext(actualBlock+'\nactualFor(p)',{g,p});}
const pick={player:'Nikola Jokić',team:'DEN',stat:'PTS',grade:'PENDING',line:26.5,projection:28,direction:'MORE'};
const game={sport:'NBA',players:[{player:'Nikola Jokic',team:'DEN',stats:{PTS:7,REB:3,AST:2}}]};
test('actual card uses exact accent-normalized player and same team',()=>{
 assert.equal(actual(game,pick),7);
 assert.equal(actual({...game,players:[{...game.players[0],player:'Nikola Jokić'}]},{...pick,player:'Nikola Jokic'}),7);
 assert.equal(actual(game,{...pick,player:'Nikola Jokic\u0301'}),7);
});
test('wrong team, fuzzy name and ambiguous accent matches remain unavailable',()=>{
 assert.equal(actual(game,{...pick,team:'NOP'}),null);
 assert.equal(actual(game,{...pick,player:'N. Jokic'}),null);
 assert.equal(actual({...game,players:[...game.players,{...game.players[0],player:'Nikola Jokić'}]},pick),null);
});
test('missing nonfinite or nonnumeric stat does not become zero',()=>{
 for(const value of [undefined,null,'7',NaN,Infinity]){
  assert.equal(actual({...game,players:[{...game.players[0],stats:{PTS:value}}]},pick),null);
 }
 assert.equal(actual({...game,players:[{...game.players[0],stats:{PTS:0}}]},pick),0);
});
test('verified immutable grade and DNP take precedence without mutation',()=>{
 const graded={...pick,grade:'GRADED',gradeSource:'OFFICIAL_FINAL',actual:30,hit:true};
 const before=JSON.stringify({game,graded});
 assert.equal(actual(game,graded),30);
 assert.equal(JSON.stringify({game,graded}),before);
 assert.equal(actual(game,{...graded,grade:'EXCLUDED_VERIFIED_DNP'}),null);
 assert.equal(actual(game,{...graded,gradeSource:null}),7);
});
test('NFL target routing unchanged',()=>{
 assert.equal(actual({sport:'NFL',players:[{player:'Joe Player',team:'ABC',stats:{PASS_YDS:123}}]},
  {player:'Joe Player',team:'ABC',target:'PASS_YDS',stat:'irrelevant'}),123);
});
