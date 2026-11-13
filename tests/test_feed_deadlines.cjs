const {test}=require('node:test');const assert=require('node:assert/strict');const fs=require('node:fs');const vm=require('node:vm');
const html=fs.readFileSync('docs/dames-picks/index.html','utf8');
const source=html.slice(html.indexOf('async function fetchData('),html.indexOf('async function getJSON('));
function helper(fetch){const c={fetch,AbortController,Promise,setTimeout,clearTimeout,Error};vm.createContext(c);vm.runInContext(source,c);return c.fetchData;}
test('successful JSON and text responses survive',async()=>{const read=helper(async()=>({ok:true,json:async()=>42,text:async()=>'csv'}));assert.equal(await read('x'),42);assert.equal(await read('x','text'), 'csv');});
test('stalled connection rejects and aborts',async()=>{let signal;const read=helper(async(u,o)=>{signal=o.signal;return new Promise(()=>{});});await assert.rejects(read('x','json',10),/timed out/);assert.equal(signal.aborted,true);});
test('stalled response body cannot hold startup',async()=>{const read=helper(async()=>({ok:true,json:()=>new Promise(()=>{})}));await assert.rejects(read('x','json',10),/timed out/);});
test('HTTP and parser failures stay failures',async()=>{await assert.rejects(helper(async()=>({ok:false,status:503}))('x'),/503/);await assert.rejects(helper(async()=>({ok:true,json:async()=>{throw Error('bad JSON')}}))('x'),/bad JSON/);});
