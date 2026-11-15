/* Isolated, fail-closed adapter for INTERNAL normalized tennis_board_v1 artifacts.
 * Not a parser for the provider's raw response. The collector must verify each
 * field against the actual offer, never derive standard sides or event context.
 * No production tennis forecast contract is approved: model payloads are ignored.
 * Lines are not odds/prices; the adapter never invents payout prices or estimates.
 */
(function(root){
 "use strict";
 const SOURCE="independent_prizepicksapi_com", MAX_AGE_MS=30*60*1000;
 const STATS=new Set(["Total Games","Total Games Won","Total Sets","Total Tie Breaks","Aces","Double Faults","Break Points Won","Fantasy Score"]);
 const text=v=>typeof v==="string"&&v.trim().length>0;
 const stamp=v=>typeof v==="string"&&/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?(?:Z|[+-]\d\d:\d\d)$/.test(v)?Date.parse(v):NaN;
 const finite=v=>typeof v==="number"&&Number.isFinite(v);
 function tennis(feed,now=Date.now()){
  if(!finite(now)||!feed||feed.schema_version!=="tennis_board_v1"||feed.source!==SOURCE||
     feed.source_status!=="fresh"||feed.provider_mode!=="live"||feed.is_demo!==false||!Array.isArray(feed.quotes))return [];
  const generated=stamp(feed.generated_at);
  if(!Number.isFinite(generated)||generated>now||now-generated>MAX_AGE_MS)return [];
  const rows=new Map();
  for(const q of feed.quotes){
   if(!q||![q.id,q.player_id,q.fixture_id,q.player,q.opponent].every(text)||
      q.player.trim().toLowerCase()===q.opponent.trim().toLowerCase()||
      q.status!=="active"||q.is_demo!==false||q.period!=="full_match"||
      q.is_combo!==false||q.tier!=="standard"||!STATS.has(q.stat)||
      !finite(q.line)||q.line<0)continue;
   // Only advertise independently verified available STANDARD sides.
   // The missing/unavailable/nonstandard other side is never invented.
   const standardSides=["more","less"].filter(side=>q[side+"_available"]===true&&q[side+"_tier"]==="standard");
   if(!standardSides.length)continue;
   const observed=stamp(q.observed_at),captured=stamp(q.captured_at),start=stamp(q.starts_at);
   if(![observed,captured,start].every(Number.isFinite)||observed>captured||
      captured>generated||captured>=start||start<=now||now-observed>MAX_AGE_MS)continue;
   // Exact period, line and provider identities: don't collapse player totals
   // into match totals, or silently join names across different ID namespaces.
   const key=JSON.stringify([q.fixture_id,q.player_id,q.stat,q.period,q.line,start]);
   const previous=rows.get(key);
   if(previous&&stamp(previous.observed)>=observed)continue;
   rows.set(key,{
    sport:"TENNIS",playerId:q.player_id,player:q.player.trim(),team:"",opponent:q.opponent.trim(),position:"",
    game:q.player.trim()+" vs "+q.opponent.trim(),gameId:q.fixture_id,start:q.starts_at,
    stat:q.stat,period:q.period,line:q.line,source:"Independent PrizePicks API · standard quote",
    observed:q.observed_at,captured:q.captured_at,quoteId:q.id,standardSides,
    projection:null,direction:null,chance:null,modelId:null,component:null,
    chanceSource:"Line only · estimate unavailable",quoteOnly:true,
    grade:"UNMODELED",actual:null,hit:null,gradeSource:null,
    form:{season:null,l5:null,l10:null,games:null},
    estimateStatus:"WITHHELD",estimateReason:"No validated production tennis forecast"
   });
  }
  return [...rows.values()].sort((a,b)=>stamp(a.start)-stamp(b.start)||a.player.localeCompare(b.player)||a.stat.localeCompare(b.stat));
 }
 root.DamesPicksTennis=Object.freeze({tennis,MAX_AGE_MS});
})(typeof globalThis!=="undefined"?globalThis:this);

/* Runtime identity only; all tennis estimates remain withheld. */
globalThis.__damesRunningAssets=globalThis.__damesRunningAssets||Object.create(null);
globalThis.__damesRunningAssets["tennis.js"]="dp-coherent-live-pace-20261115-r47";
