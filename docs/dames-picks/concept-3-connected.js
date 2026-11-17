(function conceptRuntime(){
"use strict";
const $=id=>document.getElementById(id);
const one=s=>document.querySelector(s);
const all=s=>[...document.querySelectorAll(s)];
const n=v=>(v===null||v===undefined||v===""||!Number.isFinite(Number(v)))?null:Number(v);
const fmt=v=>n(v)===null?"—":Number(v).toFixed(1);
const text=(e,s)=>{if(e)e.textContent=String(s??"—")};
const norm=s=>String(s||"").normalize("NFKD").toLowerCase().replace(/[\u0300-\u036f]/g,"").replace(/[^a-z0-9]/g,"");
const etDay=ms=>new Intl.DateTimeFormat("en-CA",{timeZone:"America/New_York",year:"numeric",month:"2-digit",day:"2-digit"}).format(new Date(ms));
const validDate=v=>Number.isFinite(Date.parse(v))?Date.parse(v):NaN;
const supported={PTS:["points",2],REB:["rebounds",3],AST:["assists",4],PRA:["pra",5]};
const state={league:"NBA",stat:"PTS",form:null,schedule:null,scores:null,picks:[],nflPicks:[],nflSchedule:null,selected:null,nflSelected:null,load:"loading",notice:"",playerPhoto:null};
const stats=["PTS","REB","AST","PRA"];
let renderNum=0,photoRequest=0,teamsCache=new Map();
const status=document.createElement("div");
status.className="connected-banner";status.setAttribute("role","status");status.setAttribute("aria-live","polite");
one(".topbar").after(status);
const el=document.createElement("div");el.id="player-options";el.style.cssText="display:none";document.body.append(el);
const list=document.createElement("datalist");list.id="concept3-players";el.append(list);
$("search").setAttribute("list","concept3-players");
const clear=(sel,label="Not available in verified feed")=>{const node=one(sel);if(node)node.replaceChildren(Object.assign(document.createElement("p"),{className:"dataempty",textContent:label}))};
function resetPreview(){
 all(".slate .game").forEach(e=>e.remove());text(one(".slate-label .muted"),"Connecting current schedule");
 text(one(".hero h1"),"Connecting player data");
 text(one(".hero .player-name small"),"Awaiting verified team");
 text(one(".hero .subline"),"Live-feed integration · loading");
 all(".player-stats b").forEach(e=>text(e));
 const im=one(".portrait img");im.removeAttribute("src");im.hidden=true;
 const fb=document.createElement("div");fb.className="portrait-fallback";fb.textContent="DP";one(".portrait").append(fb);
 text(one(".next-match"),"Matchup unavailable");text(one(".hero-tile .tilebottom"),"Current schedule only");
 text(one(".focus-line"),"No verified standard line");
 all(".focus-stats b").forEach(e=>text(e));
 text($("games-avg"));text($("games-title"),"Completed game results");
 $("bars").replaceChildren();$("barlabels").replaceChildren();$("trend-svg").replaceChildren();
 text($("trend-title"),"Observed game trend");text(one("#trends .charttitle b"));
 one(".greenring").style.background="#3a3346";text(one(".ringcenter b"));text(one(".bulletnotes"),"No certified matchup estimate selected");
 $("histogram").replaceChildren(Object.assign(document.createElement("p"),{className:"dataempty",textContent:"No model distribution published"}));
 text(one(".binlabels"),"");
 setTable("#teammates tbody",3,"Teammate on/off statistics have not been verified");
 setTable("#splits tbody",4,"Waiting for completed-game statistics");
 setTable("#matchup tbody",4,"Opponent defensive-position statistics unavailable");
 text(one("#matchup .charttitle"),"Opponent defensive context pending");
 text(one(".contextlist"),"Waiting for verified player and game data");
 text($("prop-line"),"No standard line");text($("model-proj"));text($("model-edge"));
 all(".metricboxes .metricbox b").slice(2).forEach(e=>text(e));
 setTable("#grading tbody",6,"No independently verified graded props found");
 text(one(".grading-head small"),"Frozen standard-line results only");
 text(one("#ai .previewtag"),"VERIFIED DATA MODE");
 text(one(".aiquestion"),"What do the verified stats show?");
 text($("aianswer"),"Loading records. Dame's AI will not invent a projection or result.");
 text(one(".footnote"),"The prior mockup contained illustrative numbers. This page clears them before loading actual source records; unsupported modules show unavailable.");
 document.body.classList.add("is-connected");
}
function setTable(selector,span,message){
 const tb=one(selector);if(!tb)return;const tr=document.createElement("tr"),td=document.createElement("td");td.colSpan=span;td.className="unavailable-cell";td.textContent=message;tr.append(td);tb.replaceChildren(tr);
}
function rowTable(selector,rows){const tb=one(selector);if(!tb)return;tb.replaceChildren(...rows.map(cells=>{const tr=document.createElement("tr");for(const v of cells){const td=document.createElement("td");td.textContent=String(v??"—");tr.append(td)}return tr}))}
function changeNotice(s){
 state.notice=s;status.textContent=s;window.DamesConcept3Status={league:state.league,loaded:state.load,status:s,player:state.selected?.player||state.nflSelected?.player||null,modelCount:state.picks.length,photoSource:state.playerPhoto?.source||null};
}
async function get(path,kind="json",timeout=14000){
 const ctl=new AbortController(),timer=setTimeout(()=>ctl.abort(),timeout);
 try{
  const response=await fetch(new URL("../"+path,location.href),{cache:"no-store",signal:ctl.signal});
  if(!response.ok)throw Error(path+" HTTP "+response.status);
  return kind==="text"?await response.text():await response.json();
 }finally{clearTimeout(timer)}
}
async function remote(url,timeout=8000){
 const ctl=new AbortController(),timer=setTimeout(()=>ctl.abort(),timeout);
 try{const r=await fetch(url,{signal:ctl.signal});if(!r.ok)throw Error("Roster "+r.status);return await r.json()}
 finally{clearTimeout(timer)}
}
function gameRows(){
 const ss=state.league==="NBA"?state.schedule:state.nflSchedule;
 if(state.league==="NFL")return (ss?.games||[]).filter(g=>Number.isFinite(validDate(g.kickoff_utc))).map(g=>{
  const live=(state.nflLive?.games||[]).find(x=>x.game_id===g.game_id&&Date.now()-validDate(x.observed_at||state.nflLive.checked_at)<20*60000&&validDate(x.observed_at||state.nflLive.checked_at)<=Date.now()+120000);
  return {start:g.kickoff_utc,away:g.away||g.away_team||g.away_abbreviation||"",home:g.home||g.home_team||g.home_abbreviation||"",away_code:g.away||g.away_team||g.away_abbreviation||"",home_code:g.home||g.home_team||g.home_abbreviation||"",id:g.game_id,state:live?.status==="in"?"live":live?.status==="post"?"final":"scheduled",awayScore:live&&n(live.away_score)!==null?n(live.away_score):null,homeScore:live&&n(live.home_score)!==null?n(live.home_score):null};
 });
 return (ss?.games||[]).filter(g=>Number.isFinite(validDate(g.start))).map(g=>{
  const score=state.scores?.is_live_score_source===true&&validDate(state.scores.generated_at)>Date.now()-1200000&&
   (state.scores.games||[]).find(s=>s.id===g.id&&s.game===g.game);
  return {start:g.start,away:g.away_abbreviation||g.away||"",home:g.home_abbreviation||g.home||"",
   away_code:g.away_abbreviation||"",home_code:g.home_abbreviation||"",
   id:g.id,state:score?.game_state==="in"?"live":score?.game_state==="post"?"final":"scheduled",
   awayScore:n(score?.away_score),homeScore:n(score?.home_score)};
 });
}
function renderGames(){
 const slate=$("sports");all(".slate .game").forEach(e=>e.remove());
 const games=gameRows().sort((a,b)=>validDate(a.start)-validDate(b.start));
 const today=etDay(Date.now());const date=games.some(g=>etDay(validDate(g.start))===today)?today:(games.find(g=>validDate(g.start)>Date.now()-3600000)?.start||games[0]?.start);
 const day=typeof date==="string"&&date.includes("T")?etDay(validDate(date)):date;
 const shown=games.filter(g=>day&&etDay(validDate(g.start))===day).slice(0,5);
 text(one(".slate-label .muted"),(state.league==="NBA"?"NBA":"NFL")+" · "+(day||"No scheduled slate")+(state.scores?.is_live_score_source===true?" · Score source available":" · Schedule only"));
 for(const g of shown){
  const box=document.createElement("div");box.className="game";
  const label=document.createElement("div");label.className="status";
  const tip=validDate(g.start);
  label.textContent=g.state==="live"?"LIVE · verified":g.state==="final"?"Final · verified":new Date(tip).toLocaleTimeString("en-US",{timeZone:"America/New_York",hour:"numeric",minute:"2-digit"})+" ET";
  box.append(label);
  for(const [t,score] of [[g.away_code||g.away,g.awayScore],[g.home_code||g.home,g.homeScore]]){
   const side=document.createElement("div");side.className="team";
   const team=document.createElement("span");team.className="teamtxt";
   const emblem=document.createElement("span");emblem.className="emblem";emblem.textContent="●";
   team.append(emblem,document.createTextNode(String(t||"—")));
   const pts=document.createElement("span");pts.textContent=score===null||score===undefined?"—":String(score);side.append(team,pts);box.append(side);
  }
  slate.insertBefore(box,$("games-btn"));
 }
 if(!shown.length){
  const msg=document.createElement("p");msg.className="dataempty";msg.textContent="No games in the currently published schedule";slate.insertBefore(msg,$("games-btn"))
 }
 text($("games-btn"),"All "+state.league+" Games");
}
function picksOfSelected(){
 const item=state.league==="NBA"?state.selected:state.nflSelected;
 if(!item)return [];
 const rows=state.league==="NBA"?state.picks:state.nflPicks;
 return rows.filter(p=>norm(p.player)===norm(item.player)&&String(p.team||"").toUpperCase()===String(item.team||"").toUpperCase());
}
function chosenPick(){
 const rows=picksOfSelected().filter(p=>p.stat===state.stat&&n(p.line)!==null);
 return rows.sort((a,b)=>{
  const fa=validDate(a.start)>=Date.now(),fb=validDate(b.start)>=Date.now();
  if(fa!==fb)return fa?-1:1;
  const x=validDate(a.start),y=validDate(b.start);
  return fa?x-y:y-x;
 })[0]||null;
}
function renderPlayer(){
 const item=state.league==="NBA"?state.selected:state.nflSelected;
 if(!item){text(one(".hero h1"),"No player selected");return}
 const games=gameRows(),team=String(item.team||"").toUpperCase();
 const next=games.filter(g=>(g.home_code===team||g.away_code===team)&&validDate(g.start)>Date.now()-3*3600000).sort((a,b)=>validDate(a.start)-validDate(b.start))[0]||null;
 text(one(".hero h1"),item.player+" ☆");
 text(one(".hero .player-name small"),(state.league==="NBA"?"NBA":"NFL")+" · "+team+(item.position?" · "+item.position:""));
 text(one(".hero .subline"),"Published "+(state.league==="NBA"?"player logs":"frozen NFL records")+" · "+(state.form?.updated_at?new Date(state.form.updated_at).toLocaleDateString():"source time unavailable"));
 const form=item.metrics||{};
 all(".player-stats b").forEach((b,i)=>text(b,fmt(form[stats[i]]?.season??(state.league==="NFL"&&i===0?chosenPick()?.form?.season:null))));
 text(one(".next-match"),next?String(next.away_code)+" @ "+String(next.home_code):"Next matchup not in schedule");
 text(one(".hero-tile .tilebottom"),next?new Date(validDate(next.start)).toLocaleString("en-US",{timeZone:"America/New_York",month:"short",day:"numeric",hour:"numeric",minute:"2-digit"})+" ET · schedule source":"No verified next game");
 const photo=one(".portrait img");photo.hidden=true;photo.removeAttribute("src");
 const fallback=one(".portrait-fallback");text(fallback,item.player.split(" ").slice(0,2).map(x=>x[0]).join("").toUpperCase());
 state.playerPhoto=null;const seq=++photoRequest;resolvePhoto(item,seq);
}
function logsOfSelected(){
 if(state.league==="NBA"){
  const x=state.selected?.log;
  return Array.isArray(x)?x.filter(row=>Array.isArray(row)&&row.length>=7&&n(row[supported[state.stat][1]])!==null&&Number.isFinite(validDate(row[0]))).map(row=>({date:row[0],opp:String(row[1]||""),value:n(row[supported[state.stat][1]]),minutes:n(row[6])})).sort((a,b)=>validDate(a.date)-validDate(b.date)):[];
 }
 const p=chosenPick();return Array.isArray(p?.logs)?p.logs.filter(x=>n(x?.actual)!==null).map((x,i)=>({date:x.date||"Week "+String(x.week??i+1),opp:x.opponent||"",value:n(x.actual),minutes:null})):[];
}
function renderBars(rows,line){
 const chart=$("bars"),labels=$("barlabels");
 chart.replaceChildren();labels.replaceChildren();
 if(!rows.length){const p=document.createElement("p");p.className="dataempty";p.textContent="No recent completed-game log";chart.append(p);return}
 const subset=rows.slice(-10),max=Math.max(1,40,...subset.map(r=>r.value),n(line)||0);
 [max,Math.round(max*.75),Math.round(max*.5),Math.round(max*.25),0].forEach((v,i)=>{const ax=document.createElement("span");ax.className="axislabel axis-"+[40,30,20,10,0][i];ax.textContent=v;chart.append(ax)});
 subset.forEach((r,i)=>{const b=document.createElement("div");b.className="bar tooltip";b.style.setProperty("--v",String(Math.min(40,r.value/max*40)));b.dataset.label=String(r.value);b.dataset.tip=r.date+" vs "+r.opp+": "+r.value+" "+state.stat+(r.minutes===null?"":", "+r.minutes+" MIN");b.title=b.dataset.tip;b.setAttribute("aria-label",b.dataset.tip);chart.append(b);const a=document.createElement("span");a.textContent=r.date.slice(5);labels.append(a)});
}
function renderTrend(rows){
 const svg=$("trend-svg");svg.replaceChildren();
 if(rows.length<2)return;
 const W=310,subset=rows.slice(-30),max=Math.max(1,40,...subset.map(r=>r.value));
 const pts=subset.map((v,i)=>[25+i*280/(subset.length-1),125-v.value/max*105]);
 const d="M"+pts.map(p=>p.join(",")).join(" L");
 const ns="http://www.w3.org/2000/svg";
 const path=document.createElementNS(ns,"path");path.setAttribute("d",d);path.setAttribute("fill","none");path.setAttribute("stroke","#cc62ff");path.setAttribute("stroke-width","2.5");svg.append(path);
 pts.forEach(p=>{const c=document.createElementNS(ns,"circle");c.setAttribute("cx",p[0]);c.setAttribute("cy",p[1]);c.setAttribute("r","2.5");c.setAttribute("fill","#e4a9ff");svg.append(c)});
}
function makeStats(){
 const item=state.league==="NBA"?state.selected:state.nflSelected;
 if(!item)return;
 const logs=logsOfSelected(),p=chosenPick();
 const v=logs.map(x=>x.value);
 text($("games-title"),state.stat+" · last "+Math.min(v.length,10)+" completed games");
 text($("games-avg"),v.length?fmt(v.slice(-10).reduce((s,x)=>s+x,0)/Math.min(v.length,10)):"—");
 text($("trend-title"),item.player+" · "+state.stat+" trend ("+v.length+" games)");
 const trendavg=one("#trends .charttitle b");text(trendavg,v.length?fmt(v.reduce((a,b)=>a+b,0)/v.length):"—");
 renderBars(logs,p?.line);renderTrend(logs);
 const stat=state.stat;
 if(state.league==="NBA"){
  const labels={PTS:"Points",REB:"Rebounds",AST:"Assists",PRA:"Points + Rebounds + Assists"};
  text(one("#teammates h2"),"Teammate Impact ("+stat+")");setTable("#teammates tbody",3,"Not available: source has no verified teammate on/off participation");
  text(one("#splits h2"),"Key Splits ("+stat+")");
  const mf=item.metrics?.[stat]||{};
  const rows=[
   ["Last 5 completed",Math.min(5,logs.length),fmt(mf.l5),historical(logs.slice(-5),p)],
   ["Last 10 completed",Math.min(10,logs.length),fmt(mf.l10),historical(logs.slice(-10),p)],
   ["Season sample",item.games??logs.length,fmt(mf.season),"—"]
  ];rowTable("#splits tbody",rows);
  const h=one("#splits thead tr th:last-child");text(h,"Historical clears*");
 }else {
  text(one("#teammates h2"),"Teammate Impact");setTable("#teammates tbody",3,"NFL teammate on/off not in current published feed");
  rowTable("#splits tbody",[["Published season",p?.form?.games??"—",fmt(p?.form?.season),"—"],["Recent logs",logs.length,logs.length?fmt(logs.reduce((a,b)=>a+b.value,0)/logs.length):"—",historical(logs,p)]]);
 }
 const mm=one("#matchup .charttitle");
 text(mm,item.player+" vs "+(p?.opponent||"scheduled opponent not verified"));
 rowTable("#matchup tbody",stats.map(k=>[k,fmt(item.metrics?.[k]?.season),"—","—"]));
 const cols=all("#matchup th");if(cols[1])text(cols[1],item.team||"Player");if(cols[2])text(cols[2],"Opp defense");if(cols[3])text(cols[3],"Edge");
 const context=one(".contextlist");context.replaceChildren();
 const notes=[
  "Last "+Math.min(10,logs.length)+" observed games: "+(v.length?fmt(v.slice(-10).reduce((a,b)=>a+b,0)/Math.min(10,v.length))+" "+stat:"unavailable"),
  "Source: "+(state.league==="NBA"?(state.form?.source||"third-party completed game logs"):"NFL frozen standard lines"),
  "Defense vs position: unavailable until verified",
  "Teammate on/off and current injuries: not independently verified",
  "No historical hit fraction is used as a matchup hit estimate"
 ];
 for(const note of notes){const p=document.createElement("p");p.textContent="• "+note;context.append(p)}
}
function historical(logs,p){if(!p||n(p.line)===null||!logs.length)return "—";const valid=logs.filter(x=>n(x.value)!==null);return valid.filter(x=>p.direction==="MORE"?x.value>p.line:p.direction==="LESS"?x.value<p.line:false).length+"/"+valid.length+" past games"}
function renderProp(){
 const p=chosenPick(),dt=validDate(p?.start),has=!!p&&!p.quoteOnly&&n(p.projection)!==null;
 const mode=p?.direction==="MORE"?"Over":p?.direction==="LESS"?"Under":"Direction unverified";
 text(one(".focus-line"),p?mode+" "+fmt(p.line)+" "+state.stat+(dt<Date.now()?" · archived":""):"Standard line unavailable");
 text($("prop-line"),p?mode+" "+fmt(p.line)+" · "+(dt<Date.now()?"Archived":"Pregame")+" standard line":"No captured standard line");
 text($("model-proj"),has?fmt(p.projection):"—");
 text($("focus-proj"),has?fmt(p.projection):"—");
 const edge=has?((p.direction==="LESS"?p.line-p.projection:p.projection-p.line)):null;
 text($("model-edge"),edge===null?"—":(edge>=0?"+":"")+fmt(edge));
 text($("focus-edge"),edge===null?"—":(edge>=0?"+":"")+fmt(edge));
 const certified=has&&window.DamesPicksModel?.hitEstimate?.(p);
 const good=certified?.opponentAwareVerified===true&&n(certified.rate)!==null&&certified.rate>=0&&certified.rate<=1;
 const displayed=good?Math.round(certified.rate*100)+"%":"—";
 text(one(".ringcenter b"),displayed);
 const ring=one(".greenring");ring.style.background=good?"conic-gradient(#36dc98 "+(certified.rate*360)+"deg,#483d58 0)":"#40364e";
 const metrics=all(".metricboxes .metricbox b");
 if(metrics[2])text(metrics[2],displayed);if(metrics[3])text(metrics[3],"—");
 const focusPct=all(".focus-stats b")[1];text(focusPct,displayed);
 text(one(".bulletnotes"),good?"Verified pregame matchup-based estimate; "+(certified.calibrated?"calibrated":"not prospectively calibrated"):"No certified matchup-conditioned hit estimate for this captured standard line");
 const hist=$("histogram");hist.replaceChildren(Object.assign(document.createElement("p"),{className:"dataempty",textContent:"No verified forecast distribution published"}));
 text(one(".grading-head small"),"Settlements from frozen standard lines only");
 const graded=picksOfSelected().filter(x=>x.stat===state.stat&&x.grade==="GRADED"&&typeof x.hit==="boolean"&&n(x.actual)!==null).sort((a,b)=>validDate(b.start)-validDate(a.start)).slice(0,8);
 if(graded.length)rowTable("#grading tbody",graded.map(x=>[(x.start||"").slice(0,10),x.opponent||"—",fmt(x.line),fmt(x.actual),x.hit?"✓":"✗","Verified"]));
 else setTable("#grading tbody",6,"No verified settled standard-line predictions found for this player/stat");
 const pdesc=one("#lab .muted[style]");if(pdesc)text(pdesc,"Frozen pregame predictions and exact standard lines, when published");
 const disclosure=one("#lab .labgrid .muted");
 if(disclosure)text(disclosure,has?(dt<Date.now()?"This is an archived forecast, not a current recommendation. ":"")+(good?"Matchup estimate verified by model adapter.":"Hit estimate unavailable; do not substitute historical hit percentages."):"Model projection missing or quote-only. No projection has been invented.");
}
function answer(mode="stats"){
 const item=state.league==="NBA"?state.selected:state.nflSelected;
 const p=chosenPick(),logs=logsOfSelected();if(!item){text($("aianswer"),"No verified player is selected.");return}
 if(mode==="alternate"){
  const options=picksOfSelected().filter(x=>x.start===p?.start&&x.stat!==state.stat&&x.quoteOnly!==true&&n(x.projection)!==null).slice(0,3);
  text($("aianswer"),options.length?"Other frozen markets: "+options.map(x=>x.stat+" "+fmt(x.line)+" / projection "+fmt(x.projection)).join("; ")+". These aren't guaranteed picks.":"No alternate frozen standard market has been verified for this player and game.");return
 }
 if(mode==="compare"){
  text($("aianswer"),p&&n(p.line)!==null?"Standard "+state.stat+" line "+fmt(p.line)+(n(p.projection)!==null?", pregame frozen projection "+fmt(p.projection):", projection missing")+". Captured "+(p.captured||"timestamp unavailable")+". Historical hit percentages are not the model's matchup probability.":"No exact captured standard line to compare. No model value was inferred.");return
 }
 const metric=item.metrics?.[state.stat],v=logs.slice(-10);
 text($("aianswer"),item.player+" ("+item.team+"): "+state.stat+". "+(metric?.l5!==undefined?"L5 average "+fmt(metric.l5)+"; ":"")+(metric?.l10!==undefined?"L10 average "+fmt(metric.l10)+"; ":"")+(v.length?v.length+" completed game logs available. ":"No verified recent logs. ")+(p&&n(p.projection)!==null?"Frozen projection "+fmt(p.projection)+" against standard "+fmt(p.line)+". ":"No current verified frozen projection. ")+"Source: "+(state.form?.source||"published frozen NFL record")+". No unsupported injury/defense claims.");
}
function choose(name){
 const group=state.league==="NBA"?state.form?.players:state.nflPicks;
 if(!Array.isArray(group))return;
 const found=group.find(p=>norm(p.player)===norm(name));
 if(!found){changeNotice("Player not found in available "+state.league+" feed");return}
 if(state.league==="NBA")state.selected=found;else {state.nflSelected=found;state.stat=found.stat;wireNFLStat()}
 $("search").value=found.player;
 render();
}
function render(){
 renderNum++;renderGames();renderPlayer();makeStats();renderProp();answer(); 
 const available=(state.league==="NBA"?state.form?.players||[]:state.nflPicks);
 list.replaceChildren(...available.slice(0,1000).map(p=>{const o=document.createElement("option");o.value=p.player;return o}));
}
async function resolvePhoto(item,seq){
 // Development-only: ESPN roster headshot URL is NOT a license for commercial use.
 // Athlete ID from a non-ESPN feed is never used to construct an ESPN image URL.
 if(window.DAMES_DISABLE_EXTERNAL_PHOTOS===true)return;
 const sport=state.league==="NBA"?"basketball/nba":"football/nfl";
 const head="https://site.api.espn.com/apis/site/v2/sports/"+sport+"/teams";
 try{
  let teams=teamsCache.get(sport);
  if(!teams){const j=await remote(head);teams=j?.sports?.[0]?.leagues?.[0]?.teams?.map(x=>x.team||x)||[];teamsCache.set(sport,teams)}
  const team=teams.find(t=>String(t.abbreviation||"").toUpperCase()===String(item.team||"").toUpperCase());
  if(!team?.id)return;
  const data=await remote(head+"/"+encodeURIComponent(team.id)+"/roster");
  const roster=(data.athletes||[]).flatMap(a=>Array.isArray(a.items)?a.items:[a]);
  const matches=roster.filter(a=>norm(a.displayName||a.fullName||a.name)===norm(item.player));
  if(matches.length!==1||!matches[0].id)return;
  const href=matches[0].headshot?.href;
  if(typeof href!=="string")return;const u=new URL(href);
  if(u.protocol!=="https:"||u.hostname!=="a.espncdn.com")return;
  if(seq!==photoRequest)return;
  const img=one(".portrait img");
  img.onload=()=>{if(seq!==photoRequest)return;img.hidden=false;const fb=one(".portrait-fallback");if(fb)fb.hidden=true;state.playerPhoto={source:"ESPN roster",athleteId:String(matches[0].id),url:u.href};changeNotice(state.notice.replace(" · Photo unavailable","")+" · ESPN roster photo (development preview, rights review required)")};
  img.onerror=()=>{img.hidden=true};
  img.alt=item.player+" · ESPN roster headshot (rights clearance required before commercial use)";
  img.referrerPolicy="no-referrer";img.src=u.href;
 }catch(_){/* Missing/unlicensed/blocked headshots must degrade gracefully. */}
}
function wire(){
 $("stat").replaceChildren(...Object.entries(supported).map(([key,[label]])=>{const o=document.createElement("option");o.value=key;o.textContent=label==="pra"?"PRA":label[0].toUpperCase()+label.slice(1);return o}));
 $("stat").value=state.stat;
 $("stat").addEventListener("change",e=>{state.stat=e.target.value;makeStats();renderProp();answer()});
 $("search").addEventListener("keydown",e=>{if(e.key==="Enter"){e.preventDefault();choose(e.target.value)}});
 all("[data-scroll]").forEach(b=>b.addEventListener("click",()=>{const id=b.dataset.scroll,section=$(id);if(section)section.scrollIntoView({behavior:"smooth"});all("[data-scroll]").forEach(x=>x.classList.toggle("active",x.dataset.scroll===id))}));
 $("games-btn").addEventListener("click",()=>{$("sports").scrollIntoView({behavior:"smooth"});changeNotice("The Sports Center displays published schedule; a separate verified score is required to label LIVE.")});
 all("[data-action]").forEach(b=>b.addEventListener("click",()=>answer(b.dataset.action)));
 const sourceLink=document.createElement("a");sourceLink.href="index.html";sourceLink.className="legacy-link";sourceLink.textContent="Original live app ↗";sourceLink.setAttribute("aria-label","Open current NBA NFL Tennis website");one(".headicons")?.replaceWith(sourceLink);
 const leagueNav=document.createElement("div");leagueNav.className="sport-nav";leagueNav.setAttribute("aria-label","Sport");
 for(const sport of ["NBA","NFL","TENNIS"]){const b=document.createElement("button");b.type="button";b.textContent=sport;b.className=sport===state.league?"selected":"";b.addEventListener("click",()=>{if(sport==="TENNIS"){window.location.href="index.html";return}state.league=sport;all(".sport-nav button").forEach(btn=>btn.classList.toggle("selected",btn.textContent===sport));if(sport==="NFL")loadNFL();else if(state.form){state.stat="PTS";wireNBAStat();render();}});leagueNav.append(b)}
 const toolsBar=document.createElement("div");toolsBar.className="connected-tools";toolsBar.append(leagueNav);const mobile=document.createElement("div");mobile.className="mobile-search";const search=document.createElement("input");search.id="mobile-player-search";search.setAttribute("list","concept3-players");search.placeholder="Find player…";search.setAttribute("aria-label","Find player");search.addEventListener("keydown",e=>{if(e.key==="Enter")choose(search.value)});const go=document.createElement("button");go.type="button";go.textContent="Search";go.addEventListener("click",()=>choose(search.value));mobile.append(search,go);toolsBar.append(mobile);const back=document.createElement("a");back.href="index.html";back.className="connected-back";back.textContent="Current live app ↗";toolsBar.append(back);status.after(toolsBar);
}
async function loadNFL(){
 changeNotice("Loading archived NFL standard props and 2026 schedule…");
 if(state.nflSchedule){render();return}
 const m=window.DamesPicksModel;
 const [sched,manifest,arch]=await Promise.allSettled([get("nfl/data/schedule_2026.json"),get("nfl/data/latest_2026.json"),get("nfl/data/active_frozen_2026.json")]);
 if(sched.status==="fulfilled")state.nflSchedule=sched.value;
 else {changeNotice("NFL schedule unavailable; original app remains accessible");return}
 const chunks=[];
 if(arch.status==="fulfilled"&&arch.value?.scope==="EXACT_ARCHIVED_PREGAME_ROWS"&&Array.isArray(arch.value.records))chunks.push(arch.value.records);
 const files=manifest.status==="fulfilled"&&Array.isArray(manifest.value.files)?manifest.value.files.slice(0,16):[];
 const sets=await Promise.allSettled(files.map(async name=>m.csv(await get("nfl/data/"+name,"text"))));
 chunks.push(...sets.filter(x=>x.status==="fulfilled").map(x=>x.value));
 state.nflPicks=m.nfl(chunks,state.nflSchedule);
 state.nflSelected=state.nflPicks.find(p=>validDate(p.start)>=Date.now())||state.nflPicks[0]||null;
 if(state.nflSelected)state.stat=state.nflSelected.stat;
 if(!supported[state.stat]){const newStat=state.stat;supported[newStat]=[newStat.toLowerCase(),2];}
 wireNFLStat();
 render();
 refreshDirectScores();
 changeNotice("NFL linked: "+state.nflPicks.length+" valid standard-line records. No fabricated NFL game logs or probabilities.");
}
function wireNBAStat(){const keys=["PTS","REB","AST","PRA"];$("stat").replaceChildren(...keys.map(k=>{const o=document.createElement("option");o.value=k;o.textContent=k;return o}));$("stat").value=state.stat;}
function wireNFLStat(){
 const keys=[...new Set(state.nflPicks.filter(p=>norm(p.player)===norm(state.nflSelected?.player)).map(p=>p.stat))];
 $("stat").replaceChildren(...keys.map(k=>{const o=document.createElement("option");o.value=k;o.textContent=k;return o}));
 $("stat").value=state.stat;
}
let directBusy=false;
async function refreshDirectScores(){
 if(directBusy||window.DAMES_DISABLE_DIRECT_SCORES===true||document.hidden)return;
 const live=window.DamesPicksLive;if(!live)return;
 directBusy=true;
 try{
  if(state.league==="NBA"){
   const observed=await live.fetchNBA({timeoutMs:7000});
   const merged=live.mergeScores(state.scores,observed?.board||null);
   if(merged?.is_live_score_source===true){state.scores=merged;renderGames()}
  }else if(state.league==="NFL"&&state.nflSchedule){
   const observed=await live.fetchNFL(state.nflSchedule,{timeoutMs:7000});
   if(observed?.status==="ok"&&Array.isArray(observed.games)){state.nflLive=live.mergeNFL(state.nflLive,observed);renderGames()}
  }
 }catch(_){/* Preserve last genuinely verified observation; never invent scores. */}
 finally{directBusy=false}
}
setInterval(()=>{if(!document.hidden)refreshDirectScores()},30000);
document.addEventListener("visibilitychange",()=>{if(!document.hidden)refreshDirectScores()});
async function loadNBA(){
 resetPreview();wire();changeNotice("Loading verified NBA schedule and published completed-game statistics…");
 const [form,schedule,scores]=await Promise.allSettled([get("current_form.json"),get("nba_schedule.json"),get("nba_scoreboard_independent.json")]);
 if(form.status==="fulfilled"&&Array.isArray(form.value?.players))state.form=form.value;
 if(schedule.status==="fulfilled"&&Array.isArray(schedule.value?.games))state.schedule=schedule.value;
 if(scores.status==="fulfilled")state.scores=scores.value;
 state.selected=state.form?.players.find(p=>norm(p.player)==="lebronjames")||state.form?.players[0]||null;
 state.load=state.form?"partial":"failed";
 if(state.form)render();else renderGames();
 refreshDirectScores();
 changeNotice(state.form?"NBA player logs linked; fetching frozen forecasts and standard lines…":"NBA player feed unavailable; no example statistics shown");
 const [ledger,archive,confidence]=await Promise.allSettled([get("lagged_matchup_all_market_ledger.json","json",24000),get("prizepicks_pregame_line_archive.json","json",20000),get("nba_confidence_calibration.json")]);
 const m=window.DamesPicksModel;let picks=[];
 if(ledger.status==="fulfilled"&&state.form&&m?.nba)picks=m.nba(ledger.value,state.form);
 if(archive.status==="fulfilled"&&m?.includeArchivedStandard)picks=m.includeArchivedStandard(picks,archive.value);
 if(confidence.status==="fulfilled"&&m?.attachNBAConfidence)picks=m.attachNBAConfidence(picks,confidence.value);
 if(window.DamesPicksLineHistory&&state.form)picks=window.DamesPicksLineHistory.attachGameLogs(picks,state.form);
 state.picks=Array.isArray(picks)?picks:[];
 state.load=state.form?"complete":"failed";
 if(state.selected)render();
 changeNotice("NBA connected · "+(state.form?.players.length||0)+" logged players · "+state.picks.length+" validated standard-line records · "+(ledger.status==="fulfilled"?"model ledger read":"model ledger unavailable")+" · "+(archive.status==="fulfilled"?"standard archive read":"standard archive unavailable")+". Photos from ESPN rosters require licensing review.");
}
loadNBA().catch(e=>{document.body.classList.add("is-connected");changeNotice("Connected view failed safely: "+(e?.message||"unknown error")+". No example numbers displayed.")});
})();
