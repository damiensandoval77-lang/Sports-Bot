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
/* Rank the same probability shown on pick cards, never an unrelated legacy
   field. Missing estimates remain last; ties are stable by start then identity. */
function displayedHitRate(p){
 const candidate=hitEstimate(p)?.rate??p?.matchupPreview?.rate;
 return typeof candidate==="number"&&Number.isFinite(candidate)&&candidate>=0&&candidate<=1?candidate:null;
}
function sortByHitEstimate(rows){
 return [...(rows||[])].sort((a,b)=>{
  const ar=displayedHitRate(a),br=displayedHitRate(b);
  if(ar===null&&br!==null)return 1;
  if(br===null&&ar!==null)return -1;
  if(ar!==br)return br-ar;
  const at=stamp(a.start),bt=stamp(b.start);
  return (Number.isFinite(at)?at:Infinity)-(Number.isFinite(bt)?bt:Infinity)||key(a).localeCompare(key(b));
 });
}
/* Card display only: one current captured standard line per player/stat/
   scheduled game. Never rewrite the immutable frozen-price/grade ledger.
   A real pretip model outranks an unmodeled quote-only research receipt;
   among equivalent records, the latest verified pretip capture wins. */
function displayCurrentPicks(rows,now=Date.now(),currentSlateOnly=false){
 const et=ms=>{
  if(!Number.isFinite(ms))return null;
  const parts=new Intl.DateTimeFormat("en-US",{timeZone:"America/New_York",
   year:"numeric",month:"2-digit",day:"2-digit",hour:"2-digit",hourCycle:"h23"}).formatToParts(new Date(ms));
  const get=k=>parts.find(p=>p.type===k)?.value||"";
  return {date:get("year")+"-"+get("month")+"-"+get("day"),hour:Number(get("hour"))};
 };
 const today=et(now),yesterday=et(now-24*3600000);
 const validStart=p=>p&&["NBA","NFL"].includes(p.sport)&&
   Number.isFinite(stamp(p.start))&&Number.isFinite(stamp(p.captured))&&
   stamp(p.captured)<stamp(p.start);
 const source=(rows||[]).filter(validStart);
 const dates=[...new Set(source.map(p=>et(stamp(p.start)).date))].sort();
 // On a league off-day the tracker shows the last slate with saved lines,
 // never a mixture of that slate and the next one.
 const selectedDate=dates.includes(today.date)?today.date:
   dates.filter(d=>d<today.date).at(-1)||dates.find(d=>d>today.date)||null;
 const latest=new Map();
 for(const p of source){
  if(!p||!["NBA","NFL"].includes(p.sport))continue;
  const start=stamp(p.start),captured=stamp(p.captured);
  if(!Number.isFinite(start)||!Number.isFinite(captured)||captured>=start)continue;
  if(currentSlateOnly){
   const when=et(start);
   const recentLateGame=today.hour<6&&when.date===yesterday.date&&
      start>=now-10*3600000&&start<=now;
   if(when.date!==selectedDate&&!recentLateGame)continue;
  }
  const match=[p.sport,p.gameId||p.game,start,norm(p.player)||p.playerId,
               nbaTeamCode(p.team),p.stat].join("|");
  const prior=latest.get(match);
  if(!prior){latest.set(match,p);continue;}
  const modeled=p.quoteOnly!==true&&Number.isFinite(n(p.projection));
  const priorModeled=prior.quoteOnly!==true&&Number.isFinite(n(prior.projection));
  if(modeled!==priorModeled){if(modeled)latest.set(match,p);continue;}
  const priorAt=stamp(prior.captured);
  if(captured>priorAt||(captured===priorAt&&Number(p.line)<Number(prior.line)))
   latest.set(match,p);
 }
 return [...latest.values()];
}
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
   chance:!p.injury_uncertainty_unresolved&&!p.opponent_context_unavailable&&!p.single_source_history&&prob>=0&&prob<=1?prob:null,
   chanceSource:p.single_source_history?"Full box-score stats from one public source, not independently confirmed; hit confidence withheld":p.opponent_context_unavailable?"Baseline projection only; opponent defensive sample unavailable; hit confidence withheld":p.injury_uncertainty_unresolved?"Baseline projection only; injury impact unresolved; hit confidence withheld":"Frozen new-AI model vs original standard line; residual uncertainty; uncalibrated",
   injuryUncertainty:p.injury_uncertainty_unresolved===true,
   opponentContextUnavailable:p.opponent_context_unavailable===true,
   singleSourceHistory:p.single_source_history===true,
   chanceMethod:c.method,chanceDraws:c.draws,chanceCalibrated:c.calibrated,
   opponentAwareVerified:false,
   matchupEstimate:p.matchup_hit_estimate||null,
   captured:p.captured_at,grade,actual:grade==="GRADED"?n(p.actual):null,
   hit:grade==="GRADED"&&typeof p.direction_hit==="boolean"?p.direction_hit:null,
   gradeSource:grade!=="PENDING"?p.final_source:null,
   form:{season:n(metrics?.season),l5:n(metrics?.l5),l10:n(metrics?.l10),games:person?.games||null},
   modelId:"FROZEN_NEW_AI_ALL_MARKET",component:p.components||null
  };
 });
}
/* Fresh NFL evidence is exported with its original pregame probability. Old
   rows without evidence remain unavailable; never infer it from hit history. */
