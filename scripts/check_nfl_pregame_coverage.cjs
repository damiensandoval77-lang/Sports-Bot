/* Fail closed on incomplete new captures. Never backfill a pregame forecast. */
const fs=require('node:fs'), path=require('node:path');
require('../docs/dames-picks/feeds.js');
const M=globalThis.DamesPicksModel;
function check(rows,schedule,manifest,now=Date.now()){
 const games=new Map((schedule.games||[]).map(g=>[g.game_id,g]));
 const problems=[], upcoming=new Map();let available=0,verified=0,integers=0;
 for(const g of games.values()){
  const t=Date.parse(g.kickoff_utc),until=t-now;
  if(g.status!=='final'&&until>0&&until<=2*3600000)upcoming.set(g.game_id,0);
 }
 for(const r of rows){
  if(r.odds_type!=='standard')continue;
  const g=games.get(r.game_id),t=Date.parse(g?.kickoff_utc);
  if(!g||!Number.isFinite(t)){problems.push('Standard line has no verified kickoff: '+r.game_id);continue;}
  // Old in-game history is immutable, not recertified by this new-capture gate.
  if(t<=now)continue;
  available++;if(Number.isInteger(Number(r.line)))integers++;
  if(upcoming.has(r.game_id))upcoming.set(r.game_id,upcoming.get(r.game_id)+1);
  let e;try{e=JSON.parse(r.matchup_evidence||'null')}catch(_){}
  const sideFields=e&&['less','push'].every(k=>r['p_'+k]!==''&&r['p_'+k]!=null&&Number.isFinite(Number(r['p_'+k]))&&Math.abs(Number(r['p_'+k])-Number(e['modeled_'+k+'_probability']))<=1e-8);
  if(r.captured_at!==manifest.captured_at||!M.nflMatchupPreview(r,g.kickoff_utc)||e?.schema!=='NFL_OPPONENT_FEATURES_V2'||!sideFields){
   problems.push('Missing/invalid V2 pregame distribution: '+[r.game_id,r.player_id,r.target,r.line].join('/'));
  }else verified++;
 }
 for(const [id,n] of upcoming)if(!n)problems.push('No available standard lines captured within 2 hours of kickoff: '+id);
 const age=now-Date.parse(manifest.captured_at);
 if(!Number.isFinite(age)||age < -15*60000)problems.push('Invalid/future capture timestamp');
 if(upcoming.size&&age>90*60000)problems.push('Capture older than 90 minutes within 2 hours of kickoff');
 return {status:problems.length?'FAILED':'HEALTHY',captured_at:manifest.captured_at,available_standard_lines:available,verified_standard_lines:verified,integer_lines:integers,near_kickoff_games:upcoming.size,problems};
}
function main(){
 const root=process.argv[2]||'docs/nfl/data',read=f=>fs.readFileSync(path.join(root,f),'utf8');
 const manifest=JSON.parse(read('latest_2026.json'));
 const report=check(manifest.files.flatMap(f=>M.csv(read(f))),JSON.parse(read('schedule_2026.json')),manifest);
 console.log(JSON.stringify(report,null,2));
 if(process.env.GITHUB_STEP_SUMMARY)fs.appendFileSync(process.env.GITHUB_STEP_SUMMARY,'\n### NFL pregame coverage\n```json\n'+JSON.stringify(report,null,2)+'\n```\n');
 if(report.problems.length){console.error('::error::NFL pregame coverage incomplete. Preserve previous public data; retry real capture before kickoff.');process.exitCode=1;}
}
if(require.main===module)main();module.exports={check};
