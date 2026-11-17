#!/usr/bin/env node
/**
 * Run a REAL local Wrangler Worker + D1 database, invoke scheduled(), and
 * prove 0001 + 0002 schema initialization, recurring heartbeat and no spend.
 * Never connects to the owner's remote D1 database or paid sports providers.
 */
import {spawn} from "node:child_process";
import {mkdtempSync,writeFileSync,rmSync,readFileSync} from "node:fs";
import {tmpdir} from "node:os";
import {join,resolve} from "node:path";
import {setTimeout as delay} from "node:timers/promises";

const root=resolve(import.meta.dirname,"..");
const temp=mkdtempSync(join(tmpdir(),"dames-d1-local-smoke-"));
const configPath=join(root,"wrangler.local-cron-smoke.jsonc");
const raw=JSON.parse(readFileSync(join(root,"wrangler.jsonc"),"utf8"));
delete raw.assets;
raw.name="dames-picks-d1-local-smoke";
raw.vars={APP_STAGE:"staging",PAID_PROVIDER_REQUESTS:"disabled"};
raw.d1_databases=[{...raw.d1_databases[0],database_name:"dames-picks-d1-local-smoke"}];
writeFileSync(configPath,JSON.stringify(raw,null,2));
const base="http://127.0.0.1:8789";
const cmd=resolve(root,"node_modules/.bin/wrangler");
let logs="",child;
async function get(path){
 const ctl=new AbortController();
 const timer=setTimeout(()=>ctl.abort(),8000);
 try{return await fetch(base+path,{signal:ctl.signal,cache:"no-store"})}
 finally{clearTimeout(timer)}
}
try{
 child=spawn(cmd,["dev","--local","--test-scheduled","--ip","127.0.0.1",
   "--port","8789","--config",configPath,"--persist-to",temp],{
   cwd:root,env:{...process.env,WRANGLER_SEND_METRICS:"false"},
   stdio:["ignore","pipe","pipe"]
 });
 for(const pipe of [child.stdout,child.stderr])
  pipe.on("data",x=>{logs=(logs+String(x)).slice(-14000)});
 let started=false;
 for(let i=0;i<100;i++){
  if(child.exitCode!==null)throw Error("Wrangler exited before binding D1");
  try{
   const r=await get("/healthz");
   if(r.ok){
    const info=await r.json();
    if(info.database_binding_present===true&&info.paid_provider_calls==="disabled"){
     started=true;break;
    }
   }
  }catch(_){}
  await delay(220);
 }
 if(!started)throw Error("Local Worker did not start with D1 binding");
 const paths=["/cdn-cgi/local/scheduled?format=json","/__scheduled?cron=0+*+*+*+*"];
 let invoked=false;
 for(const path of paths){
  try{
   const response=await get(path);
   const body=await response.text();
   if(!response.ok)continue;
   // Do not trust only the route's 200: inspect D1 readiness separately.
   for(let i=0;i<25;i++){
    const status=await get("/api/v1/status");
    if(status.ok){
     const data=await status.json();
     if(data.database==="connected"&&data.sources?.length===7&&data.scheduled_heartbeat){
      invoked=true;break;
     }
    }
    await delay(250);
   }
   if(invoked)break;
   logs=(logs+"\nScheduled route "+path+" returned "+body.slice(0,400)).slice(-14000);
  }catch(e){logs=(logs+"\n"+String(e)).slice(-14000)}
 }
 if(!invoked)throw Error("Worker Cron did not create real local D1 tables and persisted heartbeat");
 const status=await (await get("/api/v1/status")).json();
 if(status.status!=="collectors_not_ready"||status.sources.length!==7)
  throw Error("Worker incorrectly claimed live sources or skipped source seed");
 const odds=await get("/api/v1/odds/budget");
 if(!odds.ok)throw Error("Odds 0002 schema missing after scheduled bootstrap");
 const budget=await odds.json();
 if(budget.status!=="ok"||budget.config.collection_enabled!==false)
  throw Error("Odds credit guard failed in local D1");
 console.log("PASS REAL WRANGLER+D1: both migrations, seven disconnected sources, persisted Cron heartbeat, budget initialized, zero paid calls");
}catch(e){
 console.error("FAILED REAL WRANGLER+D1:",String(e));
 console.error(logs.slice(-7000));
 process.exitCode=1;
}finally{
 if(child){child.kill("SIGTERM");await delay(300);if(child.exitCode===null)child.kill("SIGKILL")}
 rmSync(configPath,{force:true});
 rmSync(temp,{recursive:true,force:true});
}
