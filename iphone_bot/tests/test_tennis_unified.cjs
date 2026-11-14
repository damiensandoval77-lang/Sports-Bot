const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const html=fs.readFileSync('docs/dames-picks/index.html','utf8');
function setup(){
 const nodes={};const state={league:'TENNIS',mode:'board',nba:[{sport:'NBA'}],nfl:[{sport:'NFL'}],tennis:[],selected:new Set()};
 const ctx={state,window:{DamesPicksTennis:{tennis:()=>[]}},Date,Set,
 $:id=>nodes[id]||(nodes[id]={value:'',textContent:'',innerHTML:'',dataset:{},querySelectorAll:()=>[]}),
 m:{key:p=>p.id,displayCurrentPicks:p=>p,sortByHitEstimate:p=>p,sortByTeamPosition:p=>p},
 escapeText:s=>String(s),when:s=>s,fmt:s=>String(s),timestamp:Date.parse};
 vm.createContext(ctx);
 vm.runInContext(html.slice(html.indexOf('function rows(){'),html.indexOf('function cardOverUnder(')),ctx);
 vm.runInContext(html.slice(html.indexOf('function renderTennis(){'),html.indexOf('function sortLiveGamesCompat(')),ctx);
 return {ctx,state,nodes};
}
test('league mapping is explicit; absent tennis does not fall back to NFL',()=>{
 const {ctx,state}=setup();assert.equal(ctx.rows().length,0);
 state.league='NBA';assert.equal(ctx.rows(),state.nba);state.league='NFL';assert.equal(ctx.rows(),state.nfl);
 state.league='bogus';assert.equal(ctx.rows().length,0);
});
test('tennis quote-only card has no estimates, scores or implied grading',()=>{
 const {ctx,state,nodes}=setup();ctx.window.DamesPicksTennis.tennis=()=>[{id:'q',player:'Player',opponent:'Opponent',line:22.5,stat:'Total Games',source:'Provider',start:'future',quoteOnly:true,projection:null,standardSides:['more']}];
 ctx.renderTennis();assert.match(nodes.cards.innerHTML,/LINE ONLY/);assert.match(nodes.cards.innerHTML,/NO ESTIMATE/);
 assert.match(nodes.cards.innerHTML,/verified standard side: More/);assert.doesNotMatch(nodes.cards.innerHTML,/More \/ Less/);
 assert.equal(nodes.wl.textContent,'—');assert.equal(nodes.rate.textContent,'—');assert.equal(nodes.games.textContent,'—');
 ctx.renderTennisDetail({id:'q',standardSides:['more','less']});assert.match(nodes['detail-content'].innerHTML,/side at capture: More/);assert.doesNotMatch(nodes['detail-content'].innerHTML,/More \/ Less/);
 state.mode='live';ctx.renderTennis();assert.match(nodes.cards.innerHTML,/not connected/);assert.doesNotMatch(nodes.cards.innerHTML,/LINE ONLY/);
 state.mode='tracker';ctx.renderTennis();assert.match(nodes.cards.innerHTML,/not connected/);
});
test('expired or missing quote is withheld even in saved/detail views',()=>{
 const {ctx,state,nodes}=setup();state.mode='saved';ctx.renderTennis();assert.match(nodes.cards.innerHTML,/No saved tennis/);
 ctx.renderTennisDetail({id:'expired'});assert.match(nodes['detail-content'].innerHTML,/expired or the match started/);
});
test('feed load remains independently settled; periodic expiry and runtime checking are installed',()=>{
 assert.match(html,/finalPlayers,tennisBoard\]=await Promise.allSettled/);
 assert.match(html,/getJSON\("tennis_board.json"\)/);
 assert.match(html,/setInterval\(refreshTennisView,30000\)/);
 assert.match(html,/state.tennisFeed=tennisBoard.status==="fulfilled"\?tennisBoard.value:null/);
 assert.match(html,/"short_history.js","tennis.js"/);
});

test('Old cached tennis adapter cannot crash new side-aware HTML or invent sides',()=>{
 const {ctx,state,nodes}=setup();ctx.window.DamesPicksTennis.tennis=()=>[{id:'old',player:'Player',opponent:'Opponent',line:22.5}];
 ctx.renderTennis();assert.equal(ctx.rows().length,0);assert.match(nodes.coverage.textContent,/app files need an update/);assert.doesNotMatch(nodes.cards.innerHTML,/LINE ONLY/);
 ctx.renderTennisDetail({id:'old'});assert.match(nodes['detail-content'].innerHTML,/Quote unavailable/);
});
