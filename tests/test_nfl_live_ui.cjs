/* Verify actual NFL dashboard rendering at mobile and desktop sizes.
 * Never modifies production data; screenshots are GitHub Actions artifacts.
 */
const { chromium } = require('playwright');
const fs = require('node:fs');
const assert = require('node:assert/strict');

const url = process.env.NFL_UI_URL || 'http://127.0.0.1:8765/nfl/';
const isLive = url.startsWith('https://');
const output = process.env.NFL_SCREENSHOT_DIR || 'nfl-ui-artifacts';
fs.mkdirSync(output, { recursive: true });

async function ensurePublished() {
  if (!isLive) return;
  for (let attempt=1; attempt<=12; attempt++) {
    try {
      const response = await fetch(url, {cache:'no-store'});
      if (response.ok && (await response.text()).includes('function groupPlayerMarkets(')) return;
    } catch (error) {
      console.log('Live site not yet reachable: '+error.message);
    }
    if(attempt===12) throw new Error('Live GitHub Pages does not yet serve grouped NFL player cards');
    await new Promise(resolve=>setTimeout(resolve,15000));
  }
}

async function verify(browser, name, viewport) {
  const page=await browser.newPage({viewport,deviceScaleFactor:1});
  const failures=[];
  page.on('pageerror',error=>failures.push(error.message));
  const reply=await page.goto(url,{waitUntil:'domcontentloaded',timeout:45000});
  assert(reply && reply.ok(),name+' page did not return HTTP 200');
  await page.waitForFunction(()=>document.getElementById('status').textContent!=='CONNECTING',
    {timeout:30000}).catch(()=>{});
  // Production data integrity: the UI must use the same recent validated
  // snapshot as main, not a stale Pages artifact or incomplete chunk upload.
  const manifest=await page.evaluate(async()=>{
    const response=await fetch('./data/latest_2026.json?t='+Date.now(),{cache:'no-store'});
    if(!response.ok) throw new Error('NFL latest manifest unavailable');
    return response.json();
  });
  assert(manifest.season===2026 && manifest.rows>=2236,
    name+' is serving an older/incomplete NFL usage snapshot: '+JSON.stringify({
      rows:manifest.rows,captured_at:manifest.captured_at}));
  for(const col of ['snap_pct_l3','snap_pct_trend','target_share_l3',
                    'carry_share_l3','usage_model_active']){
    assert(manifest.schema.includes(col),name+' missing validated usage field '+col);
  }
  const loaded=await page.evaluate(()=>({
    rows:state.lines.length,
    usageCount:state.lines.filter(row=>row.usage_model_active==='1.0'||
      row.usage_model_active==='1'||row.usage_model_active==='True').length,
    withSnaps:state.lines.filter(row=>row.snap_pct_l3!==undefined&&
       row.snap_pct_l3!==null&&row.snap_pct_l3!=='').length
  }));
  assert.equal(loaded.rows,manifest.rows,name+' did not load complete snapshot');
  assert.equal(loaded.usageCount,manifest.rows,
    name+' trained usage provenance is missing on some lines');
  assert(loaded.withSnaps>=manifest.rows-2,
    name+' offensive snap data unexpectedly absent');
  const status=await page.locator('#status').innerText();
  assert(!['CONNECTING','DATA UNAVAILABLE','SCHEDULE ONLY'].includes(status),
    name+' failed to load prediction feed: '+status);
  const sample=await page.evaluate(()=>{
    const byPlayer=new Map();
    for(const row of state.lines) {
      if(row.odds_type!=='standard') continue;
      const key=[row.game_id,row.team,row.player_id||row.player].join('|');
      if(!byPlayer.has(key)) byPlayer.set(key,[]);
      byPlayer.get(key).push(row);
    }
    const group=[...byPlayer.values()].find(rows=>rows.length>=2);
    if(!group)return null;
    const player=group[0];
    state.week=String(player.week);state.game=player.game_id;
    document.getElementById('weekfilter').value=state.week;
    document.getElementById('search').value=player.player;
    document.getElementById('kind').value='standard';
    render();
    return {player:player.player,game:player.game_id,marketCount:group.length};
  });
  assert(sample,name+' has no multiple-market player in loaded standard lines');
  const cards=page.locator('#cards > article.player-group');
  assert(await cards.count()>=1,name+' did not render grouped player card');
  const card=cards.first();
  const marketCount=await card.locator('.market-entry').count();
  assert(marketCount>=2,name+' shows separate player cards instead of grouped markets');
  assert((await card.locator('.group-count').innerText()).includes('markets'),
    name+' missing group-count label');
  assert.equal(await card.locator('.pickbar').count(),marketCount,name+' missing distinct market rows');
  assert.equal(await card.locator('.vals').count(),marketCount,name+' missing individual projections');
  await card.locator('details > summary').first().click();
  assert(await card.locator('.detailbody .seasonbar').count()>0,
    name+' market details did not retain season record');
  const usageLabels=await card.locator('.detailbody').first().innerText();
  for(const label of ['Offensive snaps (L3)','Snap trend',
                      'Target share (L3)','Carry share (L3)','Usage model inputs']){
    assert(usageLabels.includes(label),name+' expanded prop is missing '+label);
  }
  const playerHeaderColor=await card.locator('> .mainline').evaluate(node=>
    getComputedStyle(node).backgroundColor);
  assert(['rgb(5, 6, 8)','rgb(0, 0, 0)'].includes(playerHeaderColor),
    name+' did not retain the black player header: '+playerHeaderColor);
  await page.screenshot({path:output+'/'+name+'-player-card.png',fullPage:false});
  const metrics=await page.evaluate(()=>({screen:innerWidth,page:document.documentElement.scrollWidth,
    body:document.body.scrollWidth}));
  assert(metrics.page<=metrics.screen+2,
    name+' horizontal overflow detected: '+JSON.stringify(metrics));
  await page.locator('button[data-tab="live"]').click();
  assert(await page.locator('#live').isVisible(),name+' matchups tab broken');
  const newTrackerDeployed=await page.evaluate(()=>typeof liveComparisonRows==='function');
  if(!isLive || newTrackerDeployed){
  await page.waitForFunction(()=>state.frozenReady,{timeout:15000}).catch(()=>{});
  // Direct UI fixture: a saved pregame quote stays visible beside live stats
  // even if the public network live feed is unavailable.
  const tracker=await page.evaluate(()=>{
    const chosen=state.lines.find(r=>r.game_id===state.game && Number.isFinite(Number(r.line)));
    if(!chosen)return null;
    state.frozen=[chosen];state.frozenReady=true;
    state.live={season:2026,checked_at:new Date().toISOString(),games:[{
      game_id:chosen.game_id,status:'in',status_text:'Q1 10:00',period:1,clock:'10:00',
      away:chosen.opponent,home:chosen.team,
      players:[{player:chosen.player,team:chosen.team,stats:{[chosen.target]:3}}]
    }]};
    render();
    return {game:chosen.game_id,line:chosen.line,player:chosen.player};
  });
  assert(tracker,name+' missing fixture-compatible saved line');
  const liveDetail=page.locator('details[data-livegame="'+tracker.game+'"]');
  assert(await liveDetail.count()===1,name+' missing live comparison panel');
  await liveDetail.locator('summary').click();
  let detail=await liveDetail.innerText();
  assert(detail.includes('Frozen line vs live stats')&&detail.includes(tracker.player)&&
    detail.includes(tracker.line),name+' frozen line / live actual not rendered');
  await page.evaluate(()=>{state.live=null;render()});
  await page.locator('details[data-livegame="'+tracker.game+'"] summary').click();
  detail=await page.locator('details[data-livegame="'+tracker.game+'"]').innerText();
  assert(detail.includes(tracker.line)&&detail.includes('Live feed unavailable'),
    name+' unavailable feed incorrectly hides previously frozen props');
  }else{
    console.log(name+' deployed Pages has not yet received new live tracker; local source checks enforce this PR.');
  }
  await page.locator('button[data-tab="graded"]').click();
  assert(await page.locator('#graded').isVisible(),name+' graded tab broken');
  assert.equal(failures.length,0,name+' browser script errors: '+failures.join(' / '));
  console.log(name+' OK: '+JSON.stringify({status,sample,marketCount,metrics}));
  await page.close();
}

(async()=>{
  await ensurePublished();
  const browser=await chromium.launch({headless:true});
  try {
    await verify(browser,'iphone-390',{width:390,height:844});
    await verify(browser,'desktop-1280',{width:1280,height:900});
  } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
