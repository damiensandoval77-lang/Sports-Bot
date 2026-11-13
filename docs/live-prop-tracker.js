/* Read-only NBA player prop tracker. ESPN data is not an official sportsbook feed.
 * Frozen pregame projections never change. No auto-wagers or future scores.
 */
(function(root,factory){
 const exported=factory();
 if(typeof module==="object"&&module.exports)module.exports=exported;
 if(root)root.LivePropTracker=exported;
})(typeof window!=="undefined"?window:null,function(){
 "use strict";
 const MARKETS=new Set(["PTS","REB","AST","PRA"]);
 function normalize(s){
  return String(s||"").normalize("NFD").replace(/[\u0300-\u036f]/g,"")
   .toLowerCase().replace(/[^a-z0-9]/g,"");
 }
 function numeric(v){
  if(typeof v!=="number"&&typeof v!=="string")return null;
  const s=String(v).trim();
  if(!/^(?:\d+(?:\.\d+)?|\.\d+)$/.test(s))return null;
  const n=Number(s);
  return Number.isFinite(n)&&n>=0?n:null;
 }
 function matchup(event){
  const competitors=event?.competitions?.[0]?.competitors;
  if(!Array.isArray(competitors))return null;
  const home=competitors.find(x=>x.homeAway==="home")?.team?.displayName;
  const away=competitors.find(x=>x.homeAway==="away")?.team?.displayName;
  if(!home||!away)return null;
  return away+" @ "+home;
 }
 function identifyGame(events,game){
  const found=(Array.isArray(events)?events:[]).filter(e=>matchup(e)&&
    normalize(matchup(e))===normalize(game)&&
    /^\d+$/.test(String(e.id||"")));
  return found.length===1?found[0]:null;
 }
 function gameStatus(event){
  const state=event?.status?.type?.state;
  return state==="in"||state==="post"?state:null;
 }
 function summaryGameMatch(summary,expectedGame){
  const competitions=summary?.header?.competitions;
  const competitors=Array.isArray(competitions)?competitions[0]?.competitors:null;
  if(!Array.isArray(competitors))return false;
  const away=competitors.find(x=>x.homeAway==="away")?.team?.displayName;
  const home=competitors.find(x=>x.homeAway==="home")?.team?.displayName;
  if(!away||!home)return false;
  return normalize(away+" @ "+home)===normalize(expectedGame);
 }
 function athleteRows(summary){
  const groups=summary?.boxscore?.players;
  if(!Array.isArray(groups))return [];
  const rows=[];
  for(const group of groups){
   const team=group?.team?.abbreviation;
   if(!team)continue;
   for(const statGroup of group.statistics||[]){
    const labels=statGroup.labels||statGroup.names;
    if(!Array.isArray(labels)||!Array.isArray(statGroup.athletes))continue;
    const lookup=Object.fromEntries(labels.map((x,i)=>[String(x).toUpperCase(),i]));
    for(const entry of statGroup.athletes){
     if(entry.didNotPlay||entry.didNotDress)continue;
     const values=entry.stats;
     const athlete=entry.athlete;
     if(!athlete?.displayName||!Array.isArray(values))continue;
     const stats={};
     for(const key of ["PTS","REB","AST"]){
      const pos=lookup[key];
      stats[key]=pos===undefined?null:numeric(values[pos]);
     }
     stats.PRA=["PTS","REB","AST"].every(k=>stats[k]!==null)?
        stats.PTS+stats.REB+stats.AST:null;
     rows.push({player:athlete.displayName,team:String(team).toUpperCase(),
       athlete_id:String(athlete.id||""),stats});
    }
   }
  }
  return rows;
 }
 // ESPN uses nonstandard short team codes (GS, NY, WSH, SA, NO).
 // Our projections use NBA three-letter codes (GSW, NYK, WAS, SAS, NOP).
 // Normalize only known, explicit aliases; never match a player by name
 // across teams, which could silently attach someone else's box score.
 const TEAM_ALIASES=Object.freeze({
  ATL:"ATL",BOS:"BOS",BKN:"BKN",BRK:"BKN",BK:"BKN",
  CHA:"CHA",CHI:"CHI",CLE:"CLE",DAL:"DAL",DEN:"DEN",DET:"DET",
  GSW:"GSW",GS:"GSW",HOU:"HOU",IND:"IND",LAC:"LAC",LAL:"LAL",
  MEM:"MEM",MIA:"MIA",MIL:"MIL",MIN:"MIN",NOP:"NOP",NO:"NOP",
  NYK:"NYK",NY:"NYK",OKC:"OKC",ORL:"ORL",PHI:"PHI",PHX:"PHX",PHO:"PHX",
  POR:"POR",SAC:"SAC",SAS:"SAS",SA:"SAS",TOR:"TOR",UTA:"UTA",UT:"UTA",
  WAS:"WAS",WSH:"WAS"
 });
 function canonicalTeam(team){
  const code=String(team||"").trim().toUpperCase();
  return TEAM_ALIASES[code]||code;
 }
 // A player is never matched across teams. A missing/invalid team or
 // duplicate name is intentionally unresolved rather than assigned fake stats.
 function matchDiagnostics(rows,forecast){
  const team=canonicalTeam(forecast?.team);
  if(!team||!forecast?.player)return {matched:null,reason:"INVALID_FORECAST_IDENTITY"};
  const sameName=(Array.isArray(rows)?rows:[]).filter(r=>
    normalize(r.player)===normalize(forecast.player));
  const hits=sameName.filter(r=>canonicalTeam(r.team)===team);
  if(hits.length===1)return {matched:hits[0],reason:null};
  // If ESPN duplicates the display name, a shared verified athlete ID
  // can disambiguate; never use a provider ID to override a team mismatch.
  if(hits.length>1){
   const id=String(forecast.player_id||"").trim();
   const byId=id?hits.filter(r=>String(r.athlete_id||"")===id):[];
   if(byId.length===1)return {matched:byId[0],reason:null};
   return {matched:null,reason:"DUPLICATE_PLAYER"};
  }
  if(sameName.length)return {matched:null,reason:"TEAM_MISMATCH"};
  return {matched:null,reason:"PLAYER_NOT_IN_VERIFIED_BOXSCORE"};
 }
 function matchPlayer(rows,forecast){
  return matchDiagnostics(rows,forecast).matched;
 }
 function isFrozenForecast(row){
  const created=Date.parse(row?.board_generated_at);
  const tip=Date.parse(row?.start);
  return Number.isFinite(created)&&Number.isFinite(tip)&&created<tip&&
   MARKETS.has(row.stat)&&numeric(row.line)!==null&&
   numeric(row.combined_projection??row.projection)!==null&&
   !!row.player&&!!row.team&&!!row.game;
 }
 function gameFraction(event){
  if(gameStatus(event)==="post")return 1;
  const period=Number(event?.status?.period);
  if(!Number.isInteger(period)||period<1)return null;
  // Overtime has 5-minute periods, not regulation's 12-minute periods.
  if(period>4)return null;
  const status=event?.status||{};
  const display=String(status.displayClock||"").trim();
  const found=display.match(/^(\d+):(\d{2})(?:\.\d+)?$/);
  let remaining=found?Number(found[1])*60+Number(found[2]):null;
  if(remaining===null){
   const fallback=Number(status.clock);
   if(Number.isFinite(fallback)&&fallback>=0&&fallback<=720)
    remaining=fallback;
  }
  if(remaining===null){
   const label=String(status.type?.shortDetail||status.type?.detail||"").toLowerCase();
   if(/half.?time/.test(label)||/end of (?:the )?(?:second|2nd)/.test(label))return .5;
   if(/end of (?:the )?(?:first|1st)/.test(label))return .25;
   if(/end of (?:the )?(?:third|3rd)/.test(label))return .75;
   return null;
  }
  if(remaining<0||remaining>720)return null;
  return Math.max(0,Math.min(1,((period-1)*720+720-remaining)/2880));
 }
 function evaluate(row,actual,event){
  const projection=numeric(row.combined_projection??row.projection);
  const line=numeric(row.line);
  const side=projection===null||line===null||Math.abs(projection-line)<0.05?
    "NO_LEAN":projection>line?"OVER":"UNDER";
  const state=gameStatus(event);
  const fraction=gameFraction(event);
  const final=state==="post";
  if(actual===null)return {side,label:"STATS_UNAVAILABLE",pace:null};
  // Pace remains visible even when a side has already hit/lost. It is only
  // linear extrapolation of regulation game time, never a live model forecast.
  const pace=(!final&&fraction!==null&&fraction>=.15&&fraction<1)?
   Math.round(actual/fraction*10)/10:null;
  if(side==="NO_LEAN")return {side,label:"NO_MODEL_LEAN",pace};
  if(final)return {side,label:actual===line?"PUSH":
     (actual>line)===(side==="OVER")?"FINAL_HIT":"FINAL_MISS",pace:null};
  if(side==="OVER"&&actual>line)return {side,label:"OVER_ALREADY_CLEARED",pace};
  if(side==="UNDER"&&actual>line)return {side,label:"UNDER_ALREADY_LOST",pace};
  if(pace===null)return {side,label:"PACE_UNAVAILABLE_OR_EARLY",pace:null};
  const supports=(side==="OVER"?pace>line:pace<line);
  return {side,label:supports?"ON_PACE":"BEHIND_PACE",pace};
 }
 // Convert a legitimately timestamped pregame independent pick'em research
 // record to the SAME frozen tracker shape as the historical sportsbook cards.
 // Never use the current time as a fabricated pregame capture timestamp.
 function frozenPrizePicks(records){
  const result=[];
  for(const p of records||[]){
   if(p?.source!=="independent_prizepicksapi_com"||
      p.no_calibrated_hit_percentage!==true||
      !p.provider_projection_id)continue;
   const row={
    ...p,board_generated_at:p.captured_at,
    projection:p.original_projection,
    combined_projection:p.combined_projection,
    start:p.start,game:p.game,stat:p.stat,
    line:p.line,player:p.player,player_id:p.player_id,team:p.team,
    original_pregame_source:"PRIZEPICKS_AI_RESEARCH_ONLY"
   };
   if(isFrozenForecast(row)&&
      Date.parse(p.observed_at)<=Date.parse(p.captured_at)&&
      Date.parse(p.observed_at)<Date.parse(row.start))
    result.push(row);
  }
  return result;
 }
 // A historical provider observation may be displayed next to an AI-only
 // pretip projection. It is NOT a locked bet, line-backed prediction or grade.
 // Require the provider snapshot itself to have been saved before this tipoff.
 function observedPregameLine(forecast,provider){
  const tip=Date.parse(forecast?.start),captured=Date.parse(provider?.generated_at);
  if(provider?.status!=="LIVE_THIRD_PARTY_PRIZEPICKS_LINES"||
     provider?.source!=="independent_prizepicksapi_com"||
     !Array.isArray(provider.board_offers)||
     !Number.isFinite(tip)||!Number.isFinite(captured)||
     captured>=tip||tip-captured>6*3600000||
     !MARKETS.has(forecast?.stat)||!forecast?.player||!forecast?.team||!forecast?.game)
    return null;
  const matches=[];
  for(const q of provider.board_offers){
   if(!q||q.source!=="independent_prizepicksapi_com"||q.is_demo!==false||
      normalize(q.player)!==normalize(forecast.player)||
      canonicalTeam(q.team)!==canonicalTeam(forecast.team)||
      normalize(q.game)!==normalize(forecast.game)||q.stat!==forecast.stat||
      numeric(q.line)===null||numeric(q.line)>200||
      !q.more_tier||!q.less_tier||q.more_tier!==q.less_tier||
      !["standard","goblin","demon"].includes(q.more_tier))continue;
   const start=Date.parse(q.starts_at),observed=Date.parse(q.observed_at);
   if(!Number.isFinite(start)||Math.abs(start-tip)>30*60000||
      !Number.isFinite(observed)||observed>=tip||observed>captured+600000||
      observed>captured||captured-observed>90*60000)continue;
   matches.push(q);
  }
  // Standard is the canonical threshold; fall back to separately tagged
  // selectable alternative tiers. Never pick from conflicting thresholds.
  for(const tier of ["standard","goblin","demon"]){
   const rows=matches.filter(q=>q.more_tier===tier);
   if(!rows.length)continue;
   const lines=new Set(rows.map(q=>Number(q.line)));
   if(lines.size!==1)return null;
   const first=rows[0];
   return {line:Number(first.line),tier,
     observed_at:first.observed_at,provider_projection_id:String(first.id||""),
     source:"independent_prizepicksapi_com",
     status:"OBSERVED_PRETIP_QUOTE_NOT_FROZEN_PICK"};
  }
  return null;
 }
 // Join frozen line-backed and immutable AI-only forecasts BY player/stat.
 // A single frozen pick in a game must not suppress unpriced players.
 // Keep all distinct genuine frozen thresholds; never copy a quote into the
 // original AI-only record or assign it a betting grade.
 function mergeLiveForecasts(priced,unpriced,game){
  const found=[],pricedMarkets=new Set(),unpricedMarkets=new Set();
  function marketKey(p){
   return [normalize(p.player),canonicalTeam(p.team),normalize(p.game),
           p.stat,Date.parse(p.start)].join("|");
  }
  for(const p of priced||[]){
   if(!isFrozenForecast(p)||normalize(p.game)!==normalize(game))continue;
   found.push(p);pricedMarkets.add(marketKey(p));
  }
  for(const p of unpriced||[]){
   if(!p||normalize(p.game)!==normalize(game)||!MARKETS.has(p.stat)||
      !p.player||!p.team||p.line!=null||p.is_pregame_prediction!==true||
      numeric(p.projection)===null)continue;
   const captured=Date.parse(p.captured_at),tip=Date.parse(p.start);
   if(!Number.isFinite(captured)||!Number.isFinite(tip)||captured>=tip||
      !Number.isFinite(tip)||tip>Date.now()||pricedMarkets.has(marketKey(p))||
      unpricedMarkets.has(marketKey(p)))continue;
   unpricedMarkets.add(marketKey(p));found.push(p);
  }
  return found;
 }
 // Previously captured verified quotes persist across subsequent provider
 // refreshes. They remain observations, NOT saved graded picks.
 function archivedPregameLine(forecast,archive){
  if(archive?.status!=="VERIFIED_PRETIP_PRIZEPICKS_QUOTES_ARCHIVE"||
     !Array.isArray(archive.quotes))return null;
  const tip=Date.parse(forecast?.start);
  if(!Number.isFinite(tip))return null;
  const matches=archive.quotes.filter(q=>
     q?.source==="independent_prizepicksapi_com"&&
     q.is_demo===false&&
     normalize(q.player)===normalize(forecast.player)&&
     canonicalTeam(q.team)===canonicalTeam(forecast.team)&&
     normalize(q.game)===normalize(forecast.game)&&
     q.stat===forecast.stat&&
     Number.isFinite(Date.parse(q.starts_at))&&
     Math.abs(Date.parse(q.starts_at)-tip)<=30*60000&&
     Number.isFinite(Date.parse(q.observed_at))&&
     Date.parse(q.observed_at)<tip&&
     Number.isFinite(Date.parse(q.source_generated_at))&&
     Date.parse(q.source_generated_at)<tip&&
     numeric(q.line)!==null&&numeric(q.line)<=200&&
     ["standard","goblin","demon"].includes(q.tier)&&
     q.more_tier===q.tier&&q.less_tier===q.tier);
  for(const tier of ["standard","goblin","demon"]){
   const rows=matches.filter(q=>q.tier===tier);
   if(!rows.length)continue;
   const sorted=[...rows].sort((a,b)=>Date.parse(b.observed_at)-Date.parse(a.observed_at));
   const latest=sorted[0].observed_at;
   const tied=sorted.filter(q=>q.observed_at===latest);
   if(new Set(tied.map(q=>Number(q.line))).size!==1)return null;
   return {line:Number(tied[0].line),tier,observed_at:latest,
      provider_projection_id:String(tied[0].id||""),
      source:"independent_prizepicksapi_com",
      status:"OBSERVED_PRETIP_QUOTE_NOT_FROZEN_PICK"};
  }
  return null;
 }
 // Complete a started matchup with authentic saved pretip PrizePicks
 // thresholds that have NO available frozen AI forecast. No projection,
 // direction, probability, or wager grade can be inferred from these rows.
 function quoteOnlyLiveRows(archive,game,existing,now=Date.now()){
  if(archive?.status!=="VERIFIED_PRETIP_PRIZEPICKS_QUOTES_ARCHIVE"||
     !Array.isArray(archive.quotes))return [];
  const key=p=>[normalize(p.player),canonicalTeam(p.team),
      normalize(p.game),p.stat,Date.parse(p.start)].join("|");
  const covered=new Set((existing||[]).map(key));
  const seen=new Set(),rows=[];
  for(const quote of archive.quotes){
   if(!quote||normalize(quote.game)!==normalize(game)||
      !Number.isFinite(Date.parse(quote.starts_at))||
      Date.parse(quote.starts_at)>now||
      !quote.player||!quote.team||!MARKETS.has(quote.stat))continue;
   const p={player:quote.player,team:quote.team,game:quote.game,
     start:quote.starts_at,stat:quote.stat,line:null,
     projection:null,combined_projection:null,quote_only:true,
     is_pregame_prediction:false};
   const id=key(p);
   if(covered.has(id)||seen.has(id))continue;
   // archivedPregameLine rejects post-tip source capture, nonstandard
   // identities, invalid values and ambiguous latest-tier offers.
   if(!archivedPregameLine(p,archive))continue;
   seen.add(id);
   rows.push(p);
  }
  return rows;
 }
 function pickRows(forecasts,game){
  const dedup=new Map();
  for(const x of forecasts||[]){
   if(!isFrozenForecast(x)||normalize(x.game)!==normalize(game))continue;
   const key=[String(x.player_id||normalize(x.player)),String(x.team).toUpperCase(),
              x.stat,String(x.line)].join("|");
   if(!dedup.has(key))dedup.set(key,x);
  }
  return [...dedup.values()];
 }
 return {numeric,normalize,matchup,identifyGame,gameStatus,summaryGameMatch,
         athleteRows,canonicalTeam,matchPlayer,matchDiagnostics,isFrozenForecast,frozenPrizePicks,gameFraction,evaluate,pickRows,observedPregameLine,mergeLiveForecasts,archivedPregameLine,quoteOnlyLiveRows};
});
