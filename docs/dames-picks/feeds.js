/* Unified NBA / NFL read-only adapter. Every displayed number originates in a published bot artifact. */
(function(root){
"use strict";
const n=v=>v===null||v===undefined||v===""?null:Number.isFinite(Number(v))?Number(v):null;
const norm=v=>String(v||"").normalize("NFKD").toLowerCase().replace(/[\u0300-\u036f]/g,"").replace(/[^a-z0-9]/g,"");
const stamp=v=>{const d=Date.parse(v);return Number.isFinite(d)?d:NaN};
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
  const prob=n(c.modeled_selected_probability),grade=p.grade==="GRADED"?"GRADED":"PENDING";
  return {
   sport:"NBA",playerId:p.player_id,player:p.player,team:p.team,opponent:p.opponent,
   position:"",game:p.game,gameId:p.game,start:p.start,stat:p.stat,source:"PrizePicks",
   line:n(p.line),projection:n(p.projection),direction:c.modeled_direction==="More"?"MORE":"LESS",
   chance:prob>=0&&prob<=1?prob:null,chanceSource:"20,000 historical-residual simulations; uncalibrated",
   captured:p.captured_at,grade,actual:grade==="GRADED"?n(p.actual):null,
   hit:grade==="GRADED"&&typeof p.direction_hit==="boolean"?p.direction_hit:null,
   gradeSource:grade==="GRADED"?p.final_source:null,
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

/* Merge observation feeds by exact game/player/team. No observations alter frozen projections. */
function attachLive(rows,nbaFeed,nflFeed,now=Date.now()){
 const nbaFresh=nbaFeed?.status&&Number.isFinite(stamp(nbaFeed.captured_at))&&
  Math.abs(now-stamp(nbaFeed.captured_at))<20*60000;
 const nflFresh=nflFeed?.status==="ok"&&Number.isFinite(stamp(nflFeed.checked_at))&&
  Math.abs(now-stamp(nflFeed.checked_at))<20*60000;
 const nbaGames=new Map((nbaFresh?nbaFeed.games:[]).filter(g=>g.state==="in").map(g=>[g.game,g]));
 const nflGames=new Map((nflFresh?nflFeed.games:[]).filter(g=>g.status==="in").map(g=>[g.game_id,g]));
 return rows.map(p=>{
  if(p.sport==="NBA"){
   const game=nbaGames.get(p.game);
   const hits=(game?.player_rows||[]).filter(x=>x.team===p.team&&norm(x.player)===norm(p.player));
   if(hits.length!==1)return {...p,live:null};
   const actual=n(hits[0][p.stat]);
   return {...p,live:actual===null?null:{actual,gameStatus:game.shortDetail||game.displayClock||"In progress",
    period:game.period,observedAt:game.observed_at||nbaFeed.captured_at,source:"ESPN player snapshot"}};
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
  if(x.grade_status!=="GRADED"||x.odds_type!=="standard"||n(x.actual)===null||
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
root.DamesPicksModel={csv,nba,nfl,summarize,key,attachLive,attachNFLGrades,attachInjuries};
})(typeof window!=="undefined"?window:globalThis);
