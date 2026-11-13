const test=require("node:test"),assert=require("node:assert/strict"),fs=require("node:fs"),vm=require("node:vm");
const ctx={Intl,Date};vm.createContext(ctx);
vm.runInContext(fs.readFileSync("docs/dames-picks/feeds.js","utf8"),ctx);
const H=ctx.DamesPicksLineHistory,plain=v=>JSON.parse(JSON.stringify(v));
const form={log_fields:["date","opponent","PTS","REB","AST","PRA","MIN"],players:[
 {player:"Domantas Sabonis",player_id:"1627734",team:"SAC",log:[
  ["2026-10-21","LAC",14,18,8,40,34],["2026-10-23","POR",27,19,10,56,39],
  ["2026-11-02","DAL",9,7,4,20,31],["2026-11-06","SAS",17,12,5,34,31],
  ["2026-11-10","ORL",20,13,4,37,35]]}]};
const pick={sport:"NBA",playerId:"1627734",player:"Domantas Sabonis",team:"SAC",stat:"REB",line:12.5,
 start:"2026-11-11T03:00:00+00:00",form:{season:14.6}};
test("Only games before the pick's Eastern game date are included",()=>{
 const [r]=H.attachGameLogs([pick],form);
 assert.deepEqual(plain(r.logs.map(x=>x.date)),["2026-11-06","2026-11-02","2026-10-23","2026-10-21"]);
 assert.equal(r.form.historyGames,4);
});
test("Over under and push counts use this EXACT frozen standard line",()=>{
 const [r]=H.attachGameLogs([pick],form);
 assert.equal(r.form.over,2);assert.equal(r.form.under,2);assert.equal(r.form.push,0);
 const [q]=H.attachGameLogs([{...pick,line:12}],form);
 assert.equal(q.form.push,1);
});
test("Existing form fields are preserved",()=>assert.equal(H.attachGameLogs([pick],form)[0].form.season,14.6));
test("No log, wrong player, missing stat or NFL row is unchanged",()=>{
 const other={...pick,playerId:"999",player:"Someone Else"};
 assert.equal(H.attachGameLogs([other],form)[0].logs,undefined);
 assert.equal(H.attachGameLogs([{...pick,stat:"FG3M"}],form)[0].logs,undefined);
 const nfl={...pick,sport:"NFL"};assert.equal(H.attachGameLogs([nfl],form)[0],nfl);
 assert.equal(H.attachGameLogs([pick],{players:[]})[0],pick);
});
test("Ambiguous player names without an id are rejected",()=>{
 const dup={log_fields:form.log_fields,players:[{...form.players[0],player_id:"1"},{...form.players[0],player_id:"2"}]};
 assert.equal(H.attachGameLogs([{...pick,playerId:""}],dup)[0].logs,undefined);
});
test("Never join a player ID with the WRONG NBA team",()=>{
 const wrong={...pick,team:"LAL"};
 assert.equal(H.attachGameLogs([wrong],form)[0].logs,undefined);
});
