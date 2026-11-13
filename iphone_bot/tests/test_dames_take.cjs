const test=require("node:test"),assert=require("node:assert/strict"),fs=require("node:fs"),vm=require("node:vm");
const ctx={};vm.createContext(ctx);
vm.runInContext(fs.readFileSync("docs/dames-picks/dames_take.js","utf8"),ctx);
const t=ctx.DamesTake;
const pick=(side="MORE",more={})=>({sport:"NBA",player:"Example Guard",playerId:"1",
 game:"A @ B",gameId:"A @ B",start:"2026-11-11T00:00:00Z",stat:"PTS",
 source:"PrizePicks",line:27.5,projection:30.1,side,confidenceTier:undefined,
 chance:.64,captured:"2026-11-10T17:00:00Z",...more});
test("Player-facing takes use Over/Under and retain the surname before Jr.",()=>{
 for(const pool of Object.values(t.POOL))assert.ok(pool.every(s=>!/\b(?:more|less)\b/i.test(s)));
 const used=new Set(t.POOL.UNDER);
 const text=t.damesTake(pick("LESS",{player:"Christian Anderson Jr.",projection:24}),{usedOpeners:used});
 assert.match(text,/for Anderson PTS/);
 assert.doesNotMatch(text,/for Jr/);
});
test("At least 10 different non-corny openers exist for each of four tiers",()=>{
 for(const [tier,pool] of Object.entries(t.POOL)){
  assert.ok(pool.length>=10,tier);
  assert.equal(new Set(pool).size,pool.length,tier);
  assert.ok(pool.every(x=>!/[#\u{1F300}-\u{1FAFF}]/u.test(x)),tier);
 }
});
test("Only verified explicit model top tier may say lock",()=>{
 assert.equal(t.tierFor(pick()),"OVER");
 assert.equal(t.tierFor(pick("LESS",{projection:24.1})),"UNDER");
 assert.equal(t.tierFor(pick("MORE",{projection:27.8,chance:.52})),"THIN EDGE");
 assert.equal(t.tierFor(pick("MORE",{confidenceTier:"LOCK"})),"LOCK");
 assert.equal(t.tierFor(pick("MORE",{confidenceTier:"LOCK",projection:24})),"THIN EDGE");
});
test("One actual side-supporting stat and short group-chat voice",()=>{
 const s=t.damesTake(pick());
 assert.match(s,/We got him at 30\.1 on a 27\.5 line\./);
 assert.ok(s.trim().split(/\s+/).length<=20);
 assert.equal(s.split(". ").length,2);
});
test("Never cite over projection for an under and never invent a rank",()=>{
 const p=pick("LESS",{projection:25,opponentDefenseRank:undefined});
 const s=t.damesTake(p);
 assert.match(s,/We got him at 25 on a 27\.5 line\./);
 assert.doesNotMatch(s,/26th|defense|vs forwards/);
 const noEvidence=pick("LESS",{projection:31,form:{l5:32}});
 const only=t.damesTake(noEvidence);
 assert.doesNotMatch(only,/We got|Averaging|Under in/);
 assert.equal(only.trim().split(/\s+/).length<=20,true);
});
test("Recent performance is only used when verifiable and supports side",()=>{
 let p=pick("LESS",{projection:26,recentGames:[
  {actual:21},{actual:24},{actual:26},{actual:20},{actual:18}]});
 assert.match(t.support(p),/Under in 5 of his last 5\./);
 p=pick("MORE",{projection:null,form:{l5:31.2}});
 assert.equal(t.support(p),"Averaging 31.2 his last 5.");
 p=pick("LESS",{projection:null,recentGames:[{actual:35},{actual:null},{actual:12}]});
 assert.equal(t.support(p),null);
});
test("No evidence gives opener only; no pick gives no take",()=>{
 assert.equal(t.damesTake(pick("MORE",{projection:null,form:{}})).split(". ").length,1);
 assert.equal(t.damesTake(pick("MORE",{quoteOnly:true})),null);
 assert.equal(t.damesTake(pick(null,{projection:null,direction:null,side:null})),null);
});
test("Underdog and PrizePicks use same formatter and source-specific identities",()=>{
 const rows=[pick("MORE",{source:"PrizePicks"}),pick("MORE",{source:"Underdog"})];
 const maps=t.forSlate(rows);
 assert.equal(maps.size,2);
 assert.ok([...maps.values()].every(s=>s&&s.includes("27.5 line.")));
 assert.notEqual([...maps.values()][0].split(". ")[0],[...maps.values()][1].split(". ")[0]);
});
test("Identical slate always rotates uniquely and deterministically",()=>{
 const rows=Array.from({length:18},(_,i)=>pick("MORE",{player:"Player "+i,playerId:String(i),projection:31+i/10}));
 const first=[...t.forSlate(rows).values()],again=[...t.forSlate([...rows].reverse()).values()];
 assert.equal(new Set(first.map(x=>x.split(". ")[0])).size,18);
 assert.deepEqual(first,again);
 assert.ok(first.every(x=>x.split(/\s+/).length<=20));
});
test("No sportsbook is guessed when its prop feed is absent",()=>{
 const html=fs.readFileSync("docs/dames-picks/index.html","utf8");
 assert.match(html, /src="dames_take[.]js[?]bundle=[^"]+"/);
 assert.ok(html.includes("DamesTake.forSlate"));
 assert.ok(html.includes("No verified model lean for this line."));
});
