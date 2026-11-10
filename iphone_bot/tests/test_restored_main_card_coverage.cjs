const test=require("node:test"),assert=require("node:assert/strict"),fs=require("node:fs"),vm=require("node:vm");
const html=fs.readFileSync("docs/index.html","utf8");
const now=Date.parse("2026-11-09T23:10:00Z");
const game=(name,home,away,start="2026-11-10T00:00:00Z")=>({
  game:name,home_abbreviation:home,away_abbreviation:away,
  start,game_state:"pre",date_eastern:"2026-11-09"
});
const eight=[
 game("Cleveland Cavaliers @ Charlotte Hornets","CHA","CLE"),
 game("Los Angeles Lakers @ Atlanta Hawks","ATL","LAL"),
 game("Washington Wizards @ Detroit Pistons","DET","WAS"),
 game("Memphis Grizzlies @ Toronto Raptors","TOR","MEM"),
 game("Denver Nuggets @ Houston Rockets","HOU","DEN","2026-11-10T01:30:00Z"),
 game("Indiana Pacers @ Dallas Mavericks","DAL","IND"),
 game("San Antonio Spurs @ Phoenix Suns","PHX","SAS"),
 game("New Orleans Pelicans @ Golden State Warriors","GSW","NOP")
];
const norm=x=>String(x||"").normalize("NFKD").toLowerCase().replace(/[\u0300-\u036f]/g,"").replace(/[^a-z0-9]/g,"");
function sourceFunction(name){
 const start=html.indexOf("function "+name+"(");
 assert.ok(start>=0,"Missing "+name);
 const end=html.indexOf("\nfunction ",start+9);
 assert.ok(end>start,"Missing next function boundary for "+name);
 return html.slice(start,end);
}
function setup(extra={}){
 const context={Date,Map,Set,Number,Math,String,Array,Boolean,norm,...extra};
 vm.createContext(context);
 for(const name of ["verifiedStandardLineCoverage","verifiedBoardStandardLineCoverage","injuryCardStatus","injuryPendingCard","safeLineOnly"])
   vm.runInContext(sourceFunction(name),context);
 return context;
}
function offer(g,idx,side,line=20.5,tier="standard"){
 return {player:"Test Player "+idx,team:g.away_abbreviation,
  stat:"Points",game:g.game,start:g.start,
  market_updated:"2026-11-09T23:00:00Z",line,direction:side,pickem_tier:tier};
}
test("Eight scheduled games retain independently verified two-sided standard lines",()=>{
 const picks=eight.flatMap((g,i)=>[offer(g,i,"More"),offer(g,i,"Less"),
    offer(g,i,"More",15.5,"goblin"),offer(g,i,"Less",30.5,"demon")]);
 const source={status:"FRESH_AUTHENTIC_PRIZEPICKS_LINES",source:"AUTHENTIC_PRIZEPICKS_PICKEM_NO_ODDS",
   is_live:true,updated_at:"2026-11-09T23:03:00Z",picks};
 const ctx=setup(),rows=ctx.verifiedStandardLineCoverage(source,{games:eight},now);
 assert.equal(rows.length,8);
 assert.equal(new Set(rows.map(x=>x.game)).size,8);
 assert.ok(rows.every(x=>x.line===20.5&&x.line_only&&x.projection===null&&x.estimated_hit_chance===null));
});
test("Conflicting standard thresholds, one-sided, and stale source fail closed",()=>{
 const g=eight[0],ctx=setup(),base={status:"FRESH_AUTHENTIC_PRIZEPICKS_LINES",
  source:"AUTHENTIC_PRIZEPICKS_PICKEM_NO_ODDS",is_live:true,
  updated_at:"2026-11-09T23:03:00Z"};
 assert.equal(ctx.verifiedStandardLineCoverage({...base,picks:[offer(g,0,"More")]},{games:eight},now).length,0);
 assert.equal(ctx.verifiedStandardLineCoverage({...base,picks:[
   offer(g,0,"More"),offer(g,0,"Less"),offer(g,0,"More",21.5)]},{games:eight},now).length,0);
 assert.equal(ctx.verifiedStandardLineCoverage({...base,updated_at:"2026-11-09T10:00:00Z",
   picks:[offer(g,0,"More"),offer(g,0,"Less")]},{games:eight},now).length,0);
});
test("One official OUT affects only the correct game, not entire slate",()=>{
 const status={player:"Austin Reaves",team:"LAL",player_id:"1630559",
    game_date:"2026-11-09",status:"OUT",official:true,
    source:"OFFICIAL_NBA_REPORT",reported_at:"2026-11-09T23:00:00Z"};
 const context=setup({
   officialInjuryFeed:{status:"OFFICIAL_NBA_REPORT_VERIFIED",injury_data_verified:true,
     players:[status]},nbaSchedule:{games:eight},
   validatedOutNews:()=>[],verifiedFreeOfficialOut:()=>[status],
   easternGameDay:()=> "2026-11-09",
   newModelForCard:()=>null
 });
 const reaves={player:"Austin Reaves",team:"LAL",game:eight[1].game,start:eight[1].start};
 const teammate={...reaves,player:"LeBron James"};
 const spurs={player:"Victor Wembanyama",team:"SAS",game:eight[6].game,start:eight[6].start};
 assert.equal(context.injuryCardStatus(reaves),"OUT");
 assert.equal(context.injuryCardStatus(teammate),"PENDING_INJURY_REMODEL");
 assert.equal(context.injuryCardStatus(spurs),"CLEAR");
});
test("Affected card becomes real-line only with no fabricated projection/lean",()=>{
 const ctx=setup();
 const row=ctx.safeLineOnly({player:"LeBron James",line:24.5,projection:26.2,
    combined_projection:25.8,estimated_hit_chance:{modeled_selected_probability:.7}},
    "INJURY_REMODEL_PENDING");
 assert.equal(row.line,24.5);
 assert.equal(row.projection,null);
 assert.equal(row.combined_projection,null);
 assert.equal(row.estimated_hit_chance,null);
 assert.equal(row.line_only,true);
 assert.deepEqual(Array.from(row.books),[]);
 assert.deepEqual(Array.from(row.book_quotes),[]);
 assert.deepEqual(Array.from(row.alternative_lines),[24.5]);
 assert.ok(html.includes('const projected=p.line_only?NaN:'));
 assert.ok(html.includes('const side=p.line_only?"NO LEAN":primaryDirection(p);'));
});
test("Verified line-only card returns safely before bookmaker-only details",()=>{
 const start=html.indexOf("const list=entries.slice(0,selectedGame?");
 const safe=html.indexOf("if(p.line_only){",start);
 const books=html.indexOf("p.books.length",start);
 assert.ok(start>0&&safe>start&&books>safe);
 const fast=html.slice(safe,books);
 assert.ok(fast.includes("return card;"));
 assert.ok(fast.includes('["NEW AI PROJECTION","—"'));
 assert.ok(fast.includes('["NEW AI CHANCE","—"'));
 assert.ok(fast.includes("injury-aware new AI pending"));
});
test("Opening missing-AI games does not force sportsbook when verified standard exists",()=>{
 assert.ok(html.includes('!standardLineCards.some(x=>x.game===game)'));
 assert.ok(html.includes('const quoteOnly=standardLineCards.filter('));
 assert.ok(html.includes('const liveStandardMode=standardLineCards.length>0;'));
});

