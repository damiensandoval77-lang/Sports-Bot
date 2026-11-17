/* Unified Dame's Picks workspace: selected Concept #3 front, existing production
   Board/Live/Tracker/Saved lazy-mounted inside the SAME website. */
(() => {
 "use strict";
 const names={player:"Player Intelligence",board:"Prop Board",live:"Live Scores",tracker:"Live Tracker",saved:"Saved Picks"};
 const allowed=Object.keys(names);
 const params=new URLSearchParams(location.search);
 let current=allowed.includes(params.get("workspace"))?params.get("workspace"):"player";
 let frameReady=false,loaded=false;
 const bar=document.createElement("nav");
 bar.className="unified-navigation";
 bar.setAttribute("aria-label","Dame's Picks workspaces");
 const tabs=new Map();
 for(const key of allowed){
  const btn=document.createElement("button");btn.type="button";
  btn.className="unified-tab";btn.textContent=names[key];
  btn.dataset.workspace=key;btn.addEventListener("click",()=>activate(key,true));
  tabs.set(key,btn);bar.append(btn);
 }
 const edge=document.createElement("div");edge.className="unified-status";
 edge.textContent="NBA • NFL · Verified-data workspace";bar.append(edge);
 const toolbar=document.querySelector(".connected-tools")||document.querySelector(".connected-banner")||document.querySelector(".topbar");
 toolbar.after(bar);
 const stage=document.createElement("section");
 stage.id="unified-workspace";stage.className="unified-workspace";stage.hidden=true;
 stage.setAttribute("aria-label","Live NBA/NFL prop board, tracker and saved picks");
 stage.innerHTML='<div class="workspace-head"><div><h1 id="unified-title">Prop Board</h1><p id="unified-subtitle">Frozen standard-line forecasts, results and grading</p></div><a href="classic.html" id="unified-direct" target="_blank" rel="noopener">Open full tool ↗</a></div><iframe id="unified-frame" title="Dame’s Picks unified live tools" loading="lazy" referrerpolicy="same-origin"></iframe><p class="workspace-footnote">Existing grading and live-tracking workflows are preserved until their complete replacement passes production tests.</p>';
 document.querySelector(".wrap").after(stage);
 const frame=stage.querySelector("iframe"),title=stage.querySelector("#unified-title"),sub=stage.querySelector("#unified-subtitle");
 const direct=stage.querySelector("#unified-direct");
 frame.addEventListener("load",()=>{frameReady=true;selectLegacy();});
 function league(key){
  return document.querySelector(".sport-nav .selected")?.textContent==="NFL"?"NFL":"NBA";
 }
 function tool(key){return ["board","live","tracker","saved"].includes(key)?key:"board"}
 function url(key){
  const u=new URL("classic.html",location.href);
  u.searchParams.set("league",league(key));u.searchParams.set("view",tool(key));return u.href;
 }
 function selectLegacy(){
  if(!frameReady||current==="player")return;
  frame.contentWindow?.postMessage({type:"dames:select-view",view:tool(current),league:league(current)},location.origin);
 }
 function activate(key,push){
  if(!allowed.includes(key))key="player";
  current=key;
  const isPlayer=key==="player";
  document.body.classList.toggle("unified-tool-mode",!isPlayer);
  stage.hidden=isPlayer;
  tabs.forEach((b,k)=>{b.classList.toggle("selected",k===key);b.setAttribute("aria-pressed",String(k===key));});
  if(!isPlayer){
   const captions={
    board:"Original pregame projections and exact standard PrizePicks lines",
    live:"Independent NBA/NFL scoreboards and verified player totals",
    tracker:"Live actual totals and on-pace readings, kept separate from frozen forecasts",
    saved:"Saved standard-line picks, settlement and verified grading"
   };
   title.textContent=names[key];sub.textContent=captions[key];direct.href=url(key);
   if(!loaded){loaded=true;frame.src=url(key)}else selectLegacy();
  }
  if(push){
   const u=new URL(location.href);
   if(isPlayer)u.searchParams.delete("workspace");else u.searchParams.set("workspace",key);
   history.pushState({workspace:key},"",u);
  }
  if(!isPlayer||push)window.scrollTo({top:0,behavior:"instant"});
 }
 document.querySelectorAll("[data-scroll]").forEach(b=>b.addEventListener("click",()=>{
  if(current!=="player")activate("player",true);
 }));
 function bindBoardLink(){
  const link=document.querySelector(".legacy-link");
  if(!link)return;
  link.href=url("board");link.textContent="Prop Board ↗";
  link.addEventListener("click",e=>{e.preventDefault();activate("board",true)});
 }
 bindBoardLink();
 window.addEventListener("popstate",()=>{
  const p=new URLSearchParams(location.search).get("workspace");
  activate(allowed.includes(p)?p:"player",false);
 });
 window.DamesUnifiedUI={open:key=>activate(key,true),current:()=>current,version:"20261117-r1"};
 activate(current,false);
})();
