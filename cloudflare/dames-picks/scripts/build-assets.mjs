/**
 * Build a standalone Cloudflare staging asset tree from the existing merged
 * GitHub Pages app. This does NOT change the live site or train/poll models.
 *
 * Only public website file types and known public folders are copied.
 * Large unsupported files fail closed, rather than silently losing predictions.
 */
import {cpSync,existsSync,mkdirSync,readdirSync,readFileSync,rmSync,statSync,writeFileSync} from "node:fs";
import {join,resolve,relative,extname} from "node:path";
const project = resolve(import.meta.dirname,"..");
const input = resolve(project,"..","..","docs");
const output = resolve(project,"dist");
const MAX_FILE = 25*1024*1024;
const ALLOWED = new Set([".html",".htm",".js",".css",".json",".csv",".txt",".svg",".png",".jpg",".jpeg",".webp",".gif",".ico",".xml",".webmanifest",".wasm",".woff2"]);
const IGNORE = /(?:^|\/)(?:\.env[^/]*|[^/]*\.pem|[^/]*\.key|[^/]*\.secret|secrets?\.json|node_modules|\.git|__pycache__)(?:\/|$)/i;
const required = [
 "dames-picks/index.html","dames-picks/classic.html","dames-picks/feeds.js",
 "dames-picks/concept-3-connected.js","dames-picks/live_direct.js",
 "dames-picks/unified-shell.js","nba_schedule.json","current_form.json",
 "lagged_matchup_all_market_ledger.json","prizepicks_pregame_line_archive.json",
 "nba_confidence_calibration.json","nfl/data/latest_2026.json"
];
if(!existsSync(input))throw Error("Missing existing docs/ website tree");
rmSync(output,{recursive:true,force:true});mkdirSync(output,{recursive:true});
const report={mode:"staging-snapshot-only",source:"docs/",copied:0,bytes:0,skipped:[],not_automated:true};
function walk(dir,prefix=""){
 for(const d of readdirSync(dir,{withFileTypes:true})){
  const rel=prefix?prefix+"/"+d.name:d.name;
  if(IGNORE.test(rel)||d.isSymbolicLink())continue;
  const full=join(dir,d.name);
  if(d.isDirectory()) {
   if(rel==="dames-picks"||rel==="nfl"||rel==="nfl/data"||rel.startsWith("dames-picks/")||rel.startsWith("nfl/data/"))walk(full,rel);
   continue;
  }
  if(!d.isFile()||!ALLOWED.has(extname(d.name).toLowerCase()))continue;
  const st=statSync(full);
  if(st.size>MAX_FILE){report.skipped.push({path:rel,reason:"Cloudflare 25MiB file limit"});continue}
  const dest=join(output,rel);mkdirSync(resolve(dest,".."),{recursive:true});
  cpSync(full,dest);report.copied++;report.bytes+=st.size;
 }
}
walk(input);
const missing=required.filter(name=>!existsSync(join(output,name)));
if(missing.length)throw Error("Staging build refused: critical data/UI files unavailable or over 25MiB: "+missing.join(", "));
const existing=join(output,"dames-picks/index.html");
let html=readFileSync(existing,"utf8");
if(!html.includes("</head>")||!html.includes("<body>"))throw Error("Unexpected new homepage markup");
html=html.replace("</head>",'<meta name="robots" content="noindex,nofollow"><meta name="cf-stage" content="read-only-snapshot"></head>');
html=html.replace("<body>",'<body><div id="cloudflare-staging-banner" role="status" style="background:#321850;color:#f5ddff;text-align:center;padding:9px 12px;font:12px system-ui;position:relative;z-index:999">Cloudflare STAGING — published snapshot mirror; independent sports collectors and D1 are not yet connected. Not the production site.</div>');
writeFileSync(existing,html);
writeFileSync(join(output,"index.html"),'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="robots" content="noindex,nofollow"><meta http-equiv="refresh" content="0; url=/dames-picks/"><title>Dame\'s Picks staging</title></head><body><a href="/dames-picks/">Open Dame\'s Picks staging</a></body></html>\n');
writeFileSync(join(output,"_headers"),'/*\n  X-Robots-Tag: noindex, nofollow\n/*.json\n  Cache-Control: no-store\n/*.csv\n  Cache-Control: no-store\n');
writeFileSync(join(output,"staging-build-status.json"),JSON.stringify(report,null,2)+"\n");
if(report.copied>20000)throw Error("Exceeds free Workers per-version static asset cap");
console.log("Dame's Picks Cloudflare staging snapshot built:",report.copied,"files,",Math.round(report.bytes/1048576)+"MiB");
if(report.skipped.length)console.warn("Optional oversized public static files omitted:",report.skipped.slice(0,12));
