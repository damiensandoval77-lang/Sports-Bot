/* DS5 verified market board: read-only Cloudflare D1 quotes, never a provider request.
   No AI projection, hit rate, grade, or player identity is inferred from a quote. */
(()=>{
 "use strict";
 const root=document.querySelector(".ds5-main");
 if(!root)return;
 const API="https://dames-picks-staging.damiensandoval77.workers.dev";
 const el=(tag,className,text)=>{const node=document.createElement(tag);
   if(className)node.className=className;if(text!==undefined)node.textContent=text;return node};
 const section=el("section","ds5-odds-market");section.id="ds5-odds-market";
 section.setAttribute("aria-label","Verified live provider market quotes");
 const head=el("header","ds5-odds-head");
 const title=el("div");title.append(el("h2","","LIVE MARKET LINES"),
   el("p","","Provider-verified standard pregame quotes · NOT AI predictions"));
 const actions=el("div","ds5-odds-actions");
 const league=el("select","");league.setAttribute("aria-label","Select sport for verified provider lines");
 for(const name of ["NBA","NFL"]){const opt=el("option","",name);opt.value=name;league.append(opt)}
 const refresh=el("button","","Refresh quotes");refresh.type="button";
 const link=el("a","","Full Market Explorer");
 link.href=API+"/dames-picks/market-explorer.html";
 link.rel="noopener noreferrer";link.target="_blank";
 actions.append(league,refresh,link);head.append(title,actions);
 const status=el("p","ds5-odds-status","Checking Cloudflare D1 for verified standard lines…");
 status.setAttribute("role","status");
 const grid=el("div","ds5-odds-rows");
 section.append(head,status,grid);
 const mainTitle=root.querySelector(".ds5-titlebar");
 if(mainTitle)mainTitle.after(section);else root.prepend(section);
 const state={NBA:[],NFL:[],lastFetch:null,loading:false,error:null};
 const readableTime=iso=>{const d=Date.parse(iso||"");
  return Number.isFinite(d)?new Intl.DateTimeFormat("en-US",{
    timeZone:"America/New_York",month:"short",day:"numeric",hour:"numeric",minute:"2-digit"
  }).format(new Date(d))+" ET":"time unavailable"};
 function valid(p,now){
  return p&&p.is_standard===true&&["prizepicks","underdog","fanduel","draftkings"].includes(p.bookmaker)&&
    Number.isFinite(Number(p.line))&&p.line!==null&&typeof p.player==="string"&&
    typeof p.market_key==="string"&&Number.isFinite(Date.parse(p.event_start))&&
    Date.parse(p.event_start)>now&&Number.isFinite(Date.parse(p.observed_at))&&
    Date.parse(p.observed_at)>now-90*60000&&Date.parse(p.observed_at)<Date.parse(p.event_start);
 }
 function render(){
  const sport=league.value,quotes=state[sport],now=Date.now();
  const fresh=quotes.filter(q=>valid(q,now));
  grid.replaceChildren();
  if(state.loading&&!state.lastFetch){status.textContent="Reading cached Cloudflare market data…";return}
  if(state.error&&!state.lastFetch){status.textContent="Cloudflare market cache unavailable. No unverified lines shown.";return}
  status.textContent=fresh.length
   ?fresh.length+" source-verified standard "+sport+" market rows · last cache check "+readableTime(state.lastFetch)
   :"No recent source-verified standard "+sport+" lines are available. Unverified lines are not displayed.";
  for(const q of fresh.slice(0,4)){
    const row=el("article","ds5-odds-row");
    const player=el("div","ds5-odds-player");
    player.append(el("strong","",q.player),el("small","",q.matchup||"Upcoming game"));
    const market=el("div","ds5-odds-market-info");
    market.append(el("strong","",q.market_key.replaceAll("_"," ").replace(/^player /i,"")),
      el("small","",q.bookmaker+" · "+readableTime(q.observed_at)));
    const number=el("strong","ds5-odds-line",String(q.line));
    row.append(player,market,number);grid.append(row);
  }
  if(fresh.length>4)grid.append(el("p","ds5-odds-more",
    "Showing 4 of "+fresh.length+" verified lines · open Market Explorer for all"));
 }
 async function get(sport){
   const ctl=new AbortController();const timer=setTimeout(()=>ctl.abort(),10000);
   try{
    const response=await fetch(API+"/api/v1/odds/board?league="+sport+"&limit=100",{
      cache:"no-store",signal:ctl.signal});
    if(!response.ok)throw Error("Market cache unavailable");
    const json=await response.json();
    if(!json||!Array.isArray(json.quotes))throw Error("Invalid market board");
    return json.quotes;
   }finally{clearTimeout(timer)}
 }
 async function update(){
  if(state.loading)return;
  state.loading=true;refresh.disabled=true;render();
  const all=await Promise.allSettled([get("NBA"),get("NFL")]);
  let succeeded=false;
  for(const [i,sport] of ["NBA","NFL"].entries()){
   if(all[i].status==="fulfilled"){state[sport]=all[i].value;succeeded=true}
  }
  state.lastFetch=succeeded?new Date().toISOString():state.lastFetch;
  state.error=!succeeded;
  state.loading=false;refresh.disabled=false;render();
 }
 league.addEventListener("change",render);
 refresh.addEventListener("click",update);
 document.addEventListener("visibilitychange",()=>{if(!document.hidden&&
  (!state.lastFetch||Date.now()-Date.parse(state.lastFetch)>60000))update()});
 setInterval(()=>{if(!document.hidden)update()},60000);
 update();
})();
