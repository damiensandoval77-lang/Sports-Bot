const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const context={};vm.createContext(context);vm.runInContext(fs.readFileSync('docs/dames-picks/tennis.js','utf8'),context);
const {tennis}=context.DamesPicksTennis;
// Synthetic unit fixtures only. No real forecasts or production board are seeded.
const now=Date.parse('2026-11-14T18:00:00Z');
const quote={id:'test-only-quote',player_id:'test-player-a',fixture_id:'test-fixture',player:'Test Player A',opponent:'Test Player B',stat:'Total Games',period:'full_match',line:22.5,status:'active',is_demo:false,is_combo:false,tier:'standard',more_tier:'standard',less_tier:'standard',more_available:true,less_available:true,observed_at:'2026-11-14T17:55:00Z',captured_at:'2026-11-14T17:56:00Z',starts_at:'2026-11-14T20:00:00Z'};
const feed=(quotes=[quote])=>({schema_version:'tennis_board_v1',source:'independent_prizepicksapi_com',source_status:'fresh',provider_mode:'live',is_demo:false,generated_at:'2026-11-14T17:57:00Z',quotes});
test('Verified current full match standard line displays with no estimate or invented context',()=>{
 const rows=tennis(feed(),now);assert.equal(rows.length,1);const r=rows[0];
 assert.equal(r.sport,'TENNIS');assert.equal(r.line,22.5);assert.equal(r.gameId,quote.fixture_id);
 for(const field of ['projection','direction','chance','modelId','actual','hit'])assert.equal(r[field],null);
 assert.equal(r.quoteOnly,true);assert.equal(r.grade,'UNMODELED');assert.equal(r.team,'');
 assert.equal(r.surface,undefined);assert.equal(r.tour,undefined);
});
test('Reject unverifiable quotes individually without breaking valid rows',()=>{
 const invalid=[{is_demo:true},{is_demo:undefined},{is_combo:true},{is_combo:undefined},{tier:'goblin'},{more_tier:'demon'},{less_tier:undefined},{more_available:false},{less_available:undefined},{player_id:''},{fixture_id:''},{id:null},{opponent:''},{opponent:quote.player},{status:'live'},{period:'first_set'},{stat:'Games'},{line:null},{line:'22.5'},{line:NaN},{line:Infinity},{line:-1},{starts_at:'2026-11-14T18:00:00Z'},{captured_at:'2026-11-14T20:00:00Z'},{observed_at:'2026-11-14T17:59:00Z'},{observed_at:'2026-11-14T17:00:00Z'},{observed_at:'2026-11-14T17:55:00'},{captured_at:'2026-11-14T17:58:00Z'}];
 for(const change of invalid){assert.equal(tennis(feed([{...quote,...change}]),now).length,0,JSON.stringify(change));}
 assert.equal(tennis(feed([{...quote,is_demo:true},quote]),now).length,1);
});
test('Fail closed for absent malformed, stale, future or non-live artifacts',()=>{
 for(const input of [null,{}, {...feed(),schema_version:'raw-api'}, {...feed(),source:'demo'}, {...feed(),source_status:'PARTIAL'}, {...feed(),provider_mode:'demo'}, {...feed(),is_demo:true}, {...feed(),generated_at:'2026-11-14T17:00:00Z'}, {...feed(),generated_at:'2026-11-14T18:01:00Z'}, {...feed(),quotes:{}}])assert.equal(tennis(input,now).length,0);
 assert.equal(tennis(feed(),NaN).length,0);
});
test('No research or purported validated forecast can bypass withheld estimate gate',()=>{
 const payload={calibrated:true,validated:true,probability:.99,projection:30,direction:'MORE',model_id:'unapproved'};
 const rows=tennis({...feed([{...quote,forecast:payload,chance:.99,projection:30}]),forecasts:[payload],model_status:'APPROVED'},now);
 assert.equal(rows.length,1);assert.equal(rows[0].chance,null);assert.equal(rows[0].projection,null);
});
test('Exact stat/line/identity deduplication keeps latest observation only',()=>{
 const rows=tennis(feed([quote,{...quote,id:'new',observed_at:'2026-11-14T17:56:00Z'}, {...quote,stat:'Total Games Won'}, {...quote,line:23.5}, {...quote,player_id:'other'}, {...quote,fixture_id:'other-fixture'}]),now);
 assert.equal(rows.length,5);assert.equal(rows.find(r=>r.stat==='Total Games'&&r.line===22.5&&r.playerId===quote.player_id&&r.gameId===quote.fixture_id).quoteId,'new');
});
test('Module is additive and does not mutate input or NBA/NFL global',()=>{
 const original={nba:()=>['unchanged']};const separate={DamesPicksModel:original};vm.createContext(separate);vm.runInContext(fs.readFileSync('docs/dames-picks/tennis.js','utf8'),separate);
 assert.equal(separate.DamesPicksModel,original);const input=feed();const before=JSON.stringify(input);tennis(input,now);assert.equal(JSON.stringify(input),before);
});
