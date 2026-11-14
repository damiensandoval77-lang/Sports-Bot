import ast,collections,concurrent.futures,json,subprocess,yaml
from pathlib import Path
ROOT=Path.cwd(); rows=json.loads((ROOT/'out/current/branches.json').read_text()); refs=[r for r in rows if '/origin/' in r['ref']]
def tree(row):
 data=subprocess.check_output(['git','ls-tree','-r',row['sha']],text=True)
 found=[]
 for l in data.splitlines():
  meta,path=l.split('\t',1);mode,kind,sha=meta.split()
  if kind=='blob' and (path.endswith(('.py','.js','.cjs','.sh')) or path.startswith('.github/workflows/') and path.endswith(('.yml','.yaml'))):found.append((sha,path,row['ref']))
 return found
blobs={}
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
 for found in ex.map(tree,refs):
  for sha,path,ref in found:blobs.setdefault((sha,Path(path).suffix),{'sha':sha,'path':path,'refs':[]})['refs'].append(ref)
print('collected',len(refs),'heads',len(blobs),'distinct source blobs',flush=True)
def check(item):
 (sha,ext),entry=item
 try:
  raw=subprocess.check_output(['git','cat-file','blob',sha]);text=raw.decode('utf-8')
  if ext=='.py':ast.parse(text)
  elif ext in ('.yml','.yaml'):yaml.safe_load(text)
  elif ext=='.sh':
   p=subprocess.run(['bash','-n'],input=text,text=True,capture_output=True)
   if p.returncode:raise ValueError(p.stderr[:300])
  elif ext in ('.js','.cjs'):
   p=subprocess.run(['node','--check'],input=text,text=True,capture_output=True)
   if p.returncode:raise ValueError(p.stderr[:300])
  return None
 except Exception as e:return {**entry,'error':type(e).__name__+': '+str(e)[:400]}
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex: failures=[x for x in ex.map(check,blobs.items()) if x]
report={'scope':'All fetched remote branch heads; distinct Python, JS, CJS, shell and Actions YAML blobs; syntax only, not execution or behavioral equivalence','heads':len(refs),'unique_source_blobs':len(blobs),'failures':failures}
(ROOT/'out/current/branch-source-syntax.json').write_text(json.dumps(report,indent=2)); print(json.dumps({'heads':len(refs),'unique_source_blobs':len(blobs),'failures':len(failures),'affected_branches':len({r for f in failures for r in f['refs']})}),flush=True)
