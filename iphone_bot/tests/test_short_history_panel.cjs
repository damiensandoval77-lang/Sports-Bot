const test=require('node:test'),assert=require('node:assert/strict');
const ui=require('../../docs/dames-picks/short_history.js');
const now=Date.parse('2026-11-12T23:30:00Z');
function fixture(){
 const row={player:'Example',player_id:'123',team:'BOS',opponent:'NYK',game:'Boston @ New York',stat:'PTS',line:12.5,projection:11.2,prior_games:3,history_dates:['2026-11-05','2026-11-07','2026-11-09'],start:'2026-11-13T00:00:00Z',captured_at:'2026-11-12T23:20:00Z',market_updated:'2026-11-12T23:00:00Z',method:'SEPARATE_SHORT_HISTORY_HGB_ABSOLUTE_V1',model:'SEPARATE_SHORT_HISTORY_HGB_ABSOLUTE_V1',source:'INDEPENDENTLY_CROSSCHECKED_PLAYER_HISTORY',cohort:'SHORT_HISTORY_TRAINED_RESEARCH',research_only:true,trained_model:true,historically_evaluated:true,prospective_validation_verified:false,primary_model_eligible:false,official_grade_eligible:false,estimated_hit_chance:null,calibrated_probability:null,hit_probability:null,injury_context_status:'NO_REPORTED_OUT',pickem_tier:'standard',standard_line_two_sided_verified:true};
 return {status:'SHORT_HISTORY_TRAINED_RESEARCH_PROJECTIONS',model:row.model,generated_at:row.captured_at,official_report_issued_at:'2026-11-12T23:15:00Z',trained_model:true,historically_evaluated:true,prospective_validation_verified:false,calibrated:false,primary_model_eligible:false,official_grade_eligible:false,performance_metrics:null,model_artifact_sha256:'a'.repeat(64),accepted_markets:['PTS','REB'],estimates:[row],count:1};
}
test('isolated accepted trained cohort, not a primary pick',()=>{const f=fixture(),copy=JSON.stringify(f);assert.equal(ui.select(f,now).rows.length,1);assert.equal(JSON.stringify(f),copy)});
test('reject unsupported market, probabilities, wrong trained source and eligibility',()=>{for(const patch of [{stat:'PRA'},{hit_probability:.7},{direction:'Over'},{trained_model:false},{primary_model_eligible:true},{prospective_validation_verified:true},{model:'other'},{injury_context_status:'QUESTIONABLE'},{source:'SINGLE_SOURCE'},{player_id:'guess'}]){const f=fixture();Object.assign(f.estimates[0],patch);assert.equal(ui.select(f,now).rows.length,0,JSON.stringify(patch))}});
test('reject root calibration, invalid artifact and unsupported gate',()=>{for(const patch of [{calibrated:true},{model_artifact_sha256:null},{accepted_markets:['PRA']},{primary_model_eligible:true},{count:2}])assert.equal(ui.select({...fixture(),...patch},now).rows.length,0)});
test('reject stale, started, future or duplicate history',()=>{for(const patch of [{start:'2026-11-12T23:00:00Z'},{history_dates:['2026-11-05','2026-11-05','2026-11-09']},{captured_at:'2026-11-13T01:00:00Z'},{market_updated:'2026-11-12T10:00:00Z'}]){const f=fixture();Object.assign(f.estimates[0],patch);assert.equal(ui.select(f,now).rows.length,0)}});
test('duplicate exact identities fail closed',()=>{const f=fixture();f.estimates.push({...f.estimates[0],projection:1});f.count=2;assert.equal(ui.select(f,now).rows.length,0)});
test('renderer is disclosed, escaped, no links/buttons and hidden outside NBA board',()=>{const element={innerHTML:'',hidden:false,querySelector:()=>null},f=fixture();f.estimates[0].player='<script>bad</script>';ui.render(element,f,{now});assert.match(element.innerHTML,/Short-history model \(research\)/);assert.match(element.innerHTML,/not prospectively validated/);assert.match(element.innerHTML,/&lt;script&gt;/);assert.doesNotMatch(element.innerHTML,/<button|<a\s|<script/);for(const opts of [{league:'NFL'},{mode:'live'},{mode:'saved'}]){ui.render(element,f,{now,...opts});assert.equal(element.hidden,true);assert.equal(element.innerHTML,'')}});
test('optional integration is separate from primary cards and saved/grading adapters',()=>{
 const fs=require('node:fs');
 const html=fs.readFileSync('docs/dames-picks/index.html','utf8');
 const source=fs.readFileSync('docs/dames-picks/short_history.js','utf8');
 assert.match(html,/<section id="trained-short-history" aria-label="Short-history trained research model" hidden><\/section>/);
 assert.match(html,/state\.shortHistoryFeed=shortHistory\.status==="fulfilled"\?shortHistory\.value:null/);
 assert.match(html,/getJSON\("short_history_model.json"\)/);
 assert.equal((html.match(/state\.shortHistoryFeed/g)||[]).length,2);
 assert.doesNotMatch(source,/DamesPicksModel|state\.nba|state\.nfl|localStorage|attachLive|summarize|\.concat\(/);
});
