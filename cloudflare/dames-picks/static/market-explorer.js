/* Dame's Picks Cloudflare-only Market Explorer.
 * Browser always reads cached D1 data; it NEVER calls The Odds API directly.
 * No demo odds, fabricated players, implied DFS payout probabilities or
 * inferred model estimates. Text uses textContent, not provider HTML.
 */
(()=>{
"use strict";
const $=id=>document.getElementById(id);
const nodes=s=>[...document.querySelectorAll(s)];
const state={league:"NBA",catalog:null,quotes:[],provider:"all",market:"all",tier:"all",search:""};
const text=(el,value)=>{if(el)el.textContent=String(value??"—")};
const label={prizepicks:"PrizePicks",underdog:"Underdog",fanduel:"FanDuel",draftkings:"DraftKings"};
const timeLabel=s=>{
 const d=Date.parse(s||"");return Number.isFinite(d)?new Date(d).toLocaleString("en-US",{
  month:"short",day:"numeric",hour:"numeric",minute:"2-digit",timeZone:"America/New_York"
 })+" ET":"Timestamp unavailable";
};
const amount=n=>typeof n==="number"&&Number.isFinite(n)?String(n):"—";
const price=n=>typeof n==="number"&&Number.isFinite(n)?(n>0?"+":"")+n:"—";
async function json(path){
 const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),9000);
 try{
  const r=await fetch(path,{cache:"no-store",signal:controller.signal});
  const body=await r.json();
  return {status:r.status,body};
 }finally{clearTimeout(timer)}
}
function make(tag,value,cl=""){
 const el=document.createElement(tag);if(value!==undefined&&value!==null)el.textContent=String(value);
 if(cl)el.className=cl;return el
}
function redrawCatalog(){
 const source=state.catalog?.leagues?.[state.league]?.markets||[];
 const core=source.filter(x=>x.tier==="core").length;
 text($("count-total"),source.length);text($("count-core"),core);text($("count-extra"),source.length-core);
 const words=state.search.toLowerCase().trim();
 const matches=source.filter(x=>(state.tier==="all"||x.tier===state.tier)&&
  (!words||(x.label+" "+x.key+" "+x.stat).toLowerCase().includes(words)));
 const dest=$("catalog");
 dest.replaceChildren(...matches.map(x=>{
  const c=make("div",null,"market");
  c.append(make("b",x.label),make("small",x.stat+" · "+x.key),make("span",x.tier,x.tier==="core"?"tag good":"tag"));
  if(x.bet_type!=="over_under")c.append(make("small","Yes/No: not scanned as a standard Over/Under line"));
  return c;
 }));
 if(!matches.length)dest.append(make("p","No documented markets match these filters.","small"));
 const marketSel=$("market");
 const previously=state.market;
 marketSel.replaceChildren(make("option","All markets"));
 marketSel.firstElementChild.value="all";
 for(const m of source.filter(x=>x.bet_type==="over_under")){
  const op=make("option",m.label);op.value=m.key;marketSel.append(op);
 }
 if([...marketSel.options].some(x=>x.value===previously))marketSel.value=previously;
 else {marketSel.value="all";state.market="all";}
}
function redrawBoard(){
 const shown=state.quotes.filter(x=>(state.provider==="all"||x.bookmaker===state.provider)&&
  (state.market==="all"||x.market_key===state.market));
 const tbody=$("board").querySelector("tbody");
 tbody.replaceChildren();
 for(const q of shown.slice(0,100)){
  const tr=document.createElement("tr"),cells=[
   q.player,q.bookmaker,q.market_key,amount(q.line),
   q.line_change===null?"—":(q.line_change>0?"+":"")+q.line_change,
   q.bookmaker_price_type==="sportsbook_american"?price(q.over_price)+" / "+price(q.under_price):"DFS: indicative",
   q.sportsbook_no_vig_over===null?"—":Math.round(q.sportsbook_no_vig_over*100)+"% Over (market)",
   timeLabel(q.observed_at)
  ];
  cells.forEach((value,i)=>{
   const td=make("td",i===1?(label[value]||value):value);
   if(i===0)td.append(make("small",q.matchup));
   if(i===3)td.className="good";
   tr.append(td);
  });
  tbody.append(tr);
 }
 $("board").hidden=!shown.length;$("board-empty").hidden=Boolean(shown.length);
 text($("status"),shown.length
  ?shown.length+" verified recent standard market observations from Cloudflare D1 · no provider request made"
  :"No recent, two-sided verified standard quotes available for this selection");
}
async function loadBoard(){
 text($("status"),"Reading stored Cloudflare market snapshots…");
 try{
  const response=await json("/api/v1/odds/board?league="+encodeURIComponent(state.league)+"&limit=100");
  state.quotes=Array.isArray(response.body?.quotes)?response.body.quotes:[];
  if(response.status!==200)text($("status"),"D1 market cache isn't initialized yet. No Odds API credits were used.");
  text($("updated"),response.status===200
   ?(state.quotes.length?"Latest provider-observed lines (not AI picks)":"No stored source-verified pregame lines yet")
   :"Database setup pending · app operates in catalog-only mode");
  redrawBoard();
 }catch(_){
  state.quotes=[];redrawBoard();text($("status"),"Market cache unavailable; no stale or invented lines displayed");
 }
}
async function loadBudget(){
 try{
  const [result,catalog,diagnostics]=await Promise.all([
   json("/api/v1/odds/budget"),json("/api/v1/odds/catalog"),
   json("/api/v1/odds/diagnostics").catch(()=>null)
  ]);
  if(catalog.status===200&&catalog.body?.leagues){state.catalog=catalog.body;redrawCatalog()}
  else text($("catalog"),"Market catalog not available");
  const v=result.body||{};
  const config=v.config||{};
  text($("collection"),config.collection_enabled?"Configured":"Off");
  const used=v.usage?.used_credits;
  text($("credits"),typeof used==="number"?used:"—");
  const latest=diagnostics?.body?.recent_runs?.[0];
  const lastSummary=diagnostics?.status===200
   ?(latest?" Last scheduled collection: "+latest.status+" ("+(latest.quotes_stored??0)+" new lines, "+(latest.credits_charged??0)+" credits)."
     :" No odds collector runs recorded yet.")
   :" Collector diagnostic status unavailable.";
  text($("budget-status"),(result.status===200
   ?"D1 recorded usage: "+(used??0)+" credits this month. "+(config.collection_enabled?"Provider opt-in configured.":"No automatic paid requests enabled.")+
     " Monthly ceiling: "+(config.monthly_cap??"not set")+". Daily ceiling: "+(config.daily_cap??"not set")+"."
   :"D1 odds ledger is not initialized.")+lastSummary);
 }catch(_){text($("budget-status"),"Budget ledger unavailable · paid collection not confirmed")}
}
function wire(){
 nodes("[data-league]").forEach(b=>b.addEventListener("click",()=>{
  state.league=b.dataset.league;nodes("[data-league]").forEach(x=>x.classList.toggle("active",x===b));
  state.market="all";state.search="";state.tier="all";$("search").value="";$("tier").value="all";state.quotes=[];redrawCatalog();redrawBoard();loadBoard();
 }));
 $("search").addEventListener("input",e=>{state.search=e.target.value;redrawCatalog()});
 $("tier").addEventListener("change",e=>{state.tier=e.target.value;redrawCatalog()});
 $("provider").addEventListener("change",e=>{state.provider=e.target.value;redrawBoard()});
 $("market").addEventListener("change",e=>{state.market=e.target.value;redrawBoard()});
 $("refresh").addEventListener("click",()=>{loadBoard();loadBudget()});
}
wire();loadBudget();loadBoard();
})();
