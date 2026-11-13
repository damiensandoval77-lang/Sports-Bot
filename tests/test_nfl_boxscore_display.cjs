/* Exercise the actual unified game detail renderer, not retired NFL redirect. */
const fs=require("fs"),vm=require("vm"),assert=require("assert");
const html=fs.readFileSync("docs/dames-picks/index.html","utf8");
const from=html.indexOf("function renderGameDetail(){");
const to=html.indexOf("function ",from+10);
assert(from>=0&&to>from,"Unified game detail renderer missing");
const elements={};
const escapeText=v=>String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const context={escapeText,fmt:String,when:String,scoreText:String,rows:()=>[],
 m:{displayCurrentPicks:x=>x,sortByTeamPosition:x=>x},state:{gamePicked:{sport:"NFL",gameId:"g",game:"ARI @ SEA",statusText:"Final",players:[
 {player:"Jacoby Brissett",team:"ARI",stats:{PASS_YDS:267}},
 {player:"Marvin Harrison Jr.",team:"ARI",stats:{REC_YDS:90}},
 {player:"Jeremiyah Love",team:"ARI",stats:{RUSH_YDS:77}},
 {player:"<script>alert(1)</script>",team:"SEA",stats:{REC_YDS:10}}]}},
 $:id=>elements[id]||(elements[id]={querySelectorAll:()=>[]})};
vm.createContext(context);vm.runInContext(html.slice(from,to),context);
context.renderGameDetail();const rendered=elements["detail-content"].innerHTML;
for(const text of ["Jacoby Brissett","Marvin Harrison Jr.","Jeremiyah Love","ARI","PASS_YDS 267","REC_YDS 90","RUSH_YDS 77"])
 assert(rendered.includes(text),"Missing rendered NFL player/stat: "+text);
assert(rendered.includes("&lt;script&gt;alert(1)&lt;/script&gt;"));
assert(!rendered.includes("<script>"));
assert(rendered.includes("No verified pregame standard quotes"));
console.log("Unified NFL boxscore labels, stats, empty capture disclosure and escaping verified");
