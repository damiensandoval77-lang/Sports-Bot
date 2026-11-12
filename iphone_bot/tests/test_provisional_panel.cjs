const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs');
const m=require('../../docs/dames-picks/provisional.js');
const NOW=Date.parse('2026-11-12T22:00:00Z');
const row={player:'Example Player',player_id:'1',team:'MEM',opponent:'DAL',game:'Memphis @ Dallas',start:'2026-11-13T00:00:00Z',stat:'PTS',line:12.5,projection:11.125,captured_at:'2026-11-12T21:55:00Z',market_updated:'2026-11-12T21:50:00Z',prior_games:3,history_dates:['2026-11-06','2026-11-08','2026-11-10'],method:'ARITHMETIC_MEAN_PRIOR_SAME_TEAM_GAMES',label:'Provisional estimate',cohort:'PROVISIONAL_SHORT_HISTORY',research_only:true,trained_model:false,primary_model_eligible:false,official_grade_eligible:false,estimated_hit_chance:null,calibrated_probability:null,hit_probability:null,injury_context_status:'NO_REPORTED_OUT',source:'INDEPENDENTLY_CROSSCHECKED_PLAYER_HISTORY',pickem_tier:'standard',standard_line_two_sided_verified:true};
function feed(r=row){return {status:'PROVISIONAL_SHORT_HISTORY_DESCRIPTIVE_BASELINE',generated_at:'2026-11-12T21:55:00Z',official_report_issued_at:'2026-11-12T21:00:00Z',cohort:'PROVISIONAL_SHORT_HISTORY',trained_model:false,primary_model_eligible:false,official_grade_eligible:false,performance_metrics:null,estimates:[r],count:1}}
function element(){return {hidden:true,innerHTML:'',querySelector(){return {open:false}}}}
test('eligible baselines remain a separate ungraded descriptive cohort',()=>{
 const got=m.select(feed(),NOW);assert.equal(got.status,'PROVISIONAL_UNGRADED');assert.equal(got.rows.length,1);assert.equal(got.rows[0].projection,11.125);
 for(const key of ['direction','lean','chance','hit_probability','grade','model','recommendation'])assert.equal(Object.hasOwn(got.rows[0],key),false);
});
test('reject unsafe flags, source, counts, probabilities and directions',()=>{
 for(const [key,value] of Object.entries({primary_model_eligible:true,official_grade_eligible:true,trained_model:true,research_only:false,prior_games:2,source:'UNVERIFIED',hit_probability:0.9,calibrated_probability:0.9,estimated_hit_chance:{rate:0.9},direction:'OVER',lean:'UNDER',confidence:0.9,method:'TRAINED_AI',injury_context_status:'PLAYER_OUT',pickem_tier:'demon',standard_line_two_sided_verified:false,projection:NaN,player:{name:'unsafe'}})){
  assert.equal(m.select(feed({...row,[key]:value}),NOW).rows.length,0,key);
 }
 assert.equal(m.select(feed({...row,prior_games:8}),NOW).rows.length,0);
});
test('reject same-day/future/duplicate/invalid history dates and missing evidence',()=>{
 for(const dates of [['2026-11-12','2026-11-08','2026-11-10'],['2026-11-13','2026-11-08','2026-11-10'],['2026-11-06','2026-11-06','2026-11-10'],['2026-02-30','2026-11-08','2026-11-10'],[]])assert.equal(m.select(feed({...row,history_dates:dates}),NOW).rows.length,0);
 for(const key of ['calibrated_probability','captured_at','market_updated','research_only','prior_games']){
  const r={...row};delete r[key];assert.equal(m.select(feed(r),NOW).rows.length,0,key);
 }
});
test('reject stale, future, started and non-pregame data',()=>{
 assert.equal(m.select({...feed(),generated_at:'2026-11-12T12:00:00Z'},NOW).rows.length,0);
 assert.equal(m.select({...feed(),generated_at:'2026-11-12T23:00:00Z'},NOW).rows.length,0);
 for(const change of [{start:'2026-11-12T21:00:00Z'},{start:'2026-11-14T00:00:00Z'},{captured_at:'2026-11-12T12:00:00Z'},{captured_at:'2026-11-13T00:01:00Z'},{market_updated:'2026-11-12T23:00:00Z'},{market_updated:'2026-11-12T21:00:00'}])assert.equal(m.select(feed({...row,...change}),NOW).rows.length,0);
});
test('wrong schema and count fail closed; no primary records accepted',()=>{
 assert.equal(m.select({status:'FROZEN_NEW_AI_ALL_MARKET',records:[row]},NOW).rows.length,0);
 for(const change of [{count:0},{performance_metrics:{}},{cohort:'PRIMARY'},{trained_model:true}])assert.equal(m.select({...feed(),...change},NOW).rows.length,0);
});
test('panel only appears on NBA Board and clears on all other views',()=>{
 const el=element();m.render(el,feed(),{now:NOW});assert.equal(el.hidden,false);assert.match(el.innerHTML,/not trained AI picks/);assert.match(el.innerHTML,/Ungraded/);assert.match(el.innerHTML,/3 completed same-team games/);
 assert.doesNotMatch(el.innerHTML,/<button|data-id=|\d%|OVER|UNDER|HIT EST/);
 for(const options of [{league:'NFL',mode:'board'},{league:'NBA',mode:'live'},{league:'NBA',mode:'saved'},{league:'NBA',mode:'tracker'}]){m.render(el,feed(),{...options,now:NOW});assert.equal(el.hidden,true);assert.equal(el.innerHTML,'')}
});
test('missing optional feed produces honest unavailable message without fake baseline',()=>{
 const el=element();m.render(el,null,{now:NOW});assert.match(el.innerHTML,/estimates unavailable/);assert.doesNotMatch(el.innerHTML,/provisional-row/);
});
test('malicious text is escaped and no feed URLs become active links',()=>{
 const el=element();m.render(el,feed({...row,player:'<img src=x onerror=alert(1)>',url:'javascript:alert(1)'}),{now:NOW});
 assert.match(el.innerHTML,/&lt;img/);assert.doesNotMatch(el.innerHTML,/<img|href=|javascript:/);
});
test('search and repeated renders retain explicit disclosure-open state',()=>{
 const el=element();el.querySelector=()=>({open:true});m.render(el,feed(),{now:NOW,term:'mem'});assert.match(el.innerHTML,/<details class="provisional-panel" open>/);assert.match(el.innerHTML,/Example Player/);
 m.render(el,feed(),{now:NOW,term:'no match'});assert.match(el.innerHTML,/No provisional estimates match/);
});
test('integration is optional and disjoint from primary statistics/adapters',()=>{
 const html=fs.readFileSync('docs/dames-picks/index.html','utf8'),source=fs.readFileSync('docs/dames-picks/provisional.js','utf8');
 assert.match(html,/<div class="cards" id="cards"><\/div><section id="provisional-short-history"/);
 assert.match(html,/state\.provisionalFeed=provisional\.status==="fulfilled"\?provisional\.value:null/);
 assert.match(html,/getJSON\("provisional_short_history.json"\)/);
 assert.doesNotMatch(source,/DamesPicksModel|state\.nba|state\.nfl|localStorage|attachLive|summarize|\.concat\(/);
 assert.equal((html.match(/state\.provisionalFeed/g)||[]).length,2);
});

test('conflicting duplicate identities all fail closed independent of row ordering',()=>{
 const a={...row},b={...row,projection:15};
 for(const estimates of [[a,b],[b,a],[a,a],[a,{...b,projection:NaN}],[{...b,projection:NaN},a]])assert.equal(m.select({...feed(),estimates,count:2},NOW).rows.length,0);
});
test('cohort and capture/report timestamps remain independently verified',()=>{
 for(const change of [{cohort:'PRIMARY'},{captured_at:'2026-11-12T21:54:00Z'}])assert.equal(m.select(feed({...row,...change}),NOW).rows.length,0);
 for(const issued of [null,'invalid','2026-11-12T22:00:00Z','2026-11-12T12:00:00Z'])assert.equal(m.select({...feed(),official_report_issued_at:issued},NOW).rows.length,0);
});

test('compact archived matchup evidence is preferred without loading the full archive',()=>{
 const html=fs.readFileSync('docs/dames-picks/index.html','utf8');
 const body=html.slice(html.indexOf('async function getMatchupResearch(){'),html.indexOf('async function refresh(){'));
 assert.match(body,/\["matchup_card_estimates.json","matchup_shadow_estimates.json"\]/);
 assert.match(body,/production_approved===false/);assert.match(body,/calibrated===false/);
 assert.doesNotMatch(body,/matchup_shadow_archive.json/);
 assert.match(html,/state.nba=m.attachMatchupPreview\(state.nba,matchupResearch.value\)/);
});
