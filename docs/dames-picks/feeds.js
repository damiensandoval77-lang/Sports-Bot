/* Unified NBA / NFL read-only adapter. Every displayed number originates in a published bot artifact. */
(function(root){
"use strict";
const n=v=>v===null||v===undefined||v===""?null:Number.isFinite(Number(v))?Number(v):null;
const norm=v=>String(v||"").normalize("NFKD").toLowerCase().replace(/[\u0300-\u036f]/g,"").replace(/[^a-z0-9]/g,"");
const stamp=v=>{const d=Date.parse(v);return Number.isFinite(d)?d:NaN};
// ESPN and the immutable wager ledger use different team abbreviations.
// Alias only known, unambiguous franchises; never fuzzy-match a player/team.
const NBA_TEAM_ALIASES=Object.freeze({NY:"NYK",GS:"GSW",NO:"NOP",SA:"SAS",UTAH:"UTA",WSH:"WAS"});
const nbaTeamCode=v=>{
 const code=String(v||"").trim().toUpperCase();
 return NBA_TEAM_ALIASES[code]||code;
};

const key=p=>[p.sport,p.playerId||norm(p.player),p.gameId||p.game,p.start,p.stat,p.line,p.captured].join("|");
function csv(text){
 let cells=[],row=[],field="",quoted=false;
 for(let i=0;i<text.length;i++){
  let c=text[i];
  if(c==='"'){if(quoted&&text[i+1]==='"'){field+='"';i++}else quoted=!quoted}
  else if(c===","&&!quoted){row.push(field);field=""}
  else if((c==="\n"||c==="\r")&&!quoted){if(c==="\r"&&text[i+1]==="\n")i++;row.push(field);field="";if(row.some(x=>x!==""))cells.push(row);row=[]}
  else field+=c;
 }
 if(field||row.length){row.push(field);cells.push(row)}
 const headers=cells.shift()||[];
 return cells.map(r=>Object.fromEntries(headers.map((h,i)=>[h,r[i]??""])));
}
function nba(ledger,form){
 if(ledger?.status!=="FROZEN_NEW_AI_ALL_MARKET"||!Array.isArray(ledger.records))return [];
 const people=new Map((form?.players||[]).map(p=>[p.player_id+"|"+p.team,p]));
 return ledger.records.filter(p=>{
  const c=p?.estimated_hit_chance;
  return p&&p.pickem_tier==="standard"&&p.standard_line_two_sided_verified===true&&p.research_only===true&&
   p.production_replaced===false&&n(p.line)!==null&&n(p.projection)!==null&&
   ["PTS","REB","AST","PRA"].includes(p.stat)&&
   stamp(p.market_updated)<=stamp(p.captured_at)&&stamp(p.captured_at)<stamp(p.start)&&
   c?.method==="JOINT_2024_25_VALIDATION_RESIDUALS_20K_UNCALIBRATED"&&
   c.draws===20000&&c.calibrated===false&&
   ["More","Less"].includes(c.modeled_direction)&&n(c.modeled_selected_probability)!==null;
 }).map(p=>{
  const c=p.estimated_hit_chance,person=people.get(p.player_id+"|"+p.team),metrics=person?.metrics?.[p.stat];
  const prob=n(c.modeled_selected_probability),
        grade=p.grade==="GRADED"?"GRADED":
              p.grade==="EXCLUDED_VERIFIED_DNP"?"EXCLUDED_VERIFIED_DNP":"PENDING";
  return {
   sport:"NBA",playerId:p.player_id,player:p.player,team:p.team,opponent:p.opponent,
   position:"",game:p.game,gameId:p.game,start:p.start,stat:p.stat,source:"PrizePicks",
   line:n(p.line),projection:n(p.projection),direction:c.modeled_direction==="More"?"MORE":"LESS",
   chance:prob>=0&&prob<=1?prob:null,chanceSource:"20,000 historical-residual simulations; uncalibrated",
   captured:p.captured_at,grade,actual:grade==="GRADED"?n(p.actual):null,
   hit:grade==="GRADED"&&typeof p.direction_hit==="boolean"?p.direction_hit:null,
   gradeSource:grade!=="PENDING"?p.final_source:null,
   form:{season:n(metrics?.season),l5:n(metrics?.l5),l10:n(metrics?.l10),games:person?.games||null},
   modelId:"FROZEN_NEW_AI_ALL_MARKET",component:p.components||null
  };
 });
}
function nfl(chunks,schedule){
 const games=new Map((schedule?.games||[]).map(g=>[g.game_id,g]));
 const found=new Map();
 for(const p of chunks.flat()){
  const game=games.get(p.game_id);
  if(!game||p.odds_type!=="standard"||n(p.line)===null||n(p.proj)===null||
   !p.player||!p.player_id||!p.stat||!["More","Less"].includes(p.pick)||
   !(stamp(p.captured_at)<stamp(game.kickoff_utc)))continue;
  const prob=n(p.p_more),direction=p.pick==="More"?"MORE":"LESS";
  const chance=prob!==null&&prob>=0&&prob<=1?(direction==="MORE"?prob:1-prob):null;
  let logs=[];try{logs=JSON.parse(p.season_game_log||"[]")}catch(_){}
  const obj={
   sport:"NFL",playerId:p.player_id,player:p.player,position:p.position||"",team:p.team,opponent:p.opponent,
   game:p.team+" vs "+p.opponent,gameId:p.game_id,start:game.kickoff_utc,stat:p.stat,target:p.target,
   source:"PrizePicks",line:n(p.line),projection:n(p.proj),direction,chance,
   chanceSource:"NFL model estimate; not a calibrated hit probability",
   captured:p.captured_at,grade:"PENDING",actual:null,hit:null,gradeSource:null,
   form:{season:n(p.season_avg),l5:null,l10:null,games:n(p.season_games),
    over:n(p.season_over),under:n(p.season_under),push:n(p.season_push),
    last5Over:n(p.season_last5_over),last5Under:n(p.season_last5_under)},
   depth:{role:p.depth_role||null,rank:n(p.depth_rank),ahead:n(p.depth_ahead),
    slot:p.depth_slot||null,asOf:p.depth_asof||null,
    snapPct:n(p.snap_pct_l3),targetShare:n(p.target_share_l3),
    carryShare:n(p.carry_share_l3)},
   logs:Array.isArray(logs)?logs.slice(0,6):[],modelId:p.projection_id||null,component:null
  };
  const k=key(obj);
  const old=found.get(k);
  if(!old||stamp(old.captured)<stamp(obj.captured))found.set(k,obj);
 }
 return [...found.values()];
}
/* A player/stat/game may have several immutable pretip quote versions.
   One canonical CURRENT display card per market, preserving every original
   record unchanged for research and exact version-specific settlement.
   The most recent genuine captured STANDARD modeled offer before tip wins;
   quote-only records cannot displace a valid frozen AI model. */
function primaryDisplayLines(rows){
 const map=new Map();
 for(const p of rows||[]){
  if(!p||!p.sport||!p.stat||!p.gameId||!Number.isFinite(stamp(p.start)))continue;
  const id=[p.sport,p.gameId,p.start,p.playerId||norm(p.player),p.team,p.stat,p.source?.includes("Underdog")?"Underdog":"PrizePicks"].join("|");
  const prev=map.get(id);
  const weight=x=>x.quoteOnly?0:x.projection!==null&&x.direction?2:1;
  const newer=(a,b)=>Number.isFinite(stamp(a.captured))&&stamp(a.captured)>stamp(b.captured);
  if(!prev||weight(p)>weight(prev)||(weight(p)===weight(prev)&&
    (newer(p,prev)||(stamp(p.captured)===stamp(prev.captured)&&Number(p.line)>Number(prev.line)))))
    map.set(id,p);
 }
 return [...map.values()];
}
function summarize(rows,nflHealth,now=Date.now(),league=null){
 const pre=rows.filter(r=>stamp(r.start)>now),gameCount=new Set(pre.map(r=>r.gameId)).size;
 // Only the NBA market ledger has individually verified directional grading here.
 const graded=(league==="NFL"?rows:primaryDisplayLines(rows)).filter(r=>r.grade==="GRADED"&&typeof r.hit==="boolean");
 if((league||rows[0]?.sport)==="NFL"){
  const settled=n(nflHealth?.standard_settled),wins=n(nflHealth?.standard_wins);
  return {games:gameCount,wins:settled!==null&&wins!==null?wins:null,
   losses:settled!==null&&wins!==null?settled-wins:null,
   hitRate:settled>0&&wins!==null?wins/settled:null,
   graded:settled||0,pending:n(nflHealth?.pending_picks)};
 }
 const wins=graded.filter(x=>x.hit).length;
 return {games:gameCount,wins:graded.length?wins:null,losses:graded.length?graded.length-wins:null,
  hitRate:graded.length?wins/graded.length:null,graded:graded.length,
  pending:primaryDisplayLines(rows).filter(x=>x.grade==="PENDING").length};
}

/* Select a fresh real player feed instead of blindly preferring an empty
   legacy snapshot. A later verified game observation wins PER matchup;
   unavailable/empty sources never erase genuine previously observed rows.
   This does not infer a single player statistic. */
function preferredNBALiveFeed(primary,independent,now=Date.now()){
 const valid=feed=>feed&&[
  "OK","OBSERVED_NBA_LIVEDATA_PLAYER_BOXSCORES",
  "PARTIAL_NBA_PLAYER_BOXSCORES",
  "OBSERVED_ESPN_PLAYER_TOTALS",
  "OBSERVED_ESPN_LIVE_BOX_SCORES_SERVER_FALLBACK",
  "OBSERVED_ESPN_LIVE_BOX_SCORES_BROWSER_DIRECT"
 ].includes(feed.status)&&Array.isArray(feed.games)&&
 Number.isFinite(stamp(feed.captured_at))&&
 now-stamp(feed.captured_at)>=-120000&&now-stamp(feed.captured_at)<20*60000;
 const saved=new Map();
 for(const feed of [primary,independent]){
  if(!valid(feed))continue;
  for(const g of feed.games){
   if(!g?.game||!["in","post","pre"].includes(g.state))continue;
   const at=stamp(g.observed_at||feed.captured_at);
   if(!Number.isFinite(at)||now-at< -120000||now-at>=20*60000)continue;
   const previous=saved.get(g.game);
   const rows=Array.isArray(g.player_rows)?g.player_rows:[];
   const priorAt=previous?stamp(previous.observed_at):NaN;
   // A newer verified player observation wins. Never replace populated live
   // rows with an empty pending/pregame response.
   if(!previous || (rows.length>0 &&
       (!Array.isArray(previous.player_rows)||!previous.player_rows.length||at>priorAt)))
     saved.set(g.game,{...g,observed_at:g.observed_at||feed.captured_at});
  }
 }
 const games=[...saved.values()];
 return {status:games.length?"OBSERVED_NBA_LIVEDATA_PLAYER_BOXSCORES":"UNAVAILABLE",
  captured_at:new Date(now).toISOString(),games,
  source:"Selected verified recent player observations by matchup"};
}

/* Merge observation feeds by exact game/player/team. No observations alter frozen projections. */
function attachLive(rows,nbaFeed,nflFeed,now=Date.now()){
 const nbaFresh=nbaFeed?.status&&Number.isFinite(stamp(nbaFeed.captured_at))&&
  Math.abs(now-stamp(nbaFeed.captured_at))<20*60000;
 const nflFresh=nflFeed?.status==="ok"&&Number.isFinite(stamp(nflFeed.checked_at))&&
  Math.abs(now-stamp(nflFeed.checked_at))<20*60000;
 const nbaGames=new Map((nbaFresh?nbaFeed.games:[]).filter(g=>
  g.state==="in"&&g.stale!==true&&
  Number.isFinite(stamp(g.observed_at||nbaFeed.captured_at))&&
  now-stamp(g.observed_at||nbaFeed.captured_at)>=-120000&&
  now-stamp(g.observed_at||nbaFeed.captured_at)<20*60000
 ).map(g=>[g.game,g]));
 const nflGames=new Map((nflFresh?nflFeed.games:[]).filter(g=>g.status==="in").map(g=>[g.game_id,g]));
 return rows.map(p=>{
  if(p.sport==="NBA"){
   const game=nbaGames.get(p.game);
   const hits=(game?.player_rows||[]).filter(x=>nbaTeamCode(x.team)===nbaTeamCode(p.team)&&norm(x.player)===norm(p.player));
   if(hits.length!==1)return {...p,live:null};
   const actual=n(hits[0][p.stat]);
   return {...p,live:actual===null?null:{actual,gameStatus:game.shortDetail||game.displayClock||"In progress",
    period:game.period,observedAt:game.observed_at||nbaFeed.captured_at,source:game.source_label||"ESPN player snapshot"}};
  }
  const game=nflGames.get(p.gameId);
  const hits=(game?.players||[]).filter(x=>x.team===p.team&&norm(x.player)===norm(p.player));
  if(hits.length!==1||!p.target)return {...p,live:null};
  const actual=n(hits[0].stats?.[p.target]);
  return {...p,live:actual===null?null:{actual,gameStatus:game.status_text||"In progress",
   period:game.period,observedAt:nflFeed.checked_at,source:"ESPN player snapshot"}};
 });
}
/* NFL settlement is joined ONLY with full immutable quote identity. */
function attachNFLGrades(rows,graded){
 const entries=new Map();
 for(const x of graded||[]){
  if(String(x.grade_status||"").toLowerCase()!=="graded"||x.odds_type!=="standard"||n(x.actual)===null||
   !["true","false","1","0"].includes(String(x.won).toLowerCase()))continue;
  const k=[x.game_id,x.player_id,x.stat,x.line,x.captured_at].join("|");
  if(entries.has(k))entries.set(k,null);else entries.set(k,x);
 }
 return rows.map(p=>{
  if(p.sport!=="NFL")return p;
  const x=entries.get([p.gameId,p.playerId,p.stat,p.line,p.captured].join("|"));
  return x?{...p,grade:"GRADED",actual:n(x.actual),hit:["true","1"].includes(String(x.won).toLowerCase()),gradeSource:"NFL verified final prop ledger"}:p;
 });
}

/* The NFL permanent frozen-price settlement archive is authoritative for
   FINAL result cards. The newest pregame snapshot is not a history archive;
   earlier saved line prices must stay visible after it rotates.
   Only finalized scheduled games and unchanged pretip prices can be joined. */
function reconcileNFLSettlementCards(latest,gradedRows,pendingRows,schedule){
 const games=new Map((schedule?.games||[]).map(g=>[g.game_id,g]));
 const byKey=p=>[p.gameId,p.playerId,p.stat,fmtQuote(p.line),p.captured].join("|");
 const existing=new Map(latest.filter(p=>p.sport==="NFL").map(p=>[byKey(p),p]));
 for(const [records,kind] of [[gradedRows,"graded"],[pendingRows,"pending"]]){
  for(const r of records||[]){
   const game=games.get(r.game_id);
   const at=stamp(r.captured_at),kickoff=stamp(game?.kickoff_utc);
   const valid=game?.status==="final"&&n(game.home_score)!==null&&
      n(game.away_score)!==null&&Number.isFinite(at)&&Number.isFinite(kickoff)&&
      at<kickoff&&r.odds_type==="standard"&&
      !!r.player_id&&!!r.player&&!!r.stat&&n(r.line)!==null&&n(r.proj)!==null&&
      ["More","Less"].includes(r.pick);
   if(!valid)continue;
   const settled=kind==="graded"&&String(r.grade_status||"").toLowerCase()==="graded"&&
      n(r.actual)!==null&&(
       ["0","1"].includes(String(r.won))||
       (r.result==="Push"&&String(r.won)===""));
   const waiting=kind==="pending"&&
      !!String(r.grade_status||"").trim()&&
      String(r.grade_status).toLowerCase()!=="graded"&&
      n(r.actual)===null;
   if(!settled&&!waiting)continue;
   const key=[r.game_id,r.player_id,r.stat,fmtQuote(r.line),r.captured_at].join("|");
   const present=existing.get(key);
   if(present && (present.player!==r.player||present.team!==r.team||
       present.direction!==(r.pick==="More"?"MORE":"LESS")||
       Math.abs(present.projection-n(r.proj))>1e-5)){
     // Never mix two distinct model forecasts just because they share a price.
     continue;
   }
   const hit=settled?(r.result==="Push"?null:r.won==="1"):null;
   const extra={grade:settled?"GRADED":"PENDING",actual:settled?n(r.actual):null,
      hit,gradeSource:settled?"Verified NFL final player boxscore":null,
      pendingReason:waiting?r.grade_status:null,
      frozenSettlementArchive:true};
   if(present){
    existing.set(key,{...present,...extra});
   }else{
    const pct=n(r.model_pct);
    const p={sport:"NFL",playerId:r.player_id,player:r.player,position:r.position||"",
       team:r.team,opponent:r.opponent,game:r.team+" vs "+r.opponent,
       gameId:r.game_id,start:game.kickoff_utc,stat:r.stat,target:r.target,
       source:"PrizePicks",line:n(r.line),projection:n(r.proj),
       direction:r.pick==="More"?"MORE":"LESS",
       chance:pct!==null&&pct>=0&&pct<=100?pct/100:null,
       chanceSource:"Original saved NFL model estimate, not a calibrated hit probability",
       captured:r.captured_at,form:{season:null,l5:null,l10:null,games:null},
       logs:[],depth:null,modelId:null,component:null,...extra};
    existing.set(key,p);
   }
  }
 }
 return [...existing.values()];
}
function fmtQuote(v){return n(v)===null?"":String(n(v))}
/* Official NBA injury labels are context only; do not retroactively alter picks. */
function attachInjuries(rows,report){
 if(report?.status!=="OFFICIAL_NBA_REPORT_VERIFIED"||
    report.injury_data_verified!==true||!Array.isArray(report.players))return rows;
 const issued=stamp(report.report_issued_at),updated=stamp(report.generated_at);
 if(!Number.isFinite(issued)||!Number.isFinite(updated)||issued>updated+10*60000)return rows;
 const eastern=t=>{
  const parts=new Intl.DateTimeFormat("en-US",{timeZone:"America/New_York",year:"numeric",month:"2-digit",day:"2-digit"}).formatToParts(new Date(t));
  const get=type=>parts.find(p=>p.type===type)?.value||"";
  return get("year")+"-"+get("month")+"-"+get("day");
 };
 return rows.map(row=>{
  if(row.sport!=="NBA")return row;
  const found=report.players.filter(p=>String(p.player_id)===String(row.playerId)&&p.team===row.team&&p.game_date===eastern(row.start));
  return {...row,injury:found.length===1?{status:found[0].status,asOf:report.report_issued_at,source:"Official NBA report"}:null};
 });
}
/* Preserve every independently observed STANDARD pregame quote even if no model was frozen.
   A quote-only card is explicitly ungraded and NEVER claims a projection or AI side. */
function includeArchivedStandard(rows,archive){
 if(!Array.isArray(archive?.quotes))return rows;
 const valid=q=>q&&q.tier==="standard"&&q.more_tier==="standard"&&q.less_tier==="standard"&&
  q.is_demo===false&&["PTS","REB","AST","PRA"].includes(q.stat)&&n(q.line)!==null&&
  !!q.player&&!!q.team&&!!q.game&&Number.isFinite(stamp(q.observed_at))&&
  Number.isFinite(stamp(q.starts_at))&&stamp(q.observed_at)<stamp(q.starts_at);
 const k=p=>[norm(p.player),p.team,p.game,p.stat,n(p.line)].join("|");
 const known=new Set(rows.filter(x=>x.sport==="NBA").map(k));
 const missing=new Map();
 for(const q of archive.quotes.filter(valid)){
  const ident=k(q);
  if(known.has(ident))continue;
  const old=missing.get(ident);
  if(!old||stamp(q.observed_at)>stamp(old.observed_at))missing.set(ident,q);
 }
 const additions=[...missing.values()].map(q=>({
  sport:"NBA",playerId:"",player:q.player,team:q.team,opponent:q.game.split(" @ ")[0]||"",
  position:"",game:q.game,gameId:q.game,start:q.starts_at,stat:q.stat,source:"PrizePicks archived standard",
  line:n(q.line),projection:null,direction:null,chance:null,chanceSource:"No frozen model forecast was captured for this standard line",
  captured:q.observed_at,grade:"UNMODELED",actual:null,hit:null,gradeSource:null,
  form:{season:null,l5:null,l10:null,games:null},modelId:null,component:null,
  quoteOnly:true,quoteId:q.id
 }));
 return rows.concat(additions);
}
/* A game is independently visible even if the model failed to lock any props.
   Raw provider status is recorded, but old snapshots NEVER imply "live now". */
function liveGames(nbaFeed,nflFeed,now=Date.now()){
 const result=[];
 const observed=(value)=>Number.isFinite(stamp(value))?stamp(value):null;
 const fresh=(value)=>value!==null&&now-value>=-120000&&now-value<20*60000;
 if(Array.isArray(nbaFeed?.games)){
  for(const g of nbaFeed.games){
   if(!g?.game)continue;
   const at=observed(g.observed_at||nbaFeed.captured_at);
   const isCurrent=fresh(at)&&g.stale!==true;
   const state=g.state==="in"?"in":g.state==="post"?"final":g.state==="pre"?"scheduled":"unknown";
   const players=Array.isArray(g.player_rows)?g.player_rows:[];
   result.push({sport:"NBA",gameId:g.event_id||g.game,game:g.game,observedAt:g.observed_at||nbaFeed.captured_at,
    state:!isCurrent&&state==="in"?"stale":state,sourceState:state,fresh:isCurrent,
    statusText:isCurrent?(g.shortDetail||g.displayClock||state):(state==="final"?"Final · last snapshot":"Last observed · refresh pending"),
    players:players.map(p=>({player:p.player,team:p.team,stats:{PTS:n(p.PTS),REB:n(p.REB),AST:n(p.AST),PRA:n(p.PRA)}})),
    away:g.game.split(" @ ")[0]||"",home:g.game.split(" @ ")[1]||""});
  }
 }
 if(Array.isArray(nflFeed?.games)){
  for(const g of nflFeed.games){
   if(!g?.game_id)continue;
   const at=observed(g.observed_at||nflFeed.checked_at);
   const isCurrent=fresh(at);
   const state=g.status==="in"?"in":g.status==="post"||g.status==="final"?"final":g.status==="pre"?"scheduled":"unknown";
   result.push({sport:"NFL",gameId:g.game_id,game:(g.away||"Away")+" @ "+(g.home||"Home"),
    observedAt:g.observed_at||nflFeed.checked_at,state:!isCurrent&&state==="in"?"stale":state,
    sourceState:state,fresh:isCurrent,
    statusText:isCurrent?(g.status_text||state):(state==="final"?"Final · last snapshot":"Last observed · refresh pending"),
    away:g.away||"",home:g.home||"",awayScore:n(g.away_score),homeScore:n(g.home_score),
    players:(Array.isArray(g.players)?g.players:[]).map(p=>({player:p.player,team:p.team,stats:p.stats||{}}))});
  }
 }
 return result;
}
/* Game catalog is schedule-first, then updated with genuine scoreboard observations.
   Schedule-only data is never promoted to a live score or fabricated final. */
function gameCatalog(nbaFeed,nflFeed,nbaSchedule,nflSchedule,now=Date.now(),nbaScoreFeed=null){
 const observed=liveGames(nbaFeed,nflFeed,now);
 const result=new Map();
 const identity=g=>g.sport+"|"+g.gameId;
 for(const g of observed)result.set(identity(g),g);
 const nbaDates=Array.isArray(nbaSchedule?.dates_eastern)?nbaSchedule.dates_eastern:[];
 if(Array.isArray(nbaSchedule?.games)){
  for(const g of nbaSchedule.games){
   if(!g?.id||!g.game||!Number.isFinite(stamp(g.start)))continue;
   if(nbaDates.length && !nbaDates.includes(g.date_eastern))continue;
   const id="NBA|"+g.id;
   const existing=result.get(id)||observed.find(x=>x.sport==="NBA"&&x.game===g.game);
   if(existing)continue;
   const start=stamp(g.start);
   result.set(id,{sport:"NBA",gameId:g.id,game:g.game,away:g.away||"",home:g.home||"",
    start:g.start,observedAt:null,state:start<=now?"unknown":"scheduled",
    sourceState:"schedule",fresh:false,source:"Independent NBA schedule",
    statusText:start<=now?"Started or finished · live status unavailable":"Scheduled · no live player data",
    players:[],awayScore:null,homeScore:null});
  }
 }
 // Scoreboard is independent from player-boxscore capture. Exact NBA game
 // identity plus source freshness is required before a verified score can
 // appear on live matchup cards. Never infer scores from schedules.
 if(nbaScoreFeed?.is_live_score_source===true &&
    Array.isArray(nbaScoreFeed.games)){
  const seenAt=stamp(nbaScoreFeed.generated_at);
  const current=Number.isFinite(seenAt) && now-seenAt>=-120000 &&
                now-seenAt<20*60000;
  if(current)for(const score of nbaScoreFeed.games){
   if(!score?.id||!score?.game||!["in","post"].includes(score.game_state))continue;
   const away=numberOrNull(score.away_score),home=numberOrNull(score.home_score);
   if(away===null||home===null)continue;
   const match=[...result.values()].find(g=>g.sport==="NBA"&&
       (g.gameId===score.id||g.game===score.game));
   if(!match||match.game!==score.game)continue;
   match.awayScore=away;match.homeScore=home;
   match.scoreObservedAt=nbaScoreFeed.generated_at;
   match.scoreFresh=true;
   match.statusText=score.game_state==="post"?"Final · verified scoreboard":
                     "Live · verified scoreboard";
   match.state=score.game_state==="post"?"final":"in";
   // Player freshness is independent. A good scoreboard must not make
   // stale/missing player totals appear current.
  }
 }
 if(Array.isArray(nflSchedule?.games)){
  for(const g of nflSchedule.games){
   if(!g?.game_id||!Number.isFinite(stamp(g.kickoff_utc)))continue;
   const start=stamp(g.kickoff_utc);
   // Only show practical recent and upcoming games; do not crowd Live with 272 fixtures.
   if(start<now-48*3600000||start>now+8*86400000)continue;
   const id="NFL|"+g.game_id;
   if(result.has(id))continue;
   const verifiedFinal=g.status==="final"&&
     numberOrNull(g.away_score)!==null&&numberOrNull(g.home_score)!==null;
   result.set(id,{sport:"NFL",gameId:g.game_id,game:(g.away||"Away")+" @ "+(g.home||"Home"),
    away:g.away||"",home:g.home||"",awayScore:verifiedFinal?numberOrNull(g.away_score):null,
    homeScore:verifiedFinal?numberOrNull(g.home_score):null,
    start:g.kickoff_utc,observedAt:null,players:[],sourceState:"schedule",fresh:false,
    state:verifiedFinal?"final":start>now?"scheduled":"unknown",
    statusText:verifiedFinal?"Final · schedule-verified score":
      start>now?"Scheduled · no live player data":"Started or finished · live status unavailable"});
  }
 }
 return [...result.values()];
}
function numberOrNull(v){return n(v)}
function gradingAuditSummary(payload,now=Date.now()){
 if(!payload||!payload.days||typeof payload.days!=="object")return null;
 const checked=stamp(payload.checked_at);
 if(!Number.isFinite(checked))return null;
 const parts=new Intl.DateTimeFormat("en-CA",{timeZone:"America/New_York",year:"numeric",month:"2-digit",day:"2-digit"}).formatToParts(new Date(now));
 const value=type=>parts.find(p=>p.type===type)?.value||"";
 const today=value("year")+"-"+value("month")+"-"+value("day");
 const previous=Object.keys(payload.days).filter(d=>/^\d{4}-\d{2}-\d{2}$/.test(d)&&d<today).sort().at(-1);
 if(!previous)return null;
 const d=payload.days[previous];
 for(const k of ["captured","graded","pending","void_dnp","excluded_nonparticipant","accounted_for"]){
  if(!Number.isSafeInteger(d?.[k])||d[k]<0)return null;
 }
 if(d.captured!==d.graded+d.pending+d.void_dnp+d.excluded_nonparticipant||
   d.accounted_for!==d.graded+d.void_dnp+d.excluded_nonparticipant)return null;
 return {day:previous,captured:d.captured,graded:d.graded,
  pending:d.pending,voided:d.void_dnp+d.excluded_nonparticipant,
  stale:now-checked>4*3600000||now-checked< -120000,checkedAt:payload.checked_at};
}
root.DamesPicksModel={nbaTeam:nbaTeamCode,csv,nba,nfl,summarize,key,primaryDisplayLines,preferredNBALiveFeed,attachLive,attachNFLGrades,reconcileNFLSettlementCards,attachInjuries,includeArchivedStandard,liveGames,gameCatalog,gradingAuditSummary};
})(typeof window!=="undefined"?window:globalThis);
