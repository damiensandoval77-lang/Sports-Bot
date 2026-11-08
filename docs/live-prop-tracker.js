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
 function matchPlayer(rows,forecast){
  const hits=rows.filter(r=>r.team===String(forecast.team||"").toUpperCase()&&
     normalize(r.player)===normalize(forecast.player));
  return hits.length===1?hits[0]:null;
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
  const clock=String(event?.status?.displayClock||"");
  const found=clock.match(/^(\d+):(\d{2})(?:\.\d+)?$/);
  if(!Number.isInteger(period)||period<1||!found)return null;
  const remaining=Number(found[1])*60+Number(found[2]);
  if(period<=4&&remaining<=720)return Math.max(0,Math.min(1,((period-1)*720+720-remaining)/2880));
  // Do not treat overtime as a 5th 12-minute regulation period.
  return period>4?1:null;
 }
 function evaluate(row,actual,event){
  const projection=numeric(row.combined_projection??row.projection);
  const line=numeric(row.line);
  const side=projection===null||line===null||Math.abs(projection-line)<0.05?
    "NO_LEAN":projection>line?"OVER":"UNDER";
  const state=gameStatus(event);
  const fraction=gameFraction(event);
  const final=state==="post";
  if(side==="NO_LEAN"||actual===null)return {
    side,label:actual===null?"STATS_UNAVAILABLE":"NO_MODEL_LEAN",pace:null};
  if(final)return {side,label:actual===line?"PUSH":
     (actual>line)===(side==="OVER")?"FINAL_HIT":"FINAL_MISS",pace:null};
  if(side==="OVER"&&actual>line)return {side,label:"OVER_ALREADY_CLEARED",pace:null};
  if(side==="UNDER"&&actual>line)return {side,label:"UNDER_ALREADY_LOST",pace:null};
  if(fraction===null||fraction<0.15||fraction>=1)return {
    side,label:"PACE_UNAVAILABLE_OR_EARLY",pace:null};
  const pace=Math.round(actual/fraction*10)/10;
  const supports=(side==="OVER"?pace>line:pace<line);
  return {side,label:supports?"ON_PACE":"BEHIND_PACE",pace};
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
         athleteRows,matchPlayer,isFrozenForecast,gameFraction,evaluate,pickRows};
});
