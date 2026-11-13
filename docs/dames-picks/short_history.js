/* Isolated historically evaluated short-history models; never primary picks or grades. */
(function(root){
"use strict";
const STATUS="SHORT_HISTORY_TRAINED_RESEARCH_PROJECTIONS",METHOD="SEPARATE_SHORT_HISTORY_HGB_ABSOLUTE_V1";
const esc=x=>String(x??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const stamp=x=>typeof x==="string"&&/(?:Z|[+-]\d\d:\d\d)$/.test(x)?Date.parse(x):NaN;
const amount=x=>typeof x==="number"&&Number.isFinite(x)&&x>=0&&x<=200;
function easternDay(time){
 const parts=new Intl.DateTimeFormat("en-US",{timeZone:"America/New_York",year:"numeric",month:"2-digit",day:"2-digit"}).formatToParts(new Date(time));
 const get=t=>parts.find(p=>p.type===t)?.value;
 return get("year")+"-"+get("month")+"-"+get("day");
}
function plain(x){return typeof x==="string"&&x.trim().length>0&&x.length<=160}
function validRow(r,generated,now){
 if(!r||typeof r!=="object"||Array.isArray(r)||
   !["PTS","REB"].includes(r.stat)||
   !["player","team","opponent","game"].every(k=>plain(r[k]))||!/^\d+$/.test(String(r.player_id??""))||r.team===r.opponent||
   !amount(r.line)||!amount(r.projection)||!Number.isInteger(r.prior_games)||r.prior_games<3||r.prior_games>7||
   r.method!==METHOD||r.source!=="INDEPENDENTLY_CROSSCHECKED_PLAYER_HISTORY"||
   r.cohort!=="SHORT_HISTORY_TRAINED_RESEARCH"||r.model!==METHOD||r.historically_evaluated!==true||r.prospective_validation_verified!==false||r.research_only!==true||r.trained_model!==true||r.primary_model_eligible!==false||r.official_grade_eligible!==false||
   r.estimated_hit_chance!==null||r.calibrated_probability!==null||r.hit_probability!==null||
   r.injury_context_status!=="NO_REPORTED_OUT"||r.pickem_tier!=="standard"||r.standard_line_two_sided_verified!==true||
   ["direction","lean","recommendation","hit_rate","confidence","probability"].some(k=>Object.hasOwn(r,k)))return false;
 const tip=stamp(r.start),captured=stamp(r.captured_at),quote=stamp(r.market_updated);
 if(![tip,captured,quote].every(Number.isFinite)||tip<=now||captured>=tip||quote>captured||
    captured>now+120000||captured!==generated||now-captured>6*3600000||now-quote>6*3600000)return false;
 const day=easternDay(tip);
 if(day!==easternDay(now)||!Array.isArray(r.history_dates)||r.history_dates.length!==r.prior_games||
    new Set(r.history_dates).size!==r.prior_games)return false;
 return r.history_dates.every(d=>typeof d==="string"&&/^\d{4}-\d{2}-\d{2}$/.test(d)&&
   Number.isFinite(Date.parse(d+"T00:00:00Z"))&&new Date(d+"T00:00:00Z").toISOString().slice(0,10)===d&&d<day);
}
function select(feed,now=Date.now()){
 const empty={status:"UNAVAILABLE",rows:[],rejected:0};
 if(!Number.isFinite(now)||!feed||feed.status!==STATUS||feed.model!==METHOD||feed.historically_evaluated!==true||feed.prospective_validation_verified!==false||feed.calibrated!==false||!/^([a-f0-9]{64})$/.test(feed.model_artifact_sha256??"")||!Array.isArray(feed.accepted_markets)||feed.accepted_markets.some(s=>!["PTS","REB"].includes(s))||
   feed.trained_model!==true||feed.primary_model_eligible!==false||feed.official_grade_eligible!==false||
   feed.performance_metrics!==null||!Array.isArray(feed.estimates)||feed.estimates.length>2000||
   feed.count!==feed.estimates.length)return empty;
 const generated=stamp(feed.generated_at);
 if(!Number.isFinite(generated)||generated>now+120000||now-generated>6*3600000)return empty;
 const injury=stamp(feed.official_report_issued_at);
 if(!Number.isFinite(injury)||injury>generated||now-injury>6*3600000)return empty;
 const eligible=new Map(),seen=new Set();let rejected=0;
 for(const r of feed.estimates){
  if(!r||typeof r!=="object"||Array.isArray(r)){rejected++;continue}
  const key=[r.player_id,r.team,r.game,r.start,r.stat,r.line].join("|");
  if(seen.has(key)){
   if(eligible.has(key)){eligible.delete(key);rejected++}
   rejected++;continue;
  }
  seen.add(key);
  if(!feed.accepted_markets.includes(r.stat)||!validRow(r,generated,now)){rejected++;continue}
  // Explicit whitelist: no extra probability/recommendation metadata enters the view.
  eligible.set(key,{player:r.player,team:r.team,opponent:r.opponent,stat:r.stat,line:r.line,
    projection:r.projection,priorGames:r.prior_games,dates:[...r.history_dates].sort(),start:r.start});
 }
 const rows=[...eligible.values()];
 rows.sort((a,b)=>stamp(a.start)-stamp(b.start)||a.player.localeCompare(b.player)||a.stat.localeCompare(b.stat));
 return {status:rows.length?"SHORT_HISTORY_RESEARCH_UNGRADED":"UNAVAILABLE",rows,rejected};
}
function render(element,feed,{league="NBA",mode="board",now=Date.now(),term=""}={}){
 if(!element)return;
 const visible=league==="NBA"&&mode==="board";
 element.hidden=!visible;
 if(!visible){element.innerHTML="";return}
 const wasOpen=element.querySelector?.("details")?.open===true;
 const data=select(feed,now),query=String(term).trim().toLowerCase();
 const rows=data.rows.filter(r=>!query||[r.player,r.team,r.opponent,r.stat].join(" ").toLowerCase().includes(query));
 const body=rows.length?rows.map(r=>'<article class="provisional-row"><h3>'+esc(r.player)+' · '+esc(r.stat)+'</h3><p>'+esc(r.team)+' vs '+esc(r.opponent)+'</p><dl><div><dt>Observed standard line</dt><dd>'+r.line.toFixed(1)+'</dd></div><div><dt>Trained research projection</dt><dd>'+r.projection.toFixed(1)+'</dd></div></dl><p>'+r.priorGames+' completed same-team games · independently crosschecked history</p><p>Game dates: '+esc(r.dates.join(", "))+'</p><p class="provisional-status">Ungraded · not eligible for official grades</p></article>').join(""):
 '<p class="provisional-empty">'+(data.rows.length?"No short-history model estimates match this search.":"Short-history model unavailable. No eligible current estimates have passed the evidence checks.")+'</p>';
 element.innerHTML='<details class="provisional-panel"'+(wasOpen?' open':'')+'><summary>Short-history model (research)</summary><p class="provisional-notice">Historically evaluated PTS and REB model, not prospectively validated. No calibrated hit probability or betting recommendation. Excluded from primary picks, official grades, hit rates, saved picks and live tracking.</p><p>'+rows.length+' trained research estimates · ungraded</p>'+body+(data.rejected?'<p>Some records were withheld because their evidence could not be verified.</p>':'')+'</details>';
}
const api={select,render};root.DamesShortHistory=api;
if(typeof module!=="undefined"&&module.exports)module.exports=api;
})(typeof window!=="undefined"?window:globalThis);
globalThis.__damesRunningAssets=globalThis.__damesRunningAssets||Object.create(null);
globalThis.__damesRunningAssets["short_history.js"]="dp-nfl-threshold-labels-20261113-r35";
