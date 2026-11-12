const test=require("node:test"),assert=require("node:assert/strict"),fs=require("node:fs"),vm=require("node:vm");
const ctx={Intl,Date};ctx.globalThis=ctx;vm.createContext(ctx);
vm.runInContext("globalThis.__damesRunningAssets={};",ctx);
vm.runInContext(fs.readFileSync("docs/dames-picks/feeds.js","utf8"),ctx);
const C=ctx.DamesPicksCoverage,NOW=Date.parse("2026-11-11T23:00:00Z");
const sched={games:[{game:"A @ B",start:"2026-11-12T00:00:00+00:00",game_state:"pre"},
{game:"C @ D",start:"2026-11-12T03:00:00+00:00",game_state:"pre"},
{game:"E @ F",start:"2026-11-11T00:00:00+00:00",game_state:"post"}]};
test("near-tip game lacking saved predictions is disclosed",()=>{
 const result=C.tonight(sched,[{sport:"NBA",game:"C @ D",start:"2026-11-12T03:00:00+00:00"}],NOW);
 assert.equal(result.missing.length,1);assert.equal(result.alert,true);
 assert.match(C.message(result,()=>"7:00 PM"),/No saved picks yet for 1 of 2 upcoming games/);
});
test("covered slate does not show a false alarm",()=>{
 const rows=sched.games.map(g=>({sport:"NBA",game:g.game,start:g.start,projection:22.3,direction:"MORE",quoteOnly:false}));
 const result=C.tonight(sched,rows,NOW);assert.equal(result.alert,false);
});
test("an authentic archived line without a frozen model does not count as a saved pick",()=>{
 const onlyQuote={sport:"NBA",game:"A @ B",start:"2026-11-12T00:00:00+00:00",
   line:20.5,projection:null,direction:null,quoteOnly:true};
 const modeled={sport:"NBA",game:"C @ D",start:"2026-11-12T03:00:00+00:00",
   line:20.5,projection:23.1,direction:"MORE",quoteOnly:false};
 const result=C.tonight(sched,[onlyQuote,modeled],NOW);
 assert.equal(result.missing.length,1);
 assert.ok(result.missing.includes("A @ B"));
 assert.equal(result.alert,true);
});
test("a projection without a verified Over/Under direction is not a saved model pick",()=>{
 const noSide={sport:"NBA",game:"A @ B",start:"2026-11-12T00:00:00+00:00",
   projection:25.1,direction:null,quoteOnly:false};
 const result=C.tonight({games:[sched.games[0]]},[noSide],NOW);
 assert.equal(result.covered,0);
 assert.equal(result.alert,true);
});
test("past pick from identical matchup does not satisfy new date",()=>{
 const result=C.tonight(sched,[{sport:"NBA",game:"A @ B",start:"2026-10-01T00:00:00+00:00"}],NOW);
 assert.ok(result.missing.includes("A @ B"));
});
test("missing picks beyond three hours before tip not alarming",()=>{
 const result=C.tonight({games:[sched.games[1]]},[],NOW);assert.equal(result.alert,false);
});
