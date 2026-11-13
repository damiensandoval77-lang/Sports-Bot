const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
const ctx={Date,Intl};vm.createContext(ctx);vm.runInContext(fs.readFileSync('docs/dames-picks/feeds.js','utf8'),ctx);
const m=ctx.DamesPicksModel;
const quote=(team,game)=>({tier:'standard',more_tier:'standard',less_tier:'standard',is_demo:false,stat:'PTS',line:10.5,player:'Test',team,game,observed_at:'2026-11-13T10:00:00Z',starts_at:'2026-11-14T00:00:00Z'});
test('archive opponents use exact own team on either matchup side',()=>{
 for(const [team,game,expected] of [['CLE','Cleveland Cavaliers @ Miami Heat','Miami Heat'],['MIA','Cleveland Cavaliers @ Miami Heat','Cleveland Cavaliers'],['NY','NYK @ CLE','CLE'],['XYZ','CLE @ MIA','Opponent unavailable'],['LAC','LA Clippers @ Phoenix Suns','Phoenix Suns']]){
 const row=m.includeArchivedStandard([],{quotes:[quote(team,game)]})[0];assert.equal(row.opponent,expected);assert.equal(row.projection,null);assert.equal(row.quoteOnly,true);
 }
});
test('scheduled display is not described as stale; tracker not mislabeled today',()=>{
 const html=fs.readFileSync('docs/dames-picks/index.html','utf8');
 assert.ok(html.includes('Scheduled game — live stats begin after play starts'));
 assert.ok(html.includes('Frozen pick tracker'));assert.ok(!html.includes('Today’s frozen picks'));
 assert.ok(html.includes("g.start?' · Starts '"));
 const script=html.split('<script>').at(-1).split('</script>')[0];new vm.Script(script);
});

test('old pregame snapshots cannot claim game has not begun',()=>{
 const html=fs.readFileSync('docs/dames-picks/index.html','utf8');
 assert.ok(html.includes('g.state==="scheduled"&&timestamp(g.start)>Date.now()?"Scheduled game'));
});
