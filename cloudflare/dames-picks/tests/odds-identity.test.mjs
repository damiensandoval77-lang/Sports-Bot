import test from 'node:test';
import assert from 'node:assert/strict';
import {verifyQuoteIdentity} from '../src/odds-identity.js';
const now=Date.parse('2026-11-18T20:00:00Z');
const q={source:'the_odds_api',league:'NBA',bookmaker:'prizepicks',market_tier:'standard',is_alternate:false,source_verified_by_response:true,event_id:'abc123',event_start:'2026-11-18T23:00:00Z',market_observed_at:'2026-11-18T19:45:00Z',collected_at:'2026-11-18T19:46:00Z',line:17.5,player:'Scottie Barnes',home_team:'Toronto Raptors',away_team:'New York Knicks',player_id:null,player_team:null};
const event={provider_event_id:q.event_id,verified:true,source:'NBA_CDN_SCHEDULE',league:'NBA',canonical_event_id:'0022600241',start:q.event_start,home_name:q.home_team,away_name:q.away_team,home_team_id:'TOR',away_team_id:'NYK'};
const player={name:q.player,player_id:'1630567',team_id:'TOR',verified:true,source:'NBA_CDN_ROSTER',as_of:'2026-11-18T18:00:00Z',valid_until:'2026-11-19T00:00:00Z'};
const run=(quote=q,events=[event],roster=[player])=>verifyQuoteIdentity(quote,{events,roster,now});
test('exact official identity produces research-only copy, never a pick',()=>{
 const before=JSON.stringify([q,event,player]);const r=run();
 assert.equal(r.status,'verified_research_identity');assert.equal(r.quote.player_id,'1630567');
 assert.equal(r.quote.eligible_for_frozen_capture,false);assert.equal(r.quote.projection,undefined);
 assert.equal(JSON.stringify([q,event,player]),before);
});
test('rejects duplicate/missing event and player identities',()=>{
 for(const [events,roster] of [[[],[player]],[[event,event],[player]],[[event],[]],[[event],[player,player]]])assert.equal(run(q,events,roster).status,'unavailable');
});
test('event mismatch, wrong source, rescheduling and wrong team fail closed',()=>{
 for(const patch of [{verified:false},{source:'provider'},{start:'2026-11-18T23:01:00Z'},{home_name:'Other'},{home_team_id:'NYK'},{canonical_event_id:'bad'},{league:'NFL'}])assert.equal(run(q,[{...event,...patch}]).status,'unavailable');
});
test('roster must be authoritative and valid through exact event',()=>{
 for(const patch of [{verified:false},{source:'provider'},{team_id:'LAL'},{player_id:''},{as_of:'2026-11-18T20:00:00Z'},{valid_until:'2026-11-18T22:00:00Z'}])assert.equal(run(q,[event],[{...player,...patch}]).status,'unavailable');
});
test('stale, future, conflicting, promotional and non-PrizePicks quotes rejected',()=>{
 for(const patch of [{market_observed_at:'2026-11-18T18:00:00Z'},{collected_at:'2026-11-18T20:01:00Z'},{market_observed_at:'2026-11-18T19:47:00Z'},{event_start:'2026-11-18T19:59:00Z'},{player_id:'999'},{player_team:'NYK'},{is_alternate:true},{bookmaker:'underdog'},{market_tier:'promo'},{line:NaN},{line:'17.5'}])assert.equal(run({...q,...patch}).status,'unavailable');
});

test('malformed evidence and empty normalized identities fail closed',()=>{
 assert.equal(run(q,null,[]).status,'unavailable');
 assert.equal(run(q,[],{}).status,'unavailable');
 assert.equal(run({...q,player:'---'},[event],[{...player,name:'---'}]).status,'unavailable');
 assert.equal(run({...q,home_team:''},[{...event,home_name:''}]).status,'unavailable');
 assert.equal(run(q,[{...event,canonical_event_id:'9912345678'}]).status,'unavailable');
});
