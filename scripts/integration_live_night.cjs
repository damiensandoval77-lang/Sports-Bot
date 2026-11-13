// Read-only live-night production check. Uses deployed app code + real
// published artifacts + ESPN. Never fabricates scores, grades or lines.
const vm=require("node:vm");
const SITE=(process.argv[2]||"https://damiensandoval77-lang.github.io/Sports-Bot").replace(/\/$/,"");
const fetchJSON=async p=>{
 const response=await fetch(SITE+"/"+p+"?v="+Date.now(),{cache:"no-store"});
 if(!response.ok)throw Error(p+" HTTP "+response.status);
 return response.json();
};
const fetchText=async p=>{
 const response=await fetch(SITE+"/"+p+"?v="+Date.now(),{cache:"no-store"});
 if(!response.ok)throw Error(p+" HTTP "+response.status);
 return response.text();
};
function validateActivation(html){
 const sources=[...html.matchAll(/<script\b[^>]*\bsrc=["']([^"']+)["'][^>]*>/gi)]
  .map(x=>new URL(x[1],SITE+"/dames-picks/").pathname);
 if(!sources.includes(new URL(SITE+"/dames-picks/live_direct.js").pathname)||
    !html.includes('L.mergeScores(')||!html.includes('liveTick('))
  throw Error("Deployed page has not activated browser-direct ESPN live polling");
}
function verifyLiveObservation(score,observed,row){
 const failures=[];
 if(!observed?.player_rows?.length)failures.push(score.game+": no verified live player summary");
 if(row.fixed_card_score!==row.espn_score)failures.push(score.game+": score differs from verified ESPN observation");
 if(row.fixed_live_attached!==row.picks_with_player_in_box)
  failures.push(score.game+": missing attached verified player totals");
 return failures;
}
module.exports={validateActivation,verifyLiveObservation};
if(require.main===module)(async()=>{
 const now=Date.now();
 const [html,feeds,liveCode,ledger,form,legacy,schedule,oldScores,indep]=await Promise.all([
 "dames-picks/index.html","dames-picks/feeds.js","dames-picks/live_direct.js"
 ].map(fetchText).concat([
 "lagged_matchup_all_market_ledger.json","current_form.json",
 "live_player_tracking.json","nba_schedule.json","nba_scoreboard_independent.json",
 "nba_player_tracking_independent.json"
 ].map(fetchJSON)));
 validateActivation(html);
 const ctx={Intl,Date,AbortController,setTimeout,clearTimeout,fetch};
 vm.createContext(ctx);
 vm.runInContext(feeds,ctx);
 vm.runInContext(liveCode,ctx);
 const m=ctx.DamesPicksModel,L=ctx.DamesPicksLive;
 if(!m||!L||typeof L.fetchNBA!=="function")throw Error("Deployed live layer missing");
 const snapshot=m.preferredNBALiveFeed(legacy,indep,now);
 const direct=await L.fetchNBA({fetch,now});
 if(!direct)throw Error("ESPN direct scoreboard unavailable; browser may also be blocked");
 const picks=m.nba(ledger,form);
 const before={games:m.gameCatalog(snapshot,null,schedule,null,now,oldScores),
               picks:m.attachLive(picks,snapshot,null,now)};
 const withDirect=L.mergeFeeds(snapshot,direct.feed,now);
 const withScores=L.mergeScores(oldScores,direct.board,now);
 const after={games:m.gameCatalog(withDirect,null,schedule,null,now,withScores),
              picks:m.attachLive(picks,withDirect,null,now)};
 const live=direct.board.games.filter(g=>g.game_state==="in");
 const normalize=v=>String(v||"").normalize("NFKD").replace(/[\u0300-\u036f]/g,"").toLowerCase();
 const report={checked_at:new Date(now).toISOString(),site:SITE,
  snapshot_age_min:{legacy:Math.round((now-Date.parse(legacy.captured_at))/60000),
   independent:Math.round((now-Date.parse(indep.captured_at))/60000),
   scoreboard:Math.round((now-Date.parse(oldScores.generated_at))/60000)},
  in_progress:live.map(g=>g.game),direct_errors:direct.feed.errors,
  games:[],failures:[]};
 for(const score of live){
  const observed=direct.feed.games.find(g=>g.game===score.game);
  const livePlayers=new Set((observed?.player_rows||[]).map(p=>m.nbaTeam(p.team)+"|"+normalize(p.player)));
  const pending=arr=>arr.filter(p=>p.game===score.game&&p.grade==="PENDING");
  const eligible=pending(after.picks).filter(p=>livePlayers.has(m.nbaTeam(p.team)+"|"+normalize(p.player)));
  const first=before.games.find(x=>x.game===score.game),newest=after.games.find(x=>x.game===score.game);
  const scoreValue=g=>g&&g.awayScore!=null&&g.homeScore!=null?g.awayScore+"-"+g.homeScore:"MISSING";
  const row={game:score.game,espn_score:score.away_score+"-"+score.home_score,
   production_card_score:scoreValue(first),fixed_card_score:scoreValue(newest),
   pending_frozen_picks:pending(after.picks).length,
   picks_with_player_in_box:eligible.length,
   production_live_attached:pending(before.picks).filter(p=>p.live).length,
   fixed_live_attached:eligible.filter(p=>p.live).length,
   teams_missing_live:[...new Set(eligible.filter(p=>!p.live).map(p=>p.team))]};
  report.games.push(row);
  report.failures.push(...verifyLiveObservation(score,observed,row));
 }
 console.log(JSON.stringify(report,null,2));
 if(report.failures.length)process.exit(1);
 if(!live.length)console.log("NO_LIVE_GAMES: no live-period verification claimed");
})().catch(e=>{console.error("LIVE_INTEGRATION_FAILED",e.message);process.exit(2)});
