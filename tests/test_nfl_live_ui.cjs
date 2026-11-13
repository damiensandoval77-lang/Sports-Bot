/* Exercise the real NFL redirect and unified app, not the retired dashboard.
 * Local runs use checked-in feeds only. Hosted runs never inject data.
 */
const { chromium } = require('playwright');
const fs = require('node:fs');
const assert = require('node:assert/strict');
const url = process.env.NFL_UI_URL || 'http://127.0.0.1:8765/nfl/';
const isLive = url.startsWith('https://');
const requireDeployed = isLive && process.env.NFL_REQUIRE_DEPLOYED_VERSION === 'true';
const output = process.env.NFL_SCREENSHOT_DIR || 'nfl-ui-artifacts';
const expectedRelease = JSON.parse(fs.readFileSync('docs/dames-picks/release.json','utf8')).release_id;
fs.mkdirSync(output,{recursive:true});

async function ensurePublished(){
 if(!requireDeployed)return;
 const releaseURL=new URL('../dames-picks/release.json',url.endsWith('/')?url:url+'/');
 for(let attempt=0;attempt<40;attempt++){
  try{const r=await fetch(releaseURL+'?v='+Date.now(),{cache:'no-store'});if(r.ok&&(await r.json()).release_id===expectedRelease)return;}catch(_){}
  if(attempt<39)await new Promise(resolve=>setTimeout(resolve,12000));
 }
 throw Error('Hosted release has not converged to '+expectedRelease);
}
async function verify(browser,name,viewport){
 const page=await browser.newPage({viewport,deviceScaleFactor:1});
 const errors=[]; page.on('pageerror',e=>errors.push(e.message));
 // Deterministic local QA must not mix checked-in fixtures with raw main or
 // current ESPN data. Published browser checks retain the real network path.
 if(!isLive)await page.route('**/*',route=>new URL(route.request().url()).origin===new URL(url).origin?route.continue():route.abort());
 const response=await page.goto(url,{waitUntil:'domcontentloaded',timeout:45000});
 assert(response?.ok(),name+' entry HTTP failure');
 await page.waitForURL('**/dames-picks/**',{timeout:15000});
 await page.waitForFunction(()=>typeof state!=='undefined'&&!state.loading&&state.updated,{timeout:45000});
 await page.locator('[data-league="NFL"]').click();
 const integrity=await page.evaluate(async()=>{
   const root=new URL('../nfl/data/',location.href);
   const json=async file=>{const r=await fetch(new URL(file,root),{cache:'no-store'});if(!r.ok)throw Error(file+' HTTP '+r.status);return r.json()};
   const manifest=await json('latest_2026.json');
   const chunks=await Promise.all(manifest.files.map(async file=>{const r=await fetch(new URL(file,root),{cache:'no-store'});if(!r.ok)throw Error(file+' HTTP '+r.status);return m.csv(await r.text())}));
   const latest=chunks.flat(),schedule=await json('schedule_2026.json'),archive=await json('active_frozen_2026.json');
   const expected=m.nfl([archive.records,...chunks],schedule);
   const keys=new Set(state.nfl.map(m.key));
   return {manifest,latestCount:latest.length,usageCount:latest.filter(r=>['1','1.0','True','true'].includes(String(r.usage_model_active))).length,
     withSnaps:latest.filter(r=>r.snap_pct_l3!==undefined&&r.snap_pct_l3!==null&&r.snap_pct_l3!=='').length,
     expected:expected.length,missing:expected.filter(r=>!keys.has(m.key(r))).length,loaded:state.nfl.length,
     errors:state.errors.filter(x=>x.startsWith('NFL ')),nonStandard:state.nfl.filter(p=>p.source!=='PrizePicks standard').map(p=>p.source),
     allFinite:state.nfl.every(p=>Number.isFinite(p.line)),build:document.querySelector('#app-build').textContent};
 });
 assert.equal(integrity.manifest.season,2026,name+' wrong season');
 assert(integrity.manifest.rows>0,name+' empty export');
 assert.equal(integrity.latestCount,integrity.manifest.rows,name+' incomplete chunk export');
 for(const col of ['snap_pct_l3','snap_pct_trend','target_share_l3','carry_share_l3','usage_model_active'])assert(integrity.manifest.schema.includes(col),'missing usage field '+col);
 assert.equal(integrity.usageCount,integrity.latestCount,name+' missing trained usage provenance');
 assert(integrity.withSnaps>=integrity.latestCount-2,name+' missing offensive snaps');
 assert(integrity.expected>0&&integrity.loaded>0,name+' no eligible archived/latest standard forecasts');
 assert.equal(integrity.missing,0,name+' app lost eligible source records');
 assert.deepEqual(integrity.errors,[],name+' NFL load failure');
 assert(integrity.allFinite,name+' invalid saved line');
 if(requireDeployed)assert(integrity.build.includes(expectedRelease),name+' deployed release mismatch: '+integrity.build);
 // Board rendering and highest-estimate order: zero cards is valid only when
 // no eligible upcoming lines exist. Never substitute synthetic public picks.
 const board=await page.evaluate(()=>({expected:shown().length,rendered:document.querySelectorAll('#cards [data-id]').length,
   rates:shown().map(p=>(m.hitEstimate(p)||p.matchupPreview)?.rate??null)}));
 assert.equal(board.rendered,board.expected,name+' board card count');
 let prior=Infinity;for(const value of board.rates){const rate=value===null?-Infinity:value;assert(rate<=prior,name+' hit-estimate ordering');prior=rate;}
 // Use a real saved player with multiple markets, even after kickoff.
 const sample=await page.evaluate(()=>{
  const groups=new Map();for(const p of state.nfl){const k=[p.gameId,p.playerId||p.player].join('|');if(!groups.has(k))groups.set(k,[]);groups.get(k).push(p)}
  const group=[...groups.values()].find(g=>new Set(g.map(p=>p.stat)).size>=2);if(!group)return null;
  open(m.key(group[0]));return {player:group[0].player,line:group[0].line,projection:group[0].projection};
 });
 assert(sample,name+' no real multi-market NFL sample');
 assert(await page.locator('#detail').isVisible(),name+' detail missing');
 assert((await page.locator('#player').innerText()).includes(sample.player),name+' wrong detail identity');
 assert(await page.locator('#markets button').count()>=2,name+' market switching missing');
 const text=await page.locator('#detail-content').innerText();
 for(const label of ['Matchup','Opponent','Saved at','Automatic grading','Pending results do not count as losses'])assert(text.includes(label),name+' missing detail '+label);
 await page.locator('#markets button').last().click();
 assert(await page.locator('#detail-content .hero').count()===1,name+' market switch broke detail');
 await page.locator('#back').click();
 await page.locator('[data-view="live"]').click();
 const game=await page.evaluate(()=>{const g=state.liveGames.find(g=>g.sport==='NFL'&&state.nfl.some(p=>p.gameId===g.gameId));if(!g)return null;openGame(g);return {id:g.gameId,count:m.displayCurrentPicks(state.nfl.filter(p=>p.gameId===g.gameId)).length};});
 assert(game&&game.count>0,name+' no saved game comparison');
 assert.equal(await page.locator('#detail-content [data-prop]').count(),game.count,name+' saved comparison records missing');
 const before=await page.locator('#detail-content').innerText();
 assert(before.includes('FROZEN LINE')&&before.includes('FROZEN PROJ')&&before.includes('ACTUAL'),name+' missing frozen/live comparison');
 // Re-render/refresh must retain the selected game and immutable saved records.
 await page.evaluate(()=>renderGameDetail());
 assert.equal(await page.locator('#detail-content [data-prop]').count(),game.count,name+' redraw lost records');
 await page.locator('#detail-content [data-prop]').first().click();
 assert(await page.locator('#detail-content .hero').count()===1,name+' game-to-prop navigation broken');
 await page.locator('#back').click();
 await page.locator('[data-view="tracker"]').click();
 assert(await page.locator('#board').isVisible(),name+' tracker navigation broken');
 const metrics=await page.evaluate(()=>({screen:innerWidth,width:document.documentElement.scrollWidth}));
 assert(metrics.width<=metrics.screen+2,name+' horizontal overflow '+JSON.stringify(metrics));
 await page.screenshot({path:output+'/'+name+'-unified-nfl.png',fullPage:false});
 assert.deepEqual(errors,[],name+' browser errors');
 console.log(name+' OK '+JSON.stringify({manifestRows:integrity.latestCount,eligible:integrity.expected,board:board.rendered,game,build:integrity.build,metrics}));
 await page.close();
}
(async()=>{
 await ensurePublished();
 const browser=await chromium.launch({headless:true,...(process.env.CHROMIUM_EXECUTABLE?{executablePath:process.env.CHROMIUM_EXECUTABLE}:{})});
 try{await verify(browser,'iphone-390',{width:390,height:844});await verify(browser,'desktop-1280',{width:1280,height:900});}finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
