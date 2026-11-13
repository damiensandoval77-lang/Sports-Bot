/* Verify the supported unified NFL UI, including the retired-route redirect.
 * Reads authentic published snapshots; never injects predictions or outcomes.
 */
const { chromium } = require('playwright');
const fs = require('node:fs');
const assert = require('node:assert/strict');
require('../docs/dames-picks/feeds.js');
const feeds = globalThis.DamesPicksModel;
const url = process.env.NFL_UI_URL || 'http://127.0.0.1:8765/nfl/';
const output = process.env.NFL_SCREENSHOT_DIR || 'nfl-ui-artifacts';
fs.mkdirSync(output,{recursive:true});
async function verify(browser,name,viewport){
 const page=await browser.newPage({viewport});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 try{
  const response=await page.goto(url,{waitUntil:'domcontentloaded'});
  assert(response&&response.ok(),'HTTP response unavailable');
  await page.waitForURL('**/dames-picks/**');
  await page.waitForFunction(()=>document.querySelector('#status')?.textContent.includes('Checked'),null,{timeout:45000});
  const base=new URL('../nfl/data/',page.url()).href;
  const get=async path=>{const r=await page.request.get(base+path);assert(r.ok(),path+' unavailable');return r;};
  const manifest=await (await get('latest_2026.json')).json();
  assert.equal(manifest.season,2026);assert(manifest.rows>0&&manifest.files.length>0);
  const raw=[];
  for(const file of manifest.files){assert(/^latest_2026_[0-9]+\.csv$/.test(file));raw.push(...feeds.csv(await (await get(file)).text()));}
  assert.equal(raw.length,manifest.rows,'Incomplete published NFL chunks');
  for(const col of ['snap_pct_l3','snap_pct_trend','target_share_l3','carry_share_l3','usage_model_active'])assert(manifest.schema.includes(col),'Missing usage field '+col);
  const schedule=await (await get('schedule_2026.json')).json();
  const health=await (await get('grading_health_2026.json')).json();
  const graded=feeds.csv(await (await get('pp_graded_2026.csv')).text());
  const pending=feeds.csv(await (await get('pp_grading_pending_2026.csv')).text());
  const expected=feeds.reconcileNFLSettlementCards(feeds.nfl([raw],schedule),graded,pending,schedule);
  assert.equal(expected.filter(p=>p.grade==='GRADED'&&typeof p.hit==='boolean').length,health.standard_settled);
  assert.equal(expected.filter(p=>p.grade==='PENDING'&&p.frozenSettlementArchive&&p.pendingReason).length,pending.filter(p=>p.odds_type==='standard').length);
  await page.getByRole('button',{name:'NFL',exact:true}).click();
  await page.getByRole('button',{name:'Tracker',exact:true}).click();
  await page.locator('.pick').first().waitFor();
  assert(await page.locator('.pick').count()>0,'NFL saved standard cards absent');
  await page.locator('.pick').first().click();
  await page.locator('#detail:not(.hidden)').waitFor();
  assert.equal(await page.getByRole('heading',{name:'Dame’s projection',exact:true}).count(),1);
  assert.equal(await page.getByText('Dame’s Take',{exact:true}).count(),1);
  assert(/OVER|UNDER/.test(await page.locator('#detail-content').innerText()));
  await page.screenshot({path:output+'/'+name+'-player.png',fullPage:true});
  await page.getByRole('button',{name:'Back',exact:true}).click();
  await page.getByRole('button',{name:'Live',exact:true}).click();
  await page.locator('[data-game]').first().waitFor();
  await page.locator('[data-game]').first().click();
  assert(await page.getByText('Full published player box score',{exact:false}).count()>0);
  assert(await page.getByText('Saved pregame standard lines',{exact:false}).count()>0);
  await page.screenshot({path:output+'/'+name+'-game.png',fullPage:true});
  assert.deepEqual(errors,[],'Browser errors');
  console.log(name+' unified NFL PASS: '+raw.length+' source rows, '+health.standard_settled+' standard decisions; redirect, tracker, player/game details');
 }finally{await page.close();}
}
(async()=>{const browser=await chromium.launch({headless:true,args:['--no-sandbox']});try{await verify(browser,'phone',{width:390,height:844});await verify(browser,'desktop',{width:1280,height:900});}finally{await browser.close();}})().catch(e=>{console.error(e);process.exit(1);});
