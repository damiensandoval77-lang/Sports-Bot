/* Dame's Picks: read-only adapters over existing Sports-Bot published artifacts.
   No fabricated probabilities, grades, or cross-line recalibration. */
(function(root){
"use strict";
const clean=s=>String(s||"").normalize("NFKD").toLowerCase().replace(/[\u0300-\u036f]/g,"").replace(/[^a-z0-9]/g,"");
const number=x=>x===""||x==null?null:Number.isFinite(Number(x))?Number(x):null;
function nbaRows(ledger,form){
 if(ledger?.status!=="FROZEN_NEW_AI_ALL_MARKET"||!Array.isArray(ledger.records))return [];
 const persons=new Map((form?.players||[]).map(p=>[clean(p.player)+"|"+p.team,p]));
 return ledger.records.filter(p=>{
  const c=p.estimated_hit_chance;
  return p.pickem_tier==="standard"&&p.standard_line_two_sided_verified===true&&
   p.research_only===true&&p.production_replaced===false&&
   number(p.line)!==null&&number(p.projection)!==null&&
   ["PTS","REB","AST","PRA"].includes(p.stat)&&
   Date.parse(p.market_updated)<=Date.parse(p.captured_at)&&Date.parse(p.captured_at)<Date.parse(p.start)&&
   c?.method==="JOINT_2024_25_VALIDATION_RESIDUALS_20K_UNCALIBRATED"&&c.draws===20000&&c.calibrated===false;
 }).map(p=>{
  const c=p.estimated_hit_chance,person=persons.get(clean(p.player)+"|"+p.team),m=person?.metrics?.[p.stat];
  const side=c.modeled_direction==="More"?"MORE":c.modeled_direction==="Less"?"LESS":null;
  const chance=number(c.modeled_selected_probability);
  return {id:["NBA",p.player_id,p.game,p.start,p.stat,p.line].join("|"),
   sport:"NBA",player:p.player,team:p.team,opponent:p.opponent||"",game:p.game,
   position:"",start:p.start,stat:p.stat,line:number(p.line),projection:number(p.projection),
   chance:chance!==null&&chance>=0&&chance<=1&&side?chance:null,side,
   draws:20000,source:"PrizePicks",snapshot:p.captured_at,
   status:p.grade==="GRADED"?"GRADED":"PENDING",actual:number(p.actual),
   hit:typeof p.direction_hit==="boolean"?p.direction_hit:null,
   seasonAverage:number(m?.season),last5Average:number(m?.l5),last10Average:number(m?.l10),
   seasonGames:person?.games||null,gradeSource:p.final_source||null,
   chanceLabel:"Uncalibrated historical-residual simulation",
   isHistorical:Date.parse(p.start)<=Date.now()};
 });
}
function parseCSV(text){
 const rows=[];let row=[],field="",quoted=false;
 for(let i=0;i<text.length;i++){
  const c=text[i];
  if(c==='"'){if(quoted&&text[i+1]==='"'){field+='"';i++}else quoted=!quoted}
  else if(c===","&&!quoted){row.push(field);field=""}
  else if((c==="\n"||c==="\r")&&!quoted){
   if(c==="\r"&&text[i+1]==="\n")i++;
   row.push(field);field="";if(row.some(v=>v!==""))rows.push(row);row=[];
  }else field+=c;
 }
 if(field||row.length){row.push(field);rows.push(row)}
 const keys=rows.shift()||[];
 return rows.map(r=>Object.fromEntries(keys.map((k,i)=>[k,r[i]??""])));
}
function nflRows(files,schedule){
 const games=new Map((schedule?.games||[]).map(g=>[g.game_id,g]));
 const out=[];
 for(const p of files.flat()){
  if(p.odds_type!=="standard"||number(p.line)===null||number(p.proj)===null)continue;
  const game=games.get(p.game_id),tip=game?.kickoff_utc;
  if(!tip||!(Date.parse(p.captured_at)<Date.parse(tip)))continue;
  const direction=p.pick==="More"?"MORE":p.pick==="Less"?"LESS":null;
  const prob=number(p.p_more);
  const chosen=prob===null?null:direction==="MORE"?prob:direction==="LESS"?1-prob:null;
  let logs=[];try{logs=JSON.parse(p.season_game_log||"[]")}catch(_){}
  out.push({id:["NFL",p.projection_id,p.game_id,p.player_id,p.stat,p.line].join("|"),
   sport:"NFL",player:p.player,team:p.team,opponent:p.opponent,game:p.game_id.replace(/^\d{4}_\d{2}_/,"").replace("_"," @ "),
   position:p.position,start:tip,stat:p.stat,line:number(p.line),projection:number(p.proj),
   chance:chosen!==null&&chosen>=0&&chosen<=1?chosen:null,side:direction,
   draws:null,source:"PrizePicks",snapshot:p.captured_at,status:"PENDING",actual:null,hit:null,
   seasonAverage:number(p.season_avg),last5Average:null,last10Average:null,
   seasonGames:number(p.season_games),lastGames:Array.isArray(logs)?logs.slice(0,6):[],
   chanceLabel:"Model estimate, calibration not verified",isHistorical:Date.parse(tip)<=Date.now()});
 }
 return out;
}
function summary(rows,now=Date.now()){
 const graded=rows.filter(r=>r.status==="GRADED"&&typeof r.hit==="boolean");
 const wins=graded.filter(r=>r.hit).length,losses=graded.length-wins;
 const upcoming=rows.filter(r=>Date.parse(r.start)>now);
 return {wins,losses,hitRate:graded.length?wins/graded.length:null,
  games:new Set(upcoming.map(r=>r.game+"|"+r.start)).size,
  graded:graded.length,pending:rows.filter(r=>r.status==="PENDING").length};
}
root.DamesAdapter={nbaRows,nflRows,parseCSV,summary};
})(typeof window!=="undefined"?window:globalThis);