function nflMatchupPreview(p,start){
 let x;try{x=JSON.parse(p.matchup_evidence||"null")}catch(_){return null}
 if(!x||x.schema!=="NFL_OPPONENT_FEATURES_V1"||
    !["NFL_MATCHUP_RESIDUAL_V1","NFL_MATCHUP_POISSON_V1"].includes(x.method)||
    x.calibrated!==false||x.research_only!==true||
    !/^[a-f0-9]{64}$/.test(x.artifact_sha256||""))return null;
 const direction=p.pick==="More"?"MORE":p.pick==="Less"?"LESS":null;
 for(const k of ["player_id","game_id","team","opponent","target"])
  if(!p[k]||x[k]!==p[k])return null;
 const captured=stamp(p.captured_at),observed=stamp(x.observed_at),tip=stamp(start);
 if(!Number.isFinite(captured)||!Number.isFinite(observed)||!Number.isFinite(tip)||
    observed>captured||captured>=tip||stamp(x.captured_at)!==captured||
    x.direction!==direction||n(x.original_line)!==n(p.line))return null;
 const more=n(x.modeled_more_probability),selected=n(x.selected_probability),original=n(p.p_more);
 if(more===null||selected===null||more<0||more>1||selected<0||selected>1||
    original===null||Math.abs(more-original)>1e-8||
    Math.abs(selected-(direction==="MORE"?more:1-more))>1e-8)return null;
 const features=x.opponent_features,used=x.model_feature_names;
 if(!features||typeof features!=="object"||Array.isArray(features)||!Array.isArray(used)||
    !Object.keys(features).length||Object.entries(features).some(([k,v])=>
      !/^OPP_ALLOW_(REC_YDS|RUSH_YDS|REC|FPTS)_L6$/.test(k)||!used.includes(k)||n(v)===null||n(v)<0))return null;
 return {rate:selected,asOf:p.captured_at,method:x.method,calibrated:false,
  sport:"NFL",opponentAwareVerified:true,source:"Frozen NFL opponent-position ensemble research estimate"};
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
   chanceMethod:"NFL_FROZEN_MODEL",chanceCalibrated:false,
   matchupPreview:nflMatchupPreview(p,game.kickoff_utc),
   opponentAwareVerified:false,
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
function summarize(rows,nflHealth,now=Date.now(),league=null){
 const pre=rows.filter(r=>stamp(r.start)>now),gameCount=new Set(pre.map(r=>r.gameId)).size;
 // Only the NBA market ledger has individually verified directional grading here.
 const graded=rows.filter(r=>r.grade==="GRADED"&&typeof r.hit==="boolean");
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
  pending:rows.filter(x=>x.grade==="PENDING").length};
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
// A descriptive game-clock extrapolation, separate from the frozen AI forecast.
function livePace(actual,sport,period,clock){
 const length=sport==="NBA"?12:sport==="NFL"?15:null;
 if(!length||!Number.isInteger(period)||period<1||period>4||typeof actual!=="number"||!Number.isFinite(actual)||actual<0)return null;
 let seconds=null;
 if(typeof clock==="number"&&Number.isFinite(clock))seconds=clock;
 else if(typeof clock==="string"){
  const ordinary=/^(\d{1,2}):(\d{2})(?:\.\d+)?$/.exec(clock);
  const iso=/^PT(\d+)M([0-9.]+)S$/.exec(clock);
  if(ordinary&&Number(ordinary[2])<60)seconds=Number(ordinary[1])*60+Number(ordinary[2]);
  else if(iso&&Number(iso[2])<60)seconds=Number(iso[1])*60+Number(iso[2]);
 }
 if(seconds===null||seconds<0||seconds>length*60)return null;
 const elapsed=period*length-seconds/60;
 if(elapsed<5||elapsed>=4*length)return null;
 return {value:actual*(4*length)/elapsed,elapsedMinutes:elapsed,regulationMinutes:4*length};
}
function sortByTeamPosition(rows){
 const order={PG:0,G:0,SG:1,SF:2,F:2,PF:3,C:4,QB:0,RB:1,FB:1,WR:2,TE:3,K:4};
 return [...(rows||[])].sort((a,b)=>nbaTeamCode(a.team).localeCompare(nbaTeamCode(b.team))||
  (order[a.position]??99)-(order[b.position]??99)||String(a.player||"").localeCompare(String(b.player||""))||String(a.stat||"").localeCompare(String(b.stat||"")));
}
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
   return {...p,position:hits[0].position||p.position,live:actual===null?null:{actual,pace:livePace(actual,"NBA",game.period,game.clock??game.displayClock),gameStatus:game.shortDetail||game.displayClock||"In progress",
    period:game.period,observedAt:game.observed_at||nbaFeed.captured_at,source:game.source_label||"ESPN player snapshot"}};
  }
  const game=nflGames.get(p.gameId);
  const hits=(game?.players||[]).filter(x=>x.team===p.team&&norm(x.player)===norm(p.player));
  if(hits.length!==1||!p.target)return {...p,live:null};
  const actual=n(hits[0].stats?.[p.target]);
  return {...p,live:actual===null?null:{actual,pace:livePace(actual,"NFL",game.period,game.clock),gameStatus:game.status_text||"In progress",
   period:game.period,observedAt:nflFeed.checked_at,source:"ESPN player snapshot"}};
 });
}
/* Observed NBA game logs strictly before the pick's Eastern game date.
   Per-market line-specific over/under/push, no inferred or fabricated values. */
