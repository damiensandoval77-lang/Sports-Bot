const {test}=require('node:test'),a=require('node:assert/strict');
require('../docs/dames-picks/feeds.js');const m=globalThis.DamesPicksModel;
const now=Date.parse('2026-11-13T06:00:00Z');
const row=(line,extra={})=>({sport:'NFL',player:'DK Metcalf',playerId:'00-0035640',team:'PIT',gameId:'2026_10_PIT_CIN',stat:'Rec Targets',start:'2026-11-16T01:20:00Z',captured:'2026-11-13T05:58:52Z',line,projection:6.6,marketTier:'standard',...extra});
test('simultaneous genuine standard thresholds both survive',()=>a.deepEqual(m.displayCurrentPicks([row(7),row(6.5)],now).map(x=>x.line),[6.5,7]));
test('exact duplicates collapse regardless provider ID',()=>a.equal(m.displayCurrentPicks([row(7,{modelId:'a'}),row(7,{modelId:'b'})],now).length,1));
test('older snapshot thresholds do not survive current snapshot',()=>a.deepEqual(m.displayCurrentPicks([row(7,{captured:'2026-11-13T04:00:00Z'}),row(6.5)],now).map(x=>x.line),[6.5]));
test('simultaneous alternatives independent of input order',()=>a.deepEqual(m.displayCurrentPicks([row(6.5),row(7)],now).map(x=>x.line),[6.5,7]));
test('unverified alternate cannot join standard expansion',()=>a.deepEqual(m.displayCurrentPicks([row(6.5),row(10,{marketTier:'demon'})],now).map(x=>x.line),[6.5]));
test('NBA remains one current line',()=>a.equal(m.displayCurrentPicks([row(6.5,{sport:'NBA'}),row(7,{sport:'NBA'})],now).length,1));
test('finished game display remains one frozen card',()=>a.equal(m.displayCurrentPicks([row(6.5),row(7)],Date.parse('2026-11-17')).length,1));
test('line-specific evidence remains untouched',()=>{const x=row(7,{matchupPreview:{rate:.54,pushRate:.145}}),y=row(6.5,{matchupPreview:{rate:.54,pushRate:0}});const out=m.displayCurrentPicks([x,y],now);a.equal(out[0],y);a.equal(out[1],x);a.equal(out[1].matchupPreview.pushRate,.145)});

test('explicit goblin or demon never overrides a standard card',()=>a.deepEqual(m.displayCurrentPicks([row(6.5),row(3,{marketTier:'goblin'}),row(10,{marketTier:'demon',captured:'2026-11-13T05:59:00Z'})],now).map(x=>x.line),[6.5]));

test("detail tabs expose the exact threshold alongside escaped market name",()=>{const html=require("node:fs").readFileSync(require("node:path").join(__dirname,"../docs/dames-picks/index.html"),"utf8");a.ok(html.includes("escapeText(x.stat)+' · '+fmt(x.line)"));});
