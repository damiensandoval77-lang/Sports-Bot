import test from 'node:test';
import assert from 'node:assert/strict';
import {readOddsDiagnostics} from '../src/odds-diagnostics.js';
const now=Date.parse('2026-11-18T12:00:00.000Z');
const sample={league:'NBA',bookmaker:'prizepicks',event_id:'abc12345678',
 event_start:'2026-11-18T23:00:00Z',accepted_observations:34,fresh_pregame_lines:7,
 oldest_observed_at:'2026-11-17T12:00:00Z',latest_observed_at:'2026-11-18T11:30:00Z',
 latest_captured_at:'2026-11-18T11:31:00Z'};
function dbFor(books,events,queries=[]){return {prepare(sql){
 assert.match(sql,/^(SELECT|WITH) /);assert.doesNotMatch(sql,/\b(INSERT|UPDATE|DELETE|CREATE)\b/);
 const q={sql,args:[]};queries.push(q);
 return {bind(...args){q.args=args;return this},async all(){
  return {results:sql.includes('WITH ranked')?(sql.includes('GROUP BY league,bookmaker,event_id')?events:books):[]};
 }};
}}}
test('accepted per-book/event coverage is separate from historical observations and reports age',async()=>{
 const queries=[];let requests=0;const old=globalThis.fetch;
 globalThis.fetch=async()=>{requests++;throw Error('network forbidden')};
 try{
  const r=await readOddsDiagnostics({DB:dbFor([sample],[sample],queries)},now);
  assert.equal(r.status,'ok');assert.equal(requests,0);assert.equal(queries.length,5);
  const c=r.quote_coverage;
  assert.equal(c.bookmaker_counts[0].accepted_observations,34);
  assert.equal(c.bookmaker_counts[0].fresh_pregame_lines,7);
  assert.equal(c.bookmaker_counts[0].latest_observation_age_seconds,1800);
  assert.equal(c.event_bookmaker_counts[0].event_id,sample.event_id);
  assert.equal(c.event_groups_truncated,false);
  assert.match(c.provenance,/not_native_tier_verification/);
  for(const q of queries.filter(q=>q.sql.startsWith('WITH'))){
   assert.deepEqual(q.args.slice(0,4),['2026-11-18T12:00:00.000Z','2026-11-18T10:30:00.000Z','2026-11-18T12:00:00.000Z','2026-11-18T12:00:00.000Z']);
   assert.match(q.sql,/latest=1 AND event_start>\?/);
   assert.match(q.sql,/market_observed_at<=captured_at/);
   assert.match(q.sql,/captured_at<event_start/);
  }
 }finally{globalThis.fetch=old}
});
test('bounded event output explicitly reports truncation; bookmaker totals are independent',async()=>{
 const r=await readOddsDiagnostics({DB:dbFor([sample],Array.from({length:101},()=>sample))},now);
 assert.equal(r.quote_coverage.event_bookmaker_counts.length,100);
 assert.equal(r.quote_coverage.event_groups_truncated,true);
 assert.equal(r.quote_coverage.bookmaker_counts[0].accepted_observations,34);
});
test('future/invalid timestamps and malformed identifiers are not asserted as valid',async()=>{
 const x={...sample,event_id:'private\nvalue',bookmaker:'unlisted',latest_observed_at:'2026-11-19T00:00:00Z',latest_captured_at:'invalid'};
 const r=await readOddsDiagnostics({DB:dbFor([x],[x])},now);
 const c=r.quote_coverage.event_bookmaker_counts[0];
 assert.equal(c.event_id,null);assert.equal(c.bookmaker,null);
 assert.equal(c.latest_observation_age_seconds,null);assert.equal(c.latest_captured_at,null);
});