function etDay(v){
 const d=new Date(v);if(isNaN(d))return null;
 const parts=new Intl.DateTimeFormat("en-CA",{timeZone:"America/New_York",year:"numeric",month:"2-digit",day:"2-digit"}).formatToParts(d);
 const g=k=>parts.find(x=>x.type===k).value;
 return g("year")+"-"+g("month")+"-"+g("day");
}
function attachGameLogs(rows,form,limit=10){
 const fields=Array.isArray(form?.log_fields)?form.log_fields:null;
 if(!fields||!Array.isArray(form?.players))return rows;
 const at=k=>fields.indexOf(k),di=at("date"),oi=at("opponent");
 if(di<0||oi<0)return rows;
 const byId=new Map(),byName=new Map();
 for(const person of form.players){
  if(!Array.isArray(person?.log))continue;
  if(person.player_id)byId.set(String(person.player_id),person);
  const k=norm(person.player)+"|"+nbaTeamCode(person.team);
  byName.set(k,byName.has(k)?null:person);
 }
 return rows.map(p=>{
  if(p.sport!=="NBA"||n(p.line)===null||at(p.stat)<0)return p;
  const byIdentifier=byId.get(String(p.playerId||""));
  const person=byIdentifier&&nbaTeamCode(byIdentifier.team)===nbaTeamCode(p.team)?
    byIdentifier:byName.get(norm(p.player)+"|"+nbaTeamCode(p.team));
  const day=etDay(p.start);
  if(!person||!day)return p;
  const games=person.log.filter(r=>Array.isArray(r)&&String(r[di])<day&&n(r[at(p.stat)])!==null)
   .map(r=>({date:String(r[di]),opponent:String(r[oi]),actual:n(r[at(p.stat)])}))
   .sort((a,b)=>a.date.localeCompare(b.date));
  if(!games.length)return p;
  const cmp=g=>g.actual>p.line?"over":g.actual<p.line?"under":"push";
  const count=list=>list.reduce((c,g)=>(c[cmp(g)]++,c),{over:0,under:0,push:0});
  const all=count(games),last5=count(games.slice(-5));
  const shown=games.slice(-Math.max(1,limit));
  return {...p,
   logs:shown.slice().reverse().map(g=>({actual:g.actual,label:g.opponent,date:g.date,result:cmp(g)})),
   form:{...(p.form||{}),over:all.over,under:all.under,push:all.push,
    last5Over:last5.over,last5Under:last5.under,historyGames:games.length,
    historySource:"Observed completed games before this pick's game date"}};
 });
}
root.DamesPicksLineHistory={attachGameLogs,etDay};
/* Hit Estimate is MODEL-ESTIMATED probability of the chosen direction
   beating the ORIGINAL verified standard sportsbook line, not the
   player's raw hit frequency in previous games. Historical line-over rates
   remain separate validation and calibration evidence. Until prospective
   calibration succeeds this is uncalibrated, NOT verified win probability.
   Never reconstruct a missing frozen probability after tipoff. */
