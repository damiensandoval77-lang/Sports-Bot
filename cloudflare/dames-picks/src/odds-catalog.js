/**
 * The Odds API market catalog for Dame's Picks.
 *
 * Player props are MARKET QUOTES, not player statistics. No points, minutes,
 * usage, rebounds, injury or defense numbers are obtained from this catalog.
 * Reference: https://the-odds-api.com/sports-odds-data/betting-markets.html
 *
 * A documented market key does not guarantee a particular bookmaker will
 * offer it for every event. Alt _alternate markets are intentionally excluded.
 */
const groups = Object.freeze({
 NBA: {
   sport_key:"basketball_nba",
   core:[
     ["player_points","Points","PTS"],
     ["player_rebounds","Rebounds","REB"],
     ["player_assists","Assists","AST"],
     ["player_points_rebounds_assists","Points + rebounds + assists","PRA"]
   ],
   expanded:[
     ["player_threes","Three-pointers made","3PM"],
     ["player_steals","Steals","STL"],
     ["player_blocks","Blocks","BLK"],
     ["player_turnovers","Turnovers","TOV"],
     ["player_points_rebounds","Points + rebounds","PR"],
     ["player_points_assists","Points + assists","PA"],
     ["player_rebounds_assists","Rebounds + assists","RA"],
     ["player_blocks_steals","Blocks + steals","SB"],
     ["player_field_goals","Field goals made","FGM"],
     ["player_frees_made","Free throws made","FTM"],
     ["player_frees_attempts","Free throws attempted","FTA"],
     ["player_fantasy_points","Fantasy score","FPTS"],
     ["player_points_q1","First quarter points","PTS_Q1"],
     ["player_rebounds_q1","First quarter rebounds","REB_Q1"],
     ["player_assists_q1","First quarter assists","AST_Q1"]
   ],
   milestones:[
     ["player_double_double","Double-double","DOUBLE_DOUBLE"],
     ["player_triple_double","Triple-double","TRIPLE_DOUBLE"]
   ]
 },
 NFL:{
   sport_key:"americanfootball_nfl",
   core:[
     ["player_receptions","Receptions","REC"],
     ["player_reception_yds","Receiving yards","REC_YDS"],
     ["player_rush_yds","Rushing yards","RUSH_YDS"],
     ["player_pass_yds","Passing yards","PASS_YDS"],
     ["player_pass_tds","Passing touchdowns","PASS_TD"]
   ],
   expanded:[
     ["player_pass_attempts","Pass attempts","PASS_ATT"],
     ["player_pass_completions","Completions","PASS_CMP"],
     ["player_pass_interceptions","Interceptions thrown","PASS_INT"],
     ["player_rush_attempts","Rushing attempts","RUSH_ATT"],
     ["player_reception_tds","Receiving touchdowns","REC_TD"],
     ["player_rush_tds","Rushing touchdowns","RUSH_TD"],
     ["player_pass_rush_yds","Passing + rushing yards","PASS_RUSH_YDS"],
     ["player_rush_reception_yds","Rushing + receiving yards","RUSH_REC_YDS"],
     ["player_pass_rush_reception_yds","Passing + rushing + receiving yards","PASS_RUSH_REC_YDS"],
     ["player_rush_reception_tds","Rushing + receiving TDs","RUSH_REC_TDS"],
     ["player_pass_rush_reception_tds","Passing + rushing + receiving TDs","PASS_RUSH_REC_TDS"],
     ["player_reception_longest","Longest reception","REC_LONG"],
     ["player_rush_longest","Longest run","RUSH_LONG"],
     ["player_pass_longest_completion","Longest completion","PASS_LONG"],
     ["player_sacks","Sacks","SACKS"],
     ["player_solo_tackles","Solo tackles","SOLO_TACKLES"],
     ["player_tackles_assists","Tackles + assists","TACKLES_AST"],
     ["player_kicking_points","Kicking points","KICK_PTS"]
   ],
   milestones:[
     ["player_anytime_td","Anytime touchdown scorer","ANYTIME_TD"]
   ]
 }
});
const freezeCatalog=Object.fromEntries(Object.entries(groups).map(([league,group])=>{
 const markets=[...group.core.map(([key,label,stat])=>({key,label,stat,tier:"core",bet_type:"over_under"})),
  ...group.expanded.map(([key,label,stat])=>({key,label,stat,tier:"expanded",bet_type:"over_under"})),
  ...group.milestones.map(([key,label,stat])=>({key,label,stat,tier:"milestone",bet_type:"yes_no"}))];
 if(new Set(markets.map(x=>x.key)).size!==markets.length)throw Error("Duplicate market in "+league);
 return [league,Object.freeze({league,sport_key:group.sport_key,markets:Object.freeze(markets.map(Object.freeze))})];
}));
export const MARKET_CATALOG=Object.freeze(freezeCatalog);
export const BOOKMAKERS=Object.freeze(["prizepicks","underdog","fanduel","draftkings"]);
export const DFS_BOOKMAKERS=Object.freeze(["prizepicks","underdog"]);
export const CORE_MARKET_KEYS=Object.freeze(Object.fromEntries(Object.entries(MARKET_CATALOG).map(([k,v])=>[k,Object.freeze(v.markets.filter(m=>m.tier==="core").map(m=>m.key))])));
export function catalogFor(league){
 const l=String(league||"").toUpperCase();
 return MARKET_CATALOG[l]||null;
}
export function isStandardPlayerMarket(league,key){
 const market=catalogFor(league)?.markets.find(x=>x.key===key);
 return Boolean(market&&market.bet_type==="over_under"&&!key.includes("_alternate"));
}
export function marketTier(league,key){
 return catalogFor(league)?.markets.find(x=>x.key===key)?.tier||null;
}
export function apiCatalog(){
 return {source:"The Odds API v4 documentation (not live bookmaker availability)",
  availability:"requires real event/bookmaker response",
  provider_use:"odds and prop lines, NOT measured player game statistics",
  providers:BOOKMAKERS,
  standard_only:true,
  alternate_markets_excluded:true,
  leagues:Object.fromEntries(Object.entries(MARKET_CATALOG).map(([k,v])=>[k,{sport_key:v.sport_key,markets:v.markets}]))
 };
}
