/* Dame's Take: deterministic, auditable copy from saved NBA/NFL player props.
 * No fetches, no invented supporting statistics or implicit guaranteed locks.
 * Works with PrizePicks and Underdog records using the same pick contract.
 */
(function(root){
"use strict";
const POOL={
 LOCK:[
  "Line looking light tonight","He been right there lately","This number ain't keeping up",
  "The model likes this spot","This the one the model likes","The gap says plenty",
  "He got room on this line","This one stands out on paper","The numbers been talking",
  "That line looking behind","No need to force this one","The model seeing a gap",
  "This the strongest look here","He got a clean number","That projection says enough",
  "This is the top look","The numbers favor this","This one got the best read"
 ],
 OVER:[
  "He been getting to it","This number looking light","Bro got room to clear",
  "They set this one low","His numbers sitting higher","That line ain't caught up",
  "I like the more here","He got some space on this","This over got a case",
  "He been above this pace","That's a reachable number","He can get past that",
  "The model got him higher","This side looking better","There's room on the over",
  "More makes sense here","I see him clearing","Not sold on that low line"
 ],
 UNDER:[
  "They asking too much","That number sitting high","He ain't been near that",
  "Less looking cleaner here","I don't love that line","This feels a little rich",
  "That line needs a lot","They got him too high","I see him staying below",
  "The model leaning less","That under got a case","His numbers sitting lower",
  "I ain't chasing that total","That's a heavy number","He gotta do too much",
  "Less makes sense here","They reaching with that line","I like the lower side"
 ],
 "THIN EDGE":[
  "It's a lean not a lock","I ain't all in here","This one real close",
  "Not enough to go crazy","Small edge at best","This one could swing",
  "I'm keeping this light","Wouldn't press this one","The gap ain't huge",
  "Not a strong read","This one needs caution","I'm not forcing it",
  "Slight lean that's it","Could go either way","It's close on paper",
  "Not much separation here","This one borderline","The edge looking thin"
 ]
};
const number=v=>v===null||v===undefined||v===""?null:Number.isFinite(Number(v))?Number(v):null;
const fmt=v=>Number(v).toFixed(1).replace(/\.0$/,"");
const sideOf=p=>({MORE:"MORE",OVER:"MORE",LESS:"LESS",UNDER:"LESS"}[String(p.side||p.direction||"").toUpperCase()]||null);
const validTier=t=>["LOCK","OVER","UNDER","THIN EDGE"].includes(t)?t:null;
const good=(value,line,side)=>side==="MORE"?value>line:value<line;
function tierFor(p){
 const side=sideOf(p),line=number(p.line),projection=number(p.projection),chance=number(p.chance);
 const explicit=validTier(String(p.tier||p.confidenceTier||p.gradeTier||"").toUpperCase().replace("_"," "));
 if(!side)return "THIN EDGE";
 // Only a bot-published top tier may be shown as LOCK; uncalibrated odds
 // must not be silently upgraded to a "sure thing".
 if(explicit==="LOCK" && line!==null && projection!==null && good(projection,line,side))return "LOCK";
 if(explicit==="THIN EDGE")return "THIN EDGE";
 if(explicit==="OVER"||explicit==="UNDER")return explicit===(side==="MORE"?"OVER":"UNDER")?explicit:"THIN EDGE";
 if(line===null||projection===null||!good(projection,line,side))return "THIN EDGE";
 const edge=Math.abs(projection-line)/Math.max(1,Math.abs(line));
 // This is merely a copywriting category, not a calibrated betting probability.
 return chance!==null&&chance>=.55&&chance<=1&&edge>=.04?(side==="MORE"?"OVER":"UNDER"):"THIN EDGE";
}
function support(p){
 const side=sideOf(p),line=number(p.line),proj=number(p.projection);
 if(!side||line===null)return null;
 const candidates=[];
 // Source-proven recent outcomes can be counted only for the SAME stat/line
 // and only when 5 or 10 game-level actuals really exist.
 const logs=Array.isArray(p.recentGames)?p.recentGames:p.logs;
 if(Array.isArray(logs)){
  const vals=logs.map(g=>number(g?.actual));
  // Incomplete games must not shrink the sample and inflate a hit rate.
  if(vals.length>=5 && vals.every(v=>v!==null&&v>=0)){
   const last=vals.slice(-Math.min(vals.length,10));
   const hits=last.filter(v=>good(v,line,side)).length;
   if(hits>=Math.ceil(.7*last.length)){
    candidates.push({score:5+hits/last.length,text:(side==="MORE"?"Over":"Under")+" in "+hits+" of his last "+last.length+"."});
   }
  }
 }
 // NFL source records are computed against their stored line; never claim
 // they're about a repriced line unless the source says so.
 const f=p.form||{};
 if(p.lineStatsVerified===true){
  const wins=number(side==="MORE"?f.last5Over:f.last5Under);
  const games=number(f.last5Games);
  if(wins!==null&&games===5&&wins>=4&&wins<=5)
   candidates.push({score:6,text:(side==="MORE"?"Over":"Under")+" in "+wins+" of his last 5."});
 }
 const l5=number(f.l5 ?? p.last5Average);
 if(l5!==null&&l5>=0&&good(l5,line,side))
  candidates.push({score:3+Math.min(1,Math.abs(l5-line)/Math.max(1,line)),text:"Averaging "+fmt(l5)+" his last 5."});
 if(proj!==null&&proj>=0&&good(proj,line,side))
  candidates.push({score:4+Math.min(1,Math.abs(proj-line)/Math.max(1,line)),text:"We got him at "+fmt(proj)+" on a "+fmt(line)+" line."});
 const rank=number(p.opponentDefenseRank),position=p.position;
 if(rank!==null&&Number.isInteger(rank)&&rank>=1&&rank<=32&&position&&
    ((side==="MORE"&&rank>=25)||(side==="LESS"&&rank<=8)))
  candidates.push({score:2,text:String(p.opponent||"Opponent")+" "+rank+(rank%10===1&&rank!==11?"st":rank%10===2&&rank!==12?"nd":rank%10===3&&rank!==13?"rd":"th")+" vs "+position+"."});
 // An explicit, verified usage change with known teammate context only.
 const usage=p.verifiedUsage;
 if(usage?.verified===true&&number(usage.minutesNow)!==null&&
    number(usage.minutesBefore)!==null&&
    ((side==="MORE"&&usage.minutesNow>usage.minutesBefore)||
     (side==="LESS"&&usage.minutesNow<usage.minutesBefore))&&
    /^[a-z .'-]{2,35}$/i.test(String(usage.reason||"")))
  candidates.push({score:4.5,text:(side==="MORE"?"Up":"Down")+" to "+fmt(usage.minutesNow)+" minutes with "+usage.reason+"."});
 candidates.sort((a,b)=>b.score-a.score||a.text.localeCompare(b.text));
 return candidates[0]?.text||null;
}
function hash(input){
 let h=2166136261;
 for(const ch of String(input)){h=Math.imul(h^ch.charCodeAt(0),16777619)}
 return h>>>0;
}
function openingFor(p,tier,used=new Set()){
 const pool=POOL[tier],seed=[p.sport,p.start,p.player,p.stat,p.line,p.source||p.provider||"",tier].join("|");
 const start=hash(seed)%pool.length;
 for(let i=0;i<pool.length;i++){
  const text=pool[(start+i)%pool.length];
  if(!used.has(text)){used.add(text);return text}
 }
 // When a slate has more picks than the finite pool, disambiguate by player
 // and stat without claiming any new metric.
 const who=String(p.player||"this player").split(" ").slice(-1)[0];
 const stat=String(p.stat||"this stat");
 const base=pool[start]+" for "+who+" "+stat;
 let text=base;
 if(used.has(text))text=base+" at "+fmt(number(p.line)??0);
 if(used.has(text))text=base+" on "+String(p.source||p.provider||"the board");
 let index=2;
 while(used.has(text)){text=base+" look "+index;index++}
 used.add(text);return text;
}
function damesTake(p,options={}){
 if(!p||p.quoteOnly||!sideOf(p))return null; // no AI pick, no invented take
 const tier=tierFor(p),opening=openingFor(p,tier,options.usedOpeners);
 const stat=support(p);
 const count=s=>s.trim().split(/\s+/).length;
 let result=opening+". "+(stat||"");
 if(count(result)>20)result=opening+".";
 return result.trim();
}
function forSlate(rows){
 const bySlate=new Map(),out=new Map();
 // Deterministic order across re-renders, bookmakers, reloads and browsers.
 const sorted=[...rows].sort((a,b)=>{
  const k=p=>[p.sport,p.start,p.source||p.provider||"",p.gameId||p.game,p.playerId||p.player,p.stat,p.line,p.captured].join("|");
  return k(a).localeCompare(k(b));
 });
 for(const p of sorted){
  const time=Date.parse(p.start);
  const day=Number.isFinite(time)?new Intl.DateTimeFormat("en-CA",{timeZone:"America/New_York",year:"numeric",month:"2-digit",day:"2-digit"}).format(new Date(time)):String(p.start||"").slice(0,10);
  const slate=[p.sport,day].join("|");
  if(!bySlate.has(slate))bySlate.set(slate,new Set());
  const ident=[p.sport,p.start,p.gameId||p.game,p.playerId||p.player,p.stat,p.line,p.captured,p.source||p.provider||""].join("|");
  out.set(ident,damesTake(p,{usedOpeners:bySlate.get(slate)}));
 }
 return out;
}
root.DamesTake={POOL,tierFor,support,damesTake,forSlate};
})(typeof window!=="undefined"?window:globalThis);

/* Runtime execution identity: fail closed if any cached asset predates this release. */
globalThis.__damesRunningAssets=globalThis.__damesRunningAssets||Object.create(null);
globalThis.__damesRunningAssets["dames_take.js"]="dp-final-boxscore-20261113-r32";
