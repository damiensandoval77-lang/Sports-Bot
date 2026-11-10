/* Unified NBA / NFL read-only adapter. Every displayed number originates in a published bot artifact. */
(function(root){
"use strict";
const n=v=>v===null||v===undefined||v===""?null:Number.isFinite(Number(v))?Number(v):null;
const norm=v=>String(v||"").normalize("NFKD").toLowerCase().replace(/[\u0300-\u036f]/g,"").replace(/[^a-z0-9]/g,"");
const stamp=v=>{const d=Date.parse(v);return Number.isFinite(d)?d:NaN};
const key=p=>[p.sport,p.playerId||norm(p.player),p.gameId||p.game,p.start,p.stat].join("|");
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
   game:p.team+" vs "+p.opponent,gameId:p.game_id,start:game.kickoff_utc,stat:p.stat,
   source:"PrizePicks",line:n(p.line),projection:n(p.proj),direction,chance,
   chanceSource:"NFL model estimate; not a calibrated hit probability",
   captured:p.captured_at,grade:"PENDING",actual:null,hit:null,gradeSource:null,
   form:{season:n(p.season_avg),l5:null,l10:null,games:n(p.season_games)},
   logs:Array.isArray(logs)?logs.slice(0,6):[],modelId:p.projection_id||null,component:null
  };
  const k=key(obj);
  const old=found.get(k);
  if(!old||stamp(old.captured)<stamp(obj.captured))found.set(k,obj);
 }
 return [...found.values()];
}
function summarize(rows,nflHealth,now=Date.now()){
 const pre=rows.filter(r=>stamp(r.start)>now),gameCount=new Set(pre.map(r=>r.gameId)).size;
 // Only the NBA market ledger has individually verified directional grading here.
 const graded=rows.filter(r=>r.grade==="GRADED"&&typeof r.hit==="boolean");
 if(rows[0]?.sport==="NFL"){
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
root.DamesPicksModel={csv,nba,nfl,summarize,key};
})(typeof window!=="undefined"?window:globalThis);
