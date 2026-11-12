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
    rows.push({player_id:String(a.athlete.id||""),player:name,team,PTS,REB,AST,PRA:PTS+REB+AST});
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
root.DamesPicksLive={etDate,matchup,playerRows,build,fetchNBA,mergeFeeds,mergeScores,STATUS};
})(typeof window!=="undefined"?window:globalThis);

/* Runtime execution identity: fail closed if any cached asset predates this release. */
globalThis.__damesRunningAssets=globalThis.__damesRunningAssets||Object.create(null);
globalThis.__damesRunningAssets["live_direct.js"]="dp-provisional-isolated-20261112-r18";
