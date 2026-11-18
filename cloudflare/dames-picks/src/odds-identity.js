/** Pure, fail-closed research adapter. No fetch, writes, forecast creation or grading.
 * Inputs must come from trusted roster/schedule adapters, never from quote fields.
 * Caller retains responsibility for evidence acquisition; no production capture
 * route invokes this module until that evidence pipeline is connected.
 */
const text=v=>typeof v==='string'&&v.trim().length>0;
const name=v=>String(v||'').normalize('NFKD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/[^a-z0-9]/g,'');
const time=v=>typeof v==='string'?Date.parse(v):NaN;
const finite=v=>Number.isFinite(v);
const sources=new Set(['NBA_CDN_SCHEDULE','NBA_OFFICIAL_SCHEDULE']);
const rosterSources=new Set(['NBA_CDN_ROSTER','NBA_OFFICIAL_ROSTER']);
export function verifyQuoteIdentity(quote,{events=[],roster=[],now=Date.now()}={}){
 const reject=reason=>({status:'unavailable',reason,quote:null});
 if(!Array.isArray(events)||!Array.isArray(roster))return reject('invalid_evidence');
 if(!quote||quote.league!=='NBA'||quote.source!=='the_odds_api'||quote.bookmaker!=='prizepicks'||
    quote.market_tier!=='standard'||quote.is_alternate!==false||quote.source_verified_by_response!==true)
  return reject('unsupported_quote');
 const start=time(quote.event_start),observed=time(quote.market_observed_at),captured=time(quote.collected_at);
 if(!finite(now)||![start,observed,captured].every(finite)||observed>captured||captured>now||
    start<=now||observed>=start||now-observed>90*60000||!finite(quote.line)||quote.line<0||quote.line>200||
    !text(quote.player)||!name(quote.player)||!text(quote.event_id)||
    !text(quote.home_team)||!text(quote.away_team)||quote.home_team===quote.away_team)return reject('invalid_or_stale_quote');
 // Exact provider event linkage and exact start, not calendar-date-only matching.
 const linked=events.filter(e=>e?.provider_event_id===quote.event_id);
 if(linked.length!==1)return reject('missing_or_ambiguous_event');
 const e=linked[0];
 if(e.verified!==true||!sources.has(e.source)||e.league!=='NBA'||!/^00\d{8}$/.test(e.canonical_event_id||'')||
    time(e.start)!==start||e.home_name!==quote.home_team||e.away_name!==quote.away_team||
    !text(e.home_team_id)||!text(e.away_team_id)||e.home_team_id===e.away_team_id)
  return reject('event_mismatch');
 const matches=roster.filter(p=>name(p?.name)===name(quote.player)&&
   [e.home_team_id,e.away_team_id].includes(p?.team_id));
 if(matches.length!==1)return reject('missing_or_ambiguous_player');
 const p=matches[0],asOf=time(p.as_of),until=time(p.valid_until);
 if(p.verified!==true||!rosterSources.has(p.source)||!/^\d+$/.test(p.player_id||'')||
    !finite(asOf)||!finite(until)||asOf>captured||until<start||asOf>until)
  return reject('unverified_roster_evidence');
 if((quote.player_id!=null&&String(quote.player_id)!==p.player_id)||
    (quote.player_team!=null&&quote.player_team!==p.team_id))return reject('conflicting_quote_identity');
 return {status:'verified_research_identity',reason:null,quote:{...quote,
  player_id:p.player_id,player_team:p.team_id,identity_verified:true,
  canonical_event_id:e.canonical_event_id,identity_source:p.source,event_source:e.source,
  // Market-tier evidence is provider-normalized, not native PrizePicks metadata.
  eligible_for_frozen_capture:false}};
}
