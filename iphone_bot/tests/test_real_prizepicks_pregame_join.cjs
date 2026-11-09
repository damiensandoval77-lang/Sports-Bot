// Real published-feed contract test: PrizePicks offers + pretip AI projections.
// No provider requests, API keys, synthetic hit probabilities or betting actions.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const root = path.resolve(__dirname, '../..');
const html = fs.readFileSync(path.join(root, 'docs/index.html'), 'utf8');
function between(start, end) {
  const i = html.indexOf(start), j = html.indexOf(end, i + start.length);
  assert(i >= 0 && j > i, 'Missing production JavaScript section: '+start);
  return html.slice(i, j);
}
assert(html.includes('ppProviderPartial=ppFresh&&(pp.value.partial_board===true||pp.value.complete_provider_board===false)'), 'Partial provider coverage must be shown truthfully');
assert(html.includes('matched model/line research records (not calibrated picks or hit probabilities)'), 'Research-only join count must be disclosed');
const normalization = between('const norm=x=>', 'const fmt=x=>');
const recent = between('function isRecent(', 'function appendValues(');
const joining = between('function verifiedQuickPrizePicksJoins(', 'function groupAI(');
// Anchor simulated quote age to actual saved forecast generation time.
const forecast = load('ai_projection_fallback.json');
const NOW = Date.parse(forecast.generated_at)+5*60*1000;
assert(Number.isFinite(NOW), 'Saved forecast requires a valid generation timestamp');
assert(forecast.predictions.some(p=>Date.parse(p.start)>NOW), 'Contract needs a genuine future forecast');
class FixedDate extends Date { static now() { return NOW; } }
const sandbox = {Date: FixedDate, Number, String, Set, Map, Math, Array};
const quick = vm.runInNewContext(
  normalization+'\n'+recent+'\n'+joining+'\nverifiedQuickPrizePicksJoins', sandbox
);
function load(name) { return JSON.parse(fs.readFileSync(path.join(root, 'docs', name), 'utf8')); }
// Test real saved identities with a deliberately simulated fresh observation time.
// The source fixture itself is stale in production; this is only a contract test.
const source = load('prizepicks_site.json');
const syntheticQuoteTime = new Date(NOW-10*60*1000).toISOString();
source.generated_at=syntheticQuoteTime;
source.board_offers=source.board_offers.map(o=>({...o,observed_at:syntheticQuoteTime}));
const roster = load('current_form.json').players;
assert.equal(source.status, 'LIVE_THIRD_PARTY_PRIZEPICKS_LINES');
assert.equal(forecast.status, 'PREGAME_PROJECTIONS_NO_LINES');
assert(Array.isArray(source.board_offers) && Array.isArray(forecast.predictions));
const matched = quick(source, forecast, roster, NOW);
assert(matched.length >= 100,
  'Expected material overlap between actual archived PrizePicks board and pretip forecasts; got '+matched.length);
for (const p of matched) {
  assert(p.quick_research_only, 'Not a wagering recommendation');
  assert.equal(p.sportsbook, 'PrizePicks');
  assert.equal(p.reliability_screen.validated, false);
  assert.equal(p.reliability_screen.side, null);
  assert(Number.isFinite(p.line) && Number.isFinite(p.projection));
  assert(Date.parse(p.start) > NOW);
}
const withNoDemo = { ...source, board_offers: source.board_offers.map(o=>({...o, is_demo:true})) };
assert.equal(quick(withNoDemo, forecast, roster, NOW).length, 0, 'Demo lines must not join');
assert.equal(quick({...source, generated_at:'2026-11-08T00:00:00Z'},forecast,roster,NOW).length,0,
  'Old PrizePicks quotes must not reappear as fresh');
assert.equal(quick(source,{...forecast,generated_at:'2026-11-08T00:00:00Z'},roster,NOW).length,0,
  'Old forecasts must not be mistaken for current pregame predictions');
const staleIndividual = {...source, board_offers:source.board_offers.map(o=>({...o,observed_at:'2026-11-09T09:24:00Z'}))};
assert.equal(quick(staleIndividual,forecast,roster,NOW).length,0,
  'Stale individual prices must not join even if overall source stamp looks refreshed');
const modified = JSON.parse(JSON.stringify(source));
modified.board_offers.forEach(o=>{o.starts_at='2026-11-08T01:00:00Z';});
assert.equal(quick(modified,forecast,roster,NOW).length,0,'Started games must be filtered');
console.log('PASS: '+matched.length+' genuine historical offer/forecast joins; demo, stale, tipped-off safeguards passed.');
