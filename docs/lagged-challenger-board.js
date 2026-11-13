/* Independent, points-only new AI comparison. Never overrides legacy picks. */
(function(){
"use strict";
const SOURCE="./lagged_matchup_live_points.json";
const byId=id=>document.getElementById(id);
const el=(tag,cls,value)=>{
 const x=document.createElement(tag);
 if(cls)x.className=cls;
 if(value!==undefined)x.textContent=String(value);
 return x;
};
function render(data){
 const board=byId("lagged-challenger-board"),status=byId("lagged-challenger-status");
 if(!board||!status)return;
 board.replaceChildren();
 const now=Date.now(),generated=Date.parse(data?.generated_at);
 const valid=data?.status==="LIVE_POINTS_CHALLENGER_UNCALIBRATED" &&
   data?.points_only===true &&
   data?.market_line_policy==="STANDARD_ONLY_BOTH_SIDES_VERIFIED_NO_ALTERNATES" &&
   data?.live_model_replaced===false &&
   data?.probabilities_validated===false &&
   Number.isFinite(generated) && generated<=now+600000 &&
   now-generated<10800000 && Array.isArray(data?.predictions);
 if(!valid){
   status.textContent="No current verified new-model forecast. Existing AI board remains unaffected.";
   return;
 }
 const items=data.predictions.filter(x=>{
   const tip=Date.parse(x.start),quoted=Date.parse(x.market_updated);
   return x.stat==="PTS"&&x.real_prizepicks_line===true &&
     x.pickem_tier==="standard"&&x.standard_line_two_sided_verified===true &&
     x.research_only===true&&x.production_replaced===false &&
     x.calibrated_probability===null &&
     typeof x.projection==="number"&&Number.isFinite(x.projection)&&
     typeof x.line==="number"&&Number.isFinite(x.line)&&
     tip>now&&quoted<=now+600000&&now-quoted<21600000&&quoted<tip;
 });
 items.sort((a,b)=>Date.parse(a.start)-Date.parse(b.start) ||
   Math.abs(b.projection-b.line)-Math.abs(a.projection-a.line));
 const limited=items.slice(0,120);
 status.textContent=items.length+" verified STANDARD PrizePicks points comparisons · "+
   "new model per-line simulated chances are experimental, not verified hit rates. "+
   (items.length>limited.length?"Showing first "+limited.length+".":"");
 if(!limited.length){
   board.append(el("div","empty","No unstarted points comparisons with current verified lines."));
   return;
 }
 for(const x of limited){
   const card=el("article","prop compact-prop");
   const body=el("div","mainline");
   const head=el("div","head");
   head.append(el("strong","",x.player+" · PTS"),
               el("span","tag neutral","New AI"));
   body.append(head);
   body.append(el("div","match",x.game+" · "+new Date(x.start).toLocaleTimeString([],{hour:"numeric",minute:"2-digit"})));
   const values=el("div","vals");
   for(const [caption,value] of [
     ["New projection",x.projection.toFixed(1)],
     ["PrizePicks STANDARD",x.line.toFixed(1)],
     ["Projection − line",(x.projection-x.line>0?"+":"")+(x.projection-x.line).toFixed(1)]
   ]){
     const cell=el("div","val");
     cell.append(el("b","",value),el("small","",caption));
     values.append(cell);
   }
   body.append(values);
   const chance=x.estimated_hit_chance;
   const credible=chance?.method==="2024_25_OUT_OF_TRAINING_RESIDUAL_20K_BOOTSTRAP_UNVALIDATED" &&
       chance.draws===20000 && chance.calibrated===false &&
       Number.isInteger(chance.validation_residual_count) &&
       chance.validation_residual_count>=1000 &&
       ["More","Less"].includes(chance.estimated_selected_side) &&
       typeof chance.estimated_selected_probability==="number" &&
       Number.isFinite(chance.estimated_selected_probability) &&
       chance.estimated_selected_probability>=0 &&
       chance.estimated_selected_probability<=1;
   if(credible){
     const chanceBox=el("div","detail-highlight");
     const percent=(chance.estimated_selected_probability*100).toFixed(1)+"%";
     chanceBox.append(el("strong","","Modeled "+chance.estimated_selected_side+" chance: "+percent));
     chanceBox.append(el("div","mini","20,000 historical-error draws · "+
       chance.validation_residual_count+" out-of-training observations. "+
       "Experimental estimate, NOT verified live hit rate."));
     body.append(chanceBox);
   }else{
     body.append(el("div","mini","Hit-chance estimate unavailable or unverified."));
   }
   body.append(el("div","mini","Model-based probability only · not a verified betting edge."));
   card.append(body);board.append(card);
 }
}
async function refresh(){
 const status=byId("lagged-challenger-status");
 if(!status)return;
 try{
   const res=await fetch(SOURCE+"?v="+Date.now(),{cache:"no-store"});
   if(!res.ok)throw Error("Snapshot unavailable");
   render(await res.json());
 }catch(err){
   status.textContent="New-model feed unavailable. Existing AI board is still available.";
   byId("lagged-challenger-board")?.replaceChildren();
 }
}
document.addEventListener("DOMContentLoaded",()=>{
 refresh();
 setInterval(()=>{if(document.visibilityState==="visible")refresh();},90000);
 document.addEventListener("visibilitychange",()=>{
   if(document.visibilityState==="visible")refresh();
 });
});
})();