/* A HIT EST is a pregame opponent-conditioned model output, not an observed
   line hit frequency or generic residual distribution. Missing evidence => —.
   The browser verifies provenance shape; backtesting/calibration remain separate. */
const MATCHUP_INPUTS=["opponent_position_defense","projected_minutes",
 "usage_opportunities","teammate_availability","depth_role","pace_possessions"];
function hitEstimate(p){
 if(!p||p.quoteOnly||!["MORE","LESS"].includes(p.direction)||
   n(p.line)===null||n(p.projection)===null)return null;
 const x=p.matchupEstimate;
 if(!x||x.method!=="PREGAME_MATCHUP_CONDITIONED_V1"||
    x.research_only!==false||x.opponent_aware_verified!==true||
    typeof x.model_id!=="string"||!x.model_id||
    !x.factors||typeof x.factors!=="object")return null;
 const prob=n(x.modeled_selected_probability);
 if(prob===null||prob<0||prob>1||
    n(x.original_line)!==n(p.line)||
    x.direction!==p.direction)return null;
 const captured=Date.parse(p.captured),tip=Date.parse(p.start),
       modelCaptured=Date.parse(x.captured_at);
 if(!Number.isFinite(captured)||!Number.isFinite(tip)||
    !Number.isFinite(modelCaptured)||captured>=tip||
    modelCaptured!==captured)return null;
 for(const name of MATCHUP_INPUTS){
  const a=x.factors[name],observed=Date.parse(a?.observed_at);
  if(!a||typeof a.source!=="string"||!a.source.trim()||
     !Number.isFinite(observed)||observed>captured||
     n(a.baseline)===null||n(a.baseline)<=0||
     n(a.matchup)===null||n(a.matchup)<=0)return null;
 }
 return {rate:prob,source:"Verified pregame opponent-conditioned model estimate",
  calibrated:x.calibrated===true,method:x.method,
  opponentAwareVerified:true,historicalRateNotUsed:true};
}
/* Separately captured research estimates are NOT certified HIT EST and NEVER
   replace original pretip lines, directions, projections, grades or odds. */
