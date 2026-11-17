/* DS5 first-concept dashboard — DOM presentation only.
   Reuses existing connected NBA/NFL data and original unified app workspaces.
   Never manufactures game scores, props, probabilities, actuals, or grade counts. */
(() => {
 "use strict";
 const $ = s => document.querySelector(s);
 const el = (tag,cls,txt) => {const x=document.createElement(tag);if(cls)x.className=cls;if(txt!==undefined)x.textContent=txt;return x};
 const num = v => v===null||v===undefined||v===""||!Number.isFinite(Number(v))?null:Number(v);
 const fmt = v => num(v)===null?"—":Number(v).toFixed(1);
 const stamp = v => {const n=Date.parse(v);return Number.isFinite(n)?n:NaN};
 const etDate=v=>{const t=typeof v==="number"?v:stamp(v);return Number.isFinite(t)?new Intl.DateTimeFormat("en-CA",{timeZone:"America/New_York",year:"numeric",month:"2-digit",day:"2-digit"}).format(new Date(t)):null};
 const today = ()=>etDate(Date.now());
 const wrap=$("main.wrap"),slate=$("#sports"),hero=$("#intelligence"),gridtop=$(".gridtop"),gridmid=$(".gridmiddle"),gridbottom=$(".gridbottom"),tabs=$(".tabs");
 const recent=gridtop?.querySelector('[aria-label="Recent game performance"]');
 const distribution=gridtop?.querySelector('[aria-label="Projection distribution"]');
 const matchup=$("#matchup");
 if(!wrap||!slate||!hero||!gridtop||!gridmid||!gridbottom||!tabs||!recent||!distribution||!matchup)return;

 const board = el("div","ds5-dashboard");
 const sidebar=el("aside","ds5-sidebar");sidebar.setAttribute("aria-label","DS5 site navigation");
 const logo=el("div","ds5-side-logo");
 logo.innerHTML='<strong>DS<em>5</em></strong><small>SPORTS MEDIA</small>';
 const nav=el("nav","ds5-side-nav");nav.setAttribute("aria-label","Sections");
 const items=[
  ["▥","Dame's Picks","board"],["♙","Player Intelligence","#intelligence"],["⚗","Prediction Lab","#lab"],
  ["▦","Sports Center","#sports"],["◉","NBA","league:NBA"],["◉","NFL","league:NFL"],
  ["◉","Live Tracker","tracker"],["✓","Grading & Results","saved"],["▤","Research Hub","#ds5-research"],["☆","Saved Picks","saved"]
 ];
 for(const [ico,label,dest] of items){
  const b=el("button",dest==="board"?"active":dest.startsWith("league:")?"ds5-subnav":"");
  b.type="button";b.innerHTML='<span class="ico" aria-hidden="true"></span><span class="ds5-nav-label"></span>';
  b.querySelector(".ico").textContent=ico;b.querySelector(".ds5-nav-label").textContent=label;
  b.addEventListener("click",()=>{
   nav.querySelectorAll("button").forEach(x=>x.classList.remove("active"));b.classList.add("active");
   if(dest.startsWith("#")) {
    if(document.body.classList.contains("unified-tool-mode"))window.DamesUnifiedUI?.open("player");
    window.requestAnimationFrame(()=>document.querySelector(dest)?.scrollIntoView({behavior:"smooth",block:"start"}));
   } else if(dest.startsWith("league:")){
    const sport=dest.split(":")[1];
    if(document.body.classList.contains("unified-tool-mode"))window.DamesUnifiedUI?.open("player");
    const x=[...document.querySelectorAll(".sport-nav button")].find(btn=>btn.textContent.trim()===sport);
    if(x)x.click();
   } else window.DamesUnifiedUI?.open(dest);
  });
  nav.append(b);
 }
 sidebar.append(logo,nav,el("p","ds5-side-footer","DS5 Sports Media · NBA / NFL intelligence and verified-data research"));
 const main=el("div","ds5-main");
 const title=el("header","ds5-titlebar");
 title.innerHTML='<div><h1>PLAYER <span>INTELLIGENCE</span></h1><p>Matchups. Projections. Every angle.</p></div><div class="ds5-dames-stamp">DAME\'S PICKS<small>AI PROJECTIONS · PROP EDGES · GRADES</small></div>';
 const feature=el("div","ds5-feature-grid");
 const left=el("div","ds5-player-feature"),right=el("div","ds5-matchup-feature");
 const next=hero.querySelector(".hero-tile:not(.focus)");
 left.append(hero,recent);
 const rows=el("div","ds5-matchup-rows");rows.append(matchup,distribution);
 const take=el("section","ds5-take");take.setAttribute("aria-label","Dame's Take");
 take.innerHTML='<b>Dame\'s Take</b><p id="ds5-take-text">Waiting for a verified player projection.</p>';
 right.append(next,rows,take);
 feature.append(left,right);

 const lower=el("div","ds5-lower-grid");
 function createPanel(panelTitle,target,html){
  const sec=el("section","ds5-summary");
  const head=el("div","ds5-summary-head");
  head.append(el("h2","",panelTitle));
  const btn=el("button","","Open full view");btn.type="button";btn.setAttribute("aria-label","Open "+panelTitle);
  btn.addEventListener("click",()=>window.DamesUnifiedUI?.open(target));head.append(btn);
  sec.append(head);const body=el("div");body.innerHTML=html;sec.append(body);return sec;
 }
 const props=createPanel("Today's Player Props","board",'<table><thead><tr><th>Player</th><th>Market</th><th>Std. line</th><th>Proj.</th><th>Edge</th><th>Lean</th></tr></thead><tbody id="ds5-props-rows"><tr><td colspan="6" class="ds5-empty">Loading verified standard-line data…</td></tr></tbody></table>');
 const live=createPanel("Live Tracker","tracker",'<div id="ds5-live-info" class="ds5-empty">Waiting for independently verified game and player totals…</div>');
 const grade=createPanel("Grading (Last 30 Days)","saved",'<div class="ds5-grade-meter"><div class="ds5-grade-ring"><strong id="ds5-grade-rate">—</strong><small>HIT RATE</small></div><div class="ds5-grade-stats"><div><b id="ds5-grade-total">—</b> graded</div><div><b id="ds5-grade-hits">—</b> hits</div><div><b id="ds5-grade-misses">—</b> misses</div></div></div><div class="ds5-subtitle" id="ds5-grade-note">Verified settled predictions only. Incomplete results are excluded.</div>');
 lower.append(props,live,grade);
 const researchTitle=el("h2","ds5-research-title","Detailed matchup research");
 researchTitle.id="ds5-research";
 const footer=el("footer","ds5-footer");
 footer.innerHTML='<span><strong>DS<em>5</em></strong> SPORTS MEDIA &nbsp; | &nbsp; DAME\'S PICKS ANALYTICS</span><span>NBA &nbsp; · &nbsp; NFL &nbsp; · &nbsp; PROJECTIONS &nbsp; · &nbsp; VERIFIED GRADES</span>';
 wrap.insertBefore(board,hero);
 board.append(sidebar,main);
 const foot=$(".footnote");
 main.append(title,feature,lower,tabs,researchTitle,gridtop,gridmid,gridbottom);
 if(foot)main.append(foot);
 main.append(footer);

 /* Move existing NBA/NFL selector into the first concept's top-right header. */
 const sport=$(".connected-tools .sport-nav"),search=$(".topbar .searchbox");
 if(sport&&search)search.before(sport);
 /* Keep the title corresponding to the actual parent brand. */
 const topNav=$(".topbar .nav button[data-scroll='top']");
 if(topNav){topNav.lastChild.textContent="Overview"}
 document.body.classList.add("ds5-first-concept");

 function source(){try{return window.DS5DashboardSource?.()||null}catch(_){return null}}
 function setBodyText(selector,txt){const x=$(selector);if(x)x.textContent=txt}
 function cleanedPicks(s){
  const records=s?.picks;
  if(!Array.isArray(records))return [];
  return records.filter(p=>{
   if(!p||!["NBA","NFL"].includes(p.sport||s.league))return false;
   if(!Number.isFinite(stamp(p.start))||!Number.isFinite(stamp(p.captured))||stamp(p.captured)>stamp(p.start))return false;
   const mode=String(p.marketTier||p.lineVariant||p.lineType||p.variant||"").toLowerCase();
   if(/demon|goblin|alternate|alt[ _-]?line/.test(mode))return false;
   return num(p.line)!==null;
  });
 }
 function setCells(row,values){
  for(const [t,className,sub] of values){
   const td=el("td",className||"");td.textContent=String(t??"—");
   if(sub){const small=el("em","",sub);td.append(small)}
   row.append(td);
  }
 }
 function renderPicks(s,rows){
  const host=$("#ds5-props-rows");if(!host)return;
  host.replaceChildren();
  const upcoming=rows.filter(p=>etDate(p.start)===today() && stamp(p.start)>=Date.now()-300000 &&
    p.quoteOnly!==true && num(p.projection)!==null &&
    (p.direction==="MORE"||p.direction==="LESS"));
  const dedup=new Map();
  for(const p of upcoming){
   const key=[p.sport||s.league,p.player,p.gameId||p.game||p.start,p.stat,p.line].join("|");
   const old=dedup.get(key);
   if(!old || stamp(p.captured)>stamp(old.captured))dedup.set(key,p);
  }
  const list=[...dedup.values()].sort((a,b)=>{
   const aedge=(a.direction==="LESS"?num(a.line)-num(a.projection):num(a.projection)-num(a.line));
   const bedge=(b.direction==="LESS"?num(b.line)-num(b.projection):num(b.projection)-num(b.line));
   return bedge-aedge || String(a.player).localeCompare(String(b.player));
  }).slice(0,6);
  if(!list.length){
   const tr=el("tr");
   const td=el("td","ds5-empty",s?.status==="loading"?"Loading the current standard-line board…":"No verified, still-pregame standard props available for today's slate.");
   td.colSpan=6;tr.append(td);host.append(tr);return;
  }
  for(const p of list){
   const tr=el("tr");
   const rawEdge=p.direction==="LESS"?num(p.line)-num(p.projection):num(p.projection)-num(p.line);
   const lean=p.direction==="MORE"?"OVER":"UNDER";
   const market=String(p.stat||"—");
   const descr=[String(p.team||""),p.opponent?("vs "+p.opponent):""].filter(Boolean).join(" ");
   setCells(tr,[
    [p.player,"",descr],[market,""],[fmt(p.line),""],[fmt(p.projection),"ds5-good"],
    [(rawEdge>=0?"+":"")+fmt(rawEdge),rawEdge>=0?"ds5-good":"ds5-bad"],[lean,lean==="OVER"?"ds5-good":"ds5-bad"]
   ]);
   host.append(tr);
  }
 }
 function renderLive(s){
  const info=$("#ds5-live-info");if(!info)return;
  const liveGames=(s?.games||[]).filter(g=>g.state==="live");
  info.replaceChildren();
  const summary=el("p","",liveGames.length?liveGames.length+" independently verified live "+s.league+" game"+(liveGames.length===1?"":"s")+" currently on the scoreboard.":"No independently verified live "+(s?.league||"NBA")+" games in the loaded slate.");
  info.append(summary);
  if(liveGames.length){
   const t=el("table");
   const tb=el("tbody");
   for(const g of liveGames.slice(0,5)){
    const tr=el("tr");
    setCells(tr,[[String(g.away_code||g.away||"—")+" @ "+String(g.home_code||g.home||"—"),""],[num(g.awayScore)!==null&&num(g.homeScore)!==null?String(g.awayScore)+"–"+String(g.homeScore):"—",""]]);
    tb.append(tr);
   }t.append(tb);info.append(t);
  }
  const note=el("p","");note.style.marginTop="12px";note.textContent="Player pace and actual totals are shown only in the verified live tracker. No projections are presented as live results.";
  info.append(note);
 }
 function renderGrades(s,rows){
  const cutoff=Date.now()-30*24*3600*1000;
  const graded=rows.filter(p=>p.grade==="GRADED" && typeof p.hit==="boolean" && num(p.actual)!==null && stamp(p.start)>=cutoff && stamp(p.start)<=Date.now());
  const dedup=new Map();
  for(const p of graded){
   const key=[p.sport||s.league,p.player,p.gameId||p.game||p.start,p.stat,p.line].join("|");
   const old=dedup.get(key);
   if(!old||stamp(p.captured)>stamp(old.captured))dedup.set(key,p);
  }
  const final=[...dedup.values()],hits=final.filter(p=>p.hit).length,n=final.length;
  setBodyText("#ds5-grade-rate",n?Math.round(100*hits/n)+"%":"—");
  setBodyText("#ds5-grade-total",n?String(n):"0");
  setBodyText("#ds5-grade-hits",n?String(hits):"0");
  setBodyText("#ds5-grade-misses",n?String(n-hits):"0");
  setBodyText("#ds5-grade-note",n?"In currently loaded "+s.league+" records; frozen, verified standard lines only. Not a lifetime accuracy claim.":"No verified settled standard-line rows from the past 30 days in this loaded dataset.");
  const ring=$("#ds5-grade-rate")?.parentElement;
  if(ring)ring.style.borderColor=n?(hits/n>=.5?"#38e8a6":"#ff6687"):"#34273c";
 }
 function renderTake(s,rows){
  const p=s?.selectedPick,host=$("#ds5-take-text");
  if(!host)return;
  const eligible=p&&p.quoteOnly!==true&&num(p.projection)!==null&&num(p.line)!==null
   &&stamp(p.captured)<=stamp(p.start)&&stamp(p.start)>Date.now()-3600000;
  if(!eligible){host.textContent="No verified current projection and standard line for the selected player.";return}
  const lean=p.direction==="MORE"?"over":p.direction==="LESS"?"under":"no direction";
  host.textContent=lean==="no direction"?"Published projection: "+fmt(p.projection)+"; standard line: "+fmt(p.line)+". No verified lean.":"Model leans "+lean+". "+fmt(p.projection)+" projection vs "+fmt(p.line)+" standard line.";
 }
 function refresh(){
  const s=source();if(!s)return;
  const rows=cleanedPicks(s);
  renderPicks(s,rows);renderLive(s);renderGrades(s,rows);renderTake(s,rows);
 }
 document.addEventListener("ds5:data-updated",refresh);
 refresh();
 /* Updates to direct ESPN scores do not alter models or consume paid odds credits. */
 document.addEventListener("visibilitychange",()=>{if(!document.hidden)refresh()});
 window.DS5ConceptOne={refresh,version:"first-concept-20261117"};
})();
