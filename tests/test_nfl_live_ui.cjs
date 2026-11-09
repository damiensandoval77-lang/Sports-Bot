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
  await page.screenshot({path:output+'/'+name+'-player-card.png',fullPage:false});
  const metrics=await page.evaluate(()=>({screen:innerWidth,page:document.documentElement.scrollWidth,
    body:document.body.scrollWidth}));
  assert(metrics.page<=metrics.screen+2,
    name+' horizontal overflow detected: '+JSON.stringify(metrics));
  await page.locator('button[data-tab="live"]').click();
  assert(await page.locator('#live').isVisible(),name+' matchups tab broken');
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