function attachMatchupPreview(rows,feed,now=Date.now()){
 if(feed?.status!=="POSITION_MATCHUP_RESEARCH_ONLY_PROBABILITY"||
    feed?.production_approved!==false||feed?.calibrated!==false||
    feed?.presentation_policy!=="EXPERIMENTAL_MATCHUP_PREVIEW_NOT_CERTIFIED_HIT_EST"||
    !Array.isArray(feed.records)||!Number.isFinite(stamp(feed.captured_at))||
    stamp(feed.captured_at)>now+120000)return rows;
 const grouped=new Map(),duplicates=new Set();
 const identity=x=>[String(x.player_id),x.team,x.opponent,x.stat,
                         x.start,String(x.line),x.original_side].join("|");
 for(const item of feed.records){
  if(!item||!item.player_id||!item.team||!item.opponent||
     !["PTS","REB","AST","PRA"].includes(item.stat)||
     !["MORE","LESS"].includes(item.original_side))continue;
  const chance=item.estimated_hit_chance,rate=n(chance?.modeled_selected_probability);
  const captured=stamp(item.captured_at),kickoff=stamp(item.start);
  if(chance?.method!=="POSITION_V_POSITION_DEF_RATING_RESEARCH_ANALYTIC_V1"||
     chance.calibrated!==false||chance.research_only!==true||
     chance.verified_betting_edge!==false||
     chance.opponent_aware_inputs_sourced!==true||
     chance.opponent_adjustment_validated!==false||
     !Number.isFinite(captured)||!Number.isFinite(kickoff)||
     captured>=kickoff||captured>now+120000||
     rate===null||rate<0||rate>1||
     n(item.matchup_projection)===null||n(item.original_projection)===null||
     n(item.line)===null)continue;
  const provenance=chance.source_provenance||{};
  if(!["position_observed_at","player_observed_at","rating_observed_at",
        "minutes_snapshot_at"].every(k=>Number.isFinite(stamp(provenance[k]))&&
                                             stamp(provenance[k])<=captured))continue;
  const k=identity(item),old=grouped.get(k);
  if(old&&stamp(old.captured_at)===captured){duplicates.add(k);continue}
  if(!old||stamp(old.captured_at)<captured)grouped.set(k,item);
 }
 for(const k of duplicates)grouped.delete(k);
 return rows.map(p=>{
  if(p.sport!=="NBA"||p.quoteOnly||!["MORE","LESS"].includes(p.direction)||
     !Number.isFinite(stamp(p.captured))||stamp(p.captured)>=stamp(p.start))return p;
  const item=grouped.get([String(p.playerId),p.team,p.opponent,p.stat,
           p.start,String(p.line),p.direction].join("|"));
  if(!item||stamp(item.captured_at)<stamp(p.captured))return p;
  return {...p,position:p.position||item.listed_position||"",
   matchupPreview:{rate:n(item.estimated_hit_chance.modeled_selected_probability),
      projection:n(item.matchup_projection),asOf:item.captured_at,
      method:item.estimated_hit_chance.method,calibrated:false,
      originalPickCaptured:p.captured,
      researchOnly:true}};
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
 const k=p=>[norm(p.player),p.team,p.game,p.stat,n(p.line),stamp(p.start||p.starts_at)].join("|");
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
    players:players.map(p=>({player:p.player,team:nbaTeamCode(p.team),position:p.position||"",stats:{PTS:n(p.PTS),REB:n(p.REB),AST:n(p.AST),PRA:n(p.PRA)}})),
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
    players:(Array.isArray(g.players)?g.players:[]).map(p=>({player:p.player,team:p.team,position:p.position||"",stats:p.stats||{}}))});
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
   if(existing){existing.start=g.start;continue;}
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
// Live NBA view is one Eastern slate. Keep the full catalog for schedule coverage.
function currentSlateGames(games,league,now=Date.now()){
 const selected=(games||[]).filter(g=>g.sport===league);
 if(league!=="NBA")return selected;
 const day=value=>{
  const ms=stamp(value);if(!Number.isFinite(ms))return null;
  const parts=new Intl.DateTimeFormat("en-US",{timeZone:"America/New_York",year:"numeric",month:"2-digit",day:"2-digit"}).formatToParts(new Date(ms));
  return ["year","month","day"].map(k=>parts.find(p=>p.type===k)?.value).join("-");
 };
 const today=day(new Date(now).toISOString());
 const dates=[...new Set(selected.map(g=>day(g.start)).filter(Boolean))].sort();
 const chosen=dates.includes(today)?today:dates.filter(d=>d<today).at(-1)||dates[0];
 return selected.filter(g=>day(g.start)===chosen||(!day(g.start)&&g.sourceState!=="schedule")||
  (g.state==="in"&&g.fresh));
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
root.DamesPicksModel={nflMatchupPreview,nbaTeam:nbaTeamCode,hitEstimate,displayedHitRate,sortByHitEstimate,attachMatchupPreview,displayCurrentPicks,csv,nba,nfl,summarize,key,preferredNBALiveFeed,attachLive,attachNFLGrades,reconcileNFLSettlementCards,attachInjuries,includeArchivedStandard,livePace,sortByTeamPosition,liveGames,gameCatalog,currentSlateGames,gradingAuditSummary};
})(typeof window!=="undefined"?window:globalThis);

