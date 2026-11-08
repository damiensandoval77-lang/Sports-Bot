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
  if(hits.length>1)return {matched:null,reason:"DUPLICATE_PLAYER"};
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
         athleteRows,canonicalTeam,matchPlayer,matchDiagnostics,isFrozenForecast,frozenPrizePicks,gameFraction,evaluate,pickRows};
});
