/* Regression: NFL boxscore player and team labels must render as text. */
const fs=require("fs"),vm=require("vm"),assert=require("assert");
const html=fs.readFileSync("docs/nfl/index.html","utf8");
const script=html.split("<script>")[1].split("</script>")[0];
new vm.Script(script,{filename:"docs/nfl/index.html"});
const from=script.indexOf("function boxMetric(");
const to=script.indexOf("function renderFinalBoxscore(",from);
assert(from>=0&&to>from,"Boxscore table rendering functions missing");
const context={esc:(v)=>String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]))};
vm.createContext(context);
vm.runInContext(script.slice(from,to),context);
const player={player:"Jacoby Brissett",team:"ARI",position:"QB",
 attempts:37,completions:25,passing_yards:267,passing_tds:2,passing_interceptions:0};
assert.strictEqual(context.boxMetric(player,"player"),"Jacoby Brissett");
assert.strictEqual(context.boxMetric(player,"team"),"ARI");
assert.strictEqual(context.boxMetric(player,"position"),"QB");
assert.strictEqual(context.boxMetric(player,"passing_yards"),"267");
assert.strictEqual(context.boxMetric(player,"fumbles_lost"),"—");
const passing=context.gameStatsTable({players:[player]},"Passing");
assert(passing.includes("<td>Jacoby Brissett</td>"),"Player name missing from passing boxscore");
assert(passing.includes("<td>ARI</td>"),"Team name missing from passing boxscore");
assert(passing.includes("<td>267</td>"),"Passing stat missing");
const receiving=context.gameStatsTable({players:[{player:"Marvin Harrison Jr.",team:"ARI",targets:9,receptions:6,receiving_yards:90,receiving_tds:1}]},"Receiving");
assert(receiving.includes("Marvin Harrison Jr."),"Receiver name missing");
const rushing=context.gameStatsTable({players:[{player:"Jeremiyah Love",team:"ARI",carries:14,rushing_yards:77,rushing_tds:1}]},"Rushing");
assert(rushing.includes("Jeremiyah Love"),"Rusher name missing");
assert.strictEqual(context.boxMetric({player:"<script>alert(1)</script>"},"player"),"&lt;script&gt;alert(1)&lt;/script&gt;","Name must be escaped");
assert.strictEqual(context.boxMetric({player:null},"player"),"Unknown","Missing names cannot show numeric em dash");
console.log("NFL boxscore rendering OK: player names, teams, stats, XSS escaping, missing labels");