/* Runtime execution identity: fail closed if any cached asset predates this release. */
globalThis.__damesRunningAssets=globalThis.__damesRunningAssets||Object.create(null);
/* Published-schedule coverage: never fabricate missing predictions. */
(function(root){
"use strict";
const parse=s=>{let x=Date.parse(s);return Number.isFinite(x)?x:NaN};
function tonight(schedule,rows,now=Date.now()){
 const games=(schedule?.games||[]).filter(g=>{
  const start=parse(g.start);
  return Number.isFinite(start)&&g.game&&g.game_state!=="post"&&g.game_state!=="final"&&start-now<=12*3600000&&now-start<=4*3600000;
 });
 const saved=new Set((rows||[]).filter(r=>r.sport==="NBA"&&r.quoteOnly!==true&&r.projection!==null&&r.projection!==undefined&&["MORE","LESS"].includes(r.direction)).map(r=>r.game+"|"+Math.round(parse(r.start)/60000)));
 const missing=games.filter(g=>!saved.has(g.game+"|"+Math.round(parse(g.start)/60000)));
 const first=missing.map(g=>parse(g.start)).sort((a,b)=>a-b)[0];
 return {games:games.length,missing:missing.map(g=>g.game),covered:games.length-missing.length,
         firstTip:Number.isFinite(first)?new Date(first).toISOString():null,
         alert:missing.length>0&&Number.isFinite(first)&&first-now<=3*3600000};
}
function message(c,formatTime){
 if(!c.alert)return "";
 return "No saved picks yet for "+c.missing.length+" of "+c.games+" upcoming games (first tip "+formatTime(c.firstTip)+"). Picks may be processing or withheld for injuries; this page updates automatically.";
}
root.DamesPicksCoverage={tonight,message};
})(typeof window!=="undefined"?window:globalThis);
globalThis.__damesRunningAssets["feeds.js"]="dp-hit-estimate-sort-20261113-r25";
