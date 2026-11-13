const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const html=fs.readFileSync('docs/dames-picks/index.html','utf8');
const code=html.split('/* OPEN_TAB_RELEASE_WATCH_START */')[1].split('/* OPEN_TAB_RELEASE_WATCH_END */')[0];
function setup({next='dp-new-r2',runtime=next,page=next,hidden=false,fail=false}={}){
 const el={'release-update':{hidden:true},'load-update':{}};let calls=0,assigned=null;
 const ctx={document:{hidden,addEventListener(){}},$:id=>el[id],RELEASE_ID:'dp-old-r1',setInterval(){},Date,URL,window:{location:{href:'https://example.com/app/?diagnostics=1',assign:v=>assigned=v}},fetch:async()=>{calls++;if(fail)throw Error('offline');return {ok:true,json:async()=>({release_id:next,runtime_bundle_id:runtime}),text:async()=>`<meta name="dames-release" content="${page}">`}}};
 vm.createContext(ctx);vm.runInContext(code,ctx);return{ctx,el,calls:()=>calls,assigned:()=>assigned};
}
const settle=()=>new Promise(r=>setImmediate(r));
test('coherent new release prompts without reload, then user button reloads preserving query',async()=>{const s=setup();await settle();assert.equal(s.el['release-update'].hidden,false);assert.equal(s.assigned(),null);s.el['load-update'].onclick();assert.match(s.assigned(),/diagnostics=1&app_release=dp-new-r2/);});
for(const [name,args]of Object.entries({same:{next:'dp-old-r1'},partial:{page:'dp-other'},mismatch:{runtime:'dp-other'},offline:{fail:true},hidden:{hidden:true},invalid:{next:'javascript:bad'}}))test(name+' never prompts/reloads',async()=>{const s=setup(args);await settle();assert.equal(s.el['release-update'].hidden,true);assert.equal(s.assigned(),null);});
test('overlapping poll does not duplicate fetches',async()=>{const s=setup();vm.runInContext('checkAppRelease()',s.ctx);await settle();assert.equal(s.calls(),2);});

const whenSource=html.match(/const when=t=>\{[^\n]+/)[0];
test('missing snapshot does not render an epoch date',()=>{
 const c={Date};vm.createContext(c);vm.runInContext(whenSource+';globalThis.formatSnapshot=when;',c);
 for(const v of [null,undefined,'',false,true,'not-a-date'])assert.equal(c.formatSnapshot(v),'Time unavailable');
 assert.notEqual(c.formatSnapshot('2026-11-13T02:00:00Z'),'Time unavailable');
});