test("Provider-board backup rescues genuine upcoming standard line when derived feed is missing",()=>{
 const ctx=setup(),g=eight[4];
 const row={id:"pp_123",player:"Test Player",team:"DEN",game:g.game,stat:"PTS",
  line:10.5,starts_at:g.start,observed_at:"2026-11-09T23:05:00Z",
  more_tier:"standard",less_tier:"standard",source:"independent_prizepicksapi_com",is_demo:false};
 const provider={status:"LIVE_THIRD_PARTY_PRIZEPICKS_LINES",
  source:"independent_prizepicksapi_com",generated_at:"2026-11-09T23:08:00Z",
  board_offers:[row]};
 const out=ctx.verifiedBoardStandardLineCoverage(provider,{games:eight},now);
 assert.equal(out.length,1);
 assert.equal(out[0].line,10.5);
 assert.equal(out[0].game,g.game);
 assert.equal(out[0].line_only,true);
 assert.equal(out[0].projection,null);
 assert.equal(out[0].estimated_hit_chance,null);
});
test("Provider-board fallback rejects stale, alternate, mismatched and started games",()=>{
 const ctx=setup(),g=eight[4],base={id:"pp_123",player:"Test Player",
   team:"DEN",game:g.game,stat:"PTS",line:10.5,starts_at:g.start,
   observed_at:"2026-11-09T23:05:00Z",more_tier:"standard",less_tier:"standard",
   source:"independent_prizepicksapi_com",is_demo:false};
 const provider={status:"LIVE_THIRD_PARTY_PRIZEPICKS_LINES",
   source:"independent_prizepicksapi_com",generated_at:"2026-11-09T23:08:00Z",
   board_offers:[base]};
 const verify=(feed,at=now)=>ctx.verifiedBoardStandardLineCoverage(feed,{games:eight},at).length;
 assert.equal(verify({...provider,generated_at:"2026-11-09T20:00:00Z"}),0);
 assert.equal(verify({...provider,board_offers:[{...base,more_tier:"goblin"}]}),0);
 assert.equal(verify({...provider,board_offers:[{...base,team:"LAL"}]}),0);
 assert.equal(verify({...provider,board_offers:[{...base,source:"unverified"}]}),0);
 assert.equal(verify({...provider,board_offers:[{...base,observed_at:"2026-11-09T19:00:00Z"}]}),0);
 assert.equal(verify({...provider,board_offers:[base,{...base,id:"pp_124",line:11.5}]}),0);
 assert.equal(verify(provider,Date.parse("2026-11-10T02:00:00Z")),0);
});
test("Main NBA board merges independent verified provider standard-line fallback",()=>{
 assert.ok(html.includes("verifiedBoardStandardLineCoverage(pp.value"));
 assert.ok(html.includes("standardLineCards=[...canonical.values()]"));
 assert.ok(html.includes("const quoteOnly=standardLineCards.filter("));
});

test("Dashboard distinguishes historical independently settled PrizePicks markets from today's pending AI and New AI",()=>{
 assert.ok(html.includes('id="verified-grade-reconciliation"'));
 assert.ok(html.includes('function refreshGradeReconciliation('));
 assert.ok(html.includes('history.independent_settled_center_lines'));
 assert.ok(html.includes('ai_forecast_today_grade_status.json'));
 assert.ok(html.includes('lagged_matchup_all_market_ledger.json'));
 assert.ok(html.includes('frozen_baseline_pregame_line_grades.json'));
 assert.ok(html.includes('Pending is NOT a loss.'));
 assert.ok(html.includes('research only, not placed bets'));
});
