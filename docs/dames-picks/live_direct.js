/* Free browser-direct ESPN observations. Snapshots remain the fallback.
   Never alter frozen lines, predictions, or final grades. */
(function(root){
"use strict";
const BASE="https://site.api.espn.com/apis/site/v2/sports/basketball/nba";
const STATUS="OBSERVED_ESPN_LIVE_BOX_SCORES_BROWSER_DIRECT";
const SOURCE="ESPN direct (browser)";
const stamp=v=>{const n=Date.parse(v);return Number.isFinite(n)?n:NaN};
const num=v=>{if(v===null||v===undefined||v==="")return null;const n=Number(v);return Number.isFinite(n)?n:null};
function etDate(ms){
 const p=new Intl.DateTimeFormat("en-US",{timeZone:"America/New_York",year:"numeric",month:"2-digit",day:"2-digit",hour:"2-digit",hourCycle:"h23"}).formatToParts(new Date(ms));
 const v=k=>p.find(x=>x.type===k)?.value;
 return {ymd:v("year")+v("month")+v("day"),iso:v("year")+"-"+v("month")+"-"+v("day"),hour:Number(v("hour"))};
}
function matchup(competitors){
 if(!Array.isArray(competitors))return null;
 const side={};for(const c of competitors)side[c?.homeAway]=c?.team?.displayName;
 return side.away&&side.home?side.away+" @ "+side.home:null;
}
function scoresOf(competitors){
 const side={};for(const c of competitors||[])side[c?.homeAway]=num(c?.score);
 return {away:side.away??null,home:side.home??null};
}
function playerRows(summary){
 const rows=[];
 for(const group of summary?.boxscore?.players||[]){
  const team=group?.team?.abbreviation;if(!team)continue;
  for(const block of group.statistics||[]){
   const labels=(block.labels||block.names||[]).map(x=>String(x).toUpperCase());
   const ix=k=>labels.indexOf(k);
   if(ix("PTS")<0||ix("REB")<0||ix("AST")<0)continue;
   for(const a of block.athletes||[]){
    if(a?.didNotPlay||a?.didNotDress)continue;
    const name=a?.athlete?.displayName,values=a?.stats;
    if(!name||!Array.isArray(values))continue;
    const [PTS,REB,AST]=["PTS","REB","AST"].map(k=>num(values[ix(k)]));
    if(PTS===null||REB===null||AST===null)continue;
    rows.push({player_id:String(a.athlete.id||""),player:name,team,position:a.athlete.position?.abbreviation||"",PTS,REB,AST,PRA:PTS+REB+AST});
   }
  }
 }
 return rows;
}
function build(nowMs,events,summaries){
 const iso=new Date(nowMs).toISOString();
 const feed={status:STATUS,captured_at:iso,source:SOURCE,games:[],errors:[],
  player_totals_are_observations:true,not_live_sportsbook_odds:true,not_ai_predictions:true};
 const board={status:"OBSERVED_ESPN_SCOREBOARD_BROWSER_DIRECT",is_live_score_source:true,
  generated_at:iso,source:SOURCE,games:[]};
 const seen=new Set();
 for(const e of events||[]){
  const id=String(e?.id||""),st=e?.status?.type?.state;
  if(!/^\d+$/.test(id)||seen.has(id))continue;
  seen.add(id);
  const competitors=e.competitions?.[0]?.competitors,game=matchup(competitors);
  if(!game)continue;
  if(st==="in"||st==="post"){
   const score=scoresOf(competitors);
   if(score.away!==null&&score.home!==null)
    board.games.push({id,game,away_score:score.away,home_score:score.home,
      game_state:st,period:e.status?.period??null,short_detail:e.status?.type?.shortDetail||null});
  }
  if(st!=="in")continue;
  const summary=summaries?.[id];
  if(!summary){feed.errors.push({event_id:id,reason:"MISSING_SOURCE"});continue}
  if(matchup(summary?.header?.competitions?.[0]?.competitors)!==game){
   feed.errors.push({event_id:id,reason:"DIFFERENT_GAME"});continue;
  }
  const rows=playerRows(summary);
  if(!rows.length){feed.errors.push({event_id:id,reason:"NO_VERIFIED_STATS"});continue}
  const score=scoresOf(competitors);
  feed.games.push({game,event_id:id,state:st,period:e.status?.period,
   displayClock:e.status?.displayClock,clock:e.status?.clock,
   shortDetail:e.status?.type?.shortDetail,away_score:score.away,home_score:score.home,
   player_rows:rows,observed_at:iso,stale:false,source_label:SOURCE});
 }
 return {feed,board};
}
async function getJSON(url,fetchImpl,timeoutMs){
 const controller=typeof AbortController==="function"?new AbortController():null;
 const timer=controller?setTimeout(()=>controller.abort(),timeoutMs):null;
 try{
  const result=await fetchImpl(url,{cache:"no-store",signal:controller?.signal});
  if(!result.ok)throw Error("HTTP "+result.status);
  const body=await result.json();
  if(!body||typeof body!=="object")throw Error("NOT_OBJECT");
  return body;
 }finally{if(timer)clearTimeout(timer)}
}
async function fetchNBA(opts={}){
 const fetchImpl=opts.fetch||root.fetch?.bind(root);
 if(!fetchImpl)return null;
 const now=opts.now??Date.now(),timeout=opts.timeoutMs||12000;
 const today=etDate(now),dates=[today.ymd];
 if(today.hour<6)dates.unshift(etDate(now-24*3600000).ymd);
 const all=[];
 for(const d of dates){
  try{
   const body=await getJSON(BASE+"/scoreboard?dates="+d+"&limit=100",fetchImpl,timeout);
   all.push(...(body.events||[]));
  }catch(e){
   if(d===today.ymd)return null;
  }
 }
 const events=[...new Map(all.filter(e=>e?.id).map(e=>[String(e.id),e])).values()];
 const inProgress=events.filter(e=>e?.status?.type?.state==="in"&&/^\d+$/.test(String(e.id)));
 const summaries={};
 await Promise.all(inProgress.map(async e=>{
  try{summaries[e.id]=await getJSON(BASE+"/summary?event="+e.id,fetchImpl,timeout)}
  catch(_){}
 }));
 return build(now,events,summaries);
}
function mergeFeeds(snapshot,direct,now=Date.now()){
 if(!direct)return snapshot;
 const byGame=new Map();
 const valid=(g,feed)=>g?.game&&Number.isFinite(stamp(g.observed_at||feed?.captured_at))&&
   now-stamp(g.observed_at||feed?.captured_at)>=-120000&&
   now-stamp(g.observed_at||feed?.captured_at)<20*60000;
 for(const feed of [snapshot,direct]){
  for(const g of feed?.games||[]){
   if(!valid(g,feed))continue;
   const observed=g.observed_at||feed.captured_at;
   const prev=byGame.get(g.game),oldTime=stamp(prev?.observed_at);
   const rows=Array.isArray(g.player_rows)?g.player_rows:[];
   if(!prev||(rows.length>0&&(!prev.player_rows?.length||stamp(observed)>oldTime)))
     byGame.set(g.game,{...g,observed_at:observed});
  }
 }
 const games=[...byGame.values()];
 return {status:games.length?STATUS:"UNAVAILABLE",captured_at:new Date(now).toISOString(),
  source:"Newest verified ESPN observations per game",games,
  errors:direct.errors||[],player_totals_are_observations:true};
}
function mergeScores(snapshot,direct,now=Date.now()){
 // Keep independently verified scores per game. An empty, older or failed
 // direct result cannot erase a still-current genuine source observation.
 const recent=feed=>feed?.is_live_score_source===true&&Number.isFinite(stamp(feed.generated_at))&&
  now-stamp(feed.generated_at)>=-120000&&now-stamp(feed.generated_at)<20*60000;
 const merged=new Map();
 for(const feed of [snapshot,direct]){
  if(!recent(feed))continue;
  for(const game of feed.games||[]){
   if(!game?.game||!["in","post"].includes(game.game_state)||
      num(game.away_score)===null||num(game.home_score)===null)continue;
   const prev=merged.get(game.game);
   if(!prev||stamp(feed.generated_at)>prev.when)
    merged.set(game.game,{...game,when:stamp(feed.generated_at)});
  }
 }
 if(!merged.size)return snapshot&&recent(snapshot)?snapshot:null;
 return {status:"OBSERVED_ESPN_SCOREBOARD_BROWSER_DIRECT",is_live_score_source:true,
  generated_at:new Date(Math.max(...[...merged.values()].map(v=>v.when))).toISOString(),
  source:"Newest verified scores per game",
  games:[...merged.values()].map(({when,...g})=>g)};
}
const nflTeam=v=>({WSH:'WAS',JAC:'JAX',LA:'LAR'}[String(v).toUpperCase()]||String(v).toUpperCase());
function nflSides(e){const out={};for(const c of e?.competitions?.[0]?.competitors||[])out[c.homeAway]=nflTeam(c.team?.abbreviation);return out}
function nflPlayers(summary,away,home){
 const rows=new Map(),maps={passing:{YDS:'PASS_YDS',TD:'PASS_TD',INT:'PASS_INT','C/ATT':'PASS_CMP_ATT'},rushing:{YDS:'RUSH_YDS',CAR:'RUSH_ATT',ATT:'RUSH_ATT',TD:'RUSH_TD'},receiving:{YDS:'REC_YDS',REC:'REC',TGTS:'TGT',TAR:'TGT',TD:'REC_TD'}};
 for(const side of summary?.boxscore?.players||[]){
  const team=nflTeam(side.team?.abbreviation);if(![away,home].includes(team))continue;
  for(const block of side.statistics||[]){const map=maps[block.name];if(!map)continue;
   for(const a of block.athletes||[]){if(a.didNotPlay||!a.athlete?.id||!a.athlete?.displayName)continue;
    const id=team+':'+a.athlete.id,row=rows.get(id)||{player:a.athlete.displayName,team,espn_id:String(a.athlete.id),stats:{}};
    (block.labels||[]).forEach((label,i)=>{const target=map[String(label).toUpperCase()],value=a.stats?.[i];if(!target)return;
     if(target==='PASS_CMP_ATT'){const parts=String(value).split('/');if(parts.length===2&&parts.every(x=>num(x)!==null)){row.stats.PASS_CMP=num(parts[0]);row.stats.PASS_ATT=num(parts[1])}}
     else if(num(value)!==null)row.stats[target]=num(value);
    });rows.set(id,row);
   }
  }
 }
 for(const r of rows.values()){for(const [key,a,b] of [['RUSH_REC_YDS','RUSH_YDS','REC_YDS'],['PASS_RUSH_YDS','PASS_YDS','RUSH_YDS'],['ANY_TD','RUSH_TD','REC_TD']])if(r.stats[a]!==undefined&&r.stats[b]!==undefined)r.stats[key]=r.stats[a]+r.stats[b]}
 return [...rows.values()];
}
async function fetchNFL(schedule,opts={}){
 const now=opts.now??Date.now(),fetchImpl=opts.fetch||root.fetch?.bind(root);if(!fetchImpl)return null;
 const iso=new Date(now).toISOString(),base='https://site.api.espn.com/apis/site/v2/sports/football/nfl';
 const games=(schedule?.games||[]).filter(g=>stamp(g.kickoff_utc)<=now+4*3600000&&stamp(g.kickoff_utc)>=now-20*3600000);
 if(!games.length)return null;
 const board=await getJSON(base+'/scoreboard',fetchImpl,opts.timeoutMs||12000);
 const out=await Promise.all((board.events||[]).map(async e=>{
  const sides=nflSides(e),state=e.status?.type?.state;
  if(!['pre','in','post'].includes(state)||!/^\d+$/.test(String(e.id)))return null;
  const matches=games.filter(g=>nflTeam(g.away)===sides.away&&nflTeam(g.home)===sides.home&&Math.abs(stamp(g.kickoff_utc)-stamp(e.date))<=60000);
  if(matches.length!==1)return null;
  const g=matches[0],scores=scoresOf(e.competitions?.[0]?.competitors);
  if(scores.away===null||scores.home===null)return null;
  let players=[];
  if(state==='in'||state==='post')try{
   const s=await getJSON(base+'/summary?event='+e.id,fetchImpl,opts.timeoutMs||12000),ss=nflSides({competitions:s.header?.competitions});
   if(String(s.header?.id||s.header?.competitions?.[0]?.id)!==String(e.id)||ss.away!==sides.away||ss.home!==sides.home)return null;
   players=nflPlayers(s,sides.away,sides.home);
  }catch(_){return null; /* Keep last verified snapshot when summary fetch is blocked. */}
  return {game_id:g.game_id,espn_event_id:String(e.id),status:state,status_text:e.status?.type?.shortDetail||state,period:e.status?.period,clock:e.status?.displayClock,away:sides.away,home:sides.home,away_score:scores.away,home_score:scores.home,players,observed_at:iso};
 }));
 const found=out.filter(Boolean);
 return found.length?{season:2026,status:'ok',source:'espn_browser_direct',checked_at:iso,games:found}:null;
}
function mergeNFL(snapshot,direct,now=Date.now()){
 const games=new Map();
 for(const feed of [snapshot,direct]){
  if(feed?.status!=='ok')continue;
  for(const g of feed.games||[]){const at=stamp(g.observed_at||feed.checked_at);
   if(!g.game_id||!Number.isFinite(at)||now-at< -120000||now-at>=20*60000)continue;
   const old=games.get(g.game_id);if(!old||at>stamp(old.observed_at))games.set(g.game_id,{...g,observed_at:new Date(at).toISOString()});
  }
 }
 if(!games.size)return snapshot||null;
 return {status:'ok',season:2026,source:'newest_verified_nfl_observations',checked_at:new Date(Math.max(...[...games.values()].map(g=>stamp(g.observed_at)))).toISOString(),games:[...games.values()]};
}

root.DamesPicksLive={fetchNFL,mergeNFL,nflPlayers,etDate,matchup,playerRows,build,fetchNBA,mergeFeeds,mergeScores,STATUS};
})(typeof window!=="undefined"?window:globalThis);

/* Runtime execution identity: fail closed if any cached asset predates this release. */
globalThis.__damesRunningAssets=globalThis.__damesRunningAssets||Object.create(null);
globalThis.__damesRunningAssets["live_direct.js"]="dp-take-over-under-20261113-r33";
