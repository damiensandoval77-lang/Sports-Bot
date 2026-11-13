"""Read the *central directory* of large Kaggle ZIP with bounded HTTP ranges.

Never stream the entire >2GB archive. Refuses non-206 responses to avoid
unintended full transfer, and caps total received bytes.
"""
import io,json,re,urllib.request,urllib.error,zipfile
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlparse
from .inspect_kaggle_nba_archive import classify
URL="https://www.kaggle.com/api/v1/datasets/download/chevronronson/nba-stats-dataset"
OUT=Path("docs/kaggle_nba_zip_range_inventory.json")
BLOCK=2*1024*1024
MAX_BYTES=26*1024*1024
class RemoteZip(io.RawIOBase):
 def __init__(self):
    self.position=0
    self.used=0
    self.cache={}
    req=urllib.request.Request(URL,method="HEAD",
                               headers={"User-Agent":"SportsBot-Research/1.0"})
    with urllib.request.urlopen(req,timeout=45) as r:
        self.length=int(r.headers["Content-Length"])
        self.endpoint=r.url
    if self.length>5*1024**3:raise ValueError("Dataset too large to inspect safely")
    if urlparse(self.endpoint).scheme!="https":raise ValueError("Unsafe redirect")
 def readable(self):return True
 def seekable(self):return True
 def tell(self):return self.position
 def seek(self,offset,whence=0):
    self.position=(offset if whence==0 else
                   self.position+offset if whence==1 else self.length+offset)
    if not 0<=self.position<=self.length:raise ValueError("Seek outside archive")
    return self.position
 def block(self,index):
    if index in self.cache:return self.cache[index]
    start=index*BLOCK;end=min(self.length-1,start+BLOCK-1)
    req=urllib.request.Request(self.endpoint,headers={
       "Range":f"bytes={start}-{end}",
       "User-Agent":"SportsBot-Research/1.0","Accept-Encoding":"identity"})
    with urllib.request.urlopen(req,timeout=35) as r:
        if r.status!=206:raise ValueError("HTTP_BYTE_RANGE_NOT_SUPPORTED")
        content=r.read(BLOCK+1)
        if len(content)!=end-start+1:raise ValueError("INVALID_RANGE_RESPONSE")
    self.used+=len(content)
    if self.used>MAX_BYTES:raise ValueError("RANGE_BUDGET_EXCEEDED")
    self.cache[index]=content
    return content
 def read(self,size=-1):
    if size is None or size<0:size=self.length-self.position
    remaining=min(size,self.length-self.position)
    fragments=[]
    while remaining:
        index=self.position//BLOCK;offset=self.position%BLOCK
        piece=self.block(index)[offset:offset+remaining]
        if not piece:break
        fragments.append(piece)
        self.position+=len(piece);remaining-=len(piece)
    return b"".join(fragments)
def main():
    output={"checked_at":datetime.now(timezone.utc).isoformat(),
        "status":"NOT_SUPPORTED","remote_archive_full_download":False,
        "model_changed":False}
    try:
        reader=RemoteZip()
        output["declared_archive_bytes"]=reader.length
        with zipfile.ZipFile(reader) as z:
            files=[x for x in z.infolist() if not x.is_dir()]
            output["file_count"]=len(files)
            output["files"]=[{"name":x.filename,"bytes":x.file_size,
                 "compressed_bytes":x.compress_size,
                 "market_name_candidate":bool(re.search(
                     r"odds|moneyline|open|close|movement|spread",x.filename,re.I))}
                     for x in files[:500]]
            candidates=[x for x in files if re.search(
                 r"odds|moneyline|open|close|movement|spread",x.filename,re.I)]
            output["market_file_names"]=[x.filename for x in candidates[:100]]
            output["status"]="ZIP_DIRECTORY_READ"
        output["bytes_transferred"]=reader.used
    except (urllib.error.URLError,ValueError,KeyError,OSError,
            zipfile.BadZipFile,TimeoutError) as e:
        output["error_type"]=type(e).__name__
        output["error_reason"]=str(e)[:100] if isinstance(e,ValueError) else None
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(output,indent=2)+"\n")
    print("Kaggle range ZIP inventory:",output["status"],
          "files:",output.get("file_count",0),
          "bytes received:",output.get("bytes_transferred",0))
if __name__=="__main__":main()
