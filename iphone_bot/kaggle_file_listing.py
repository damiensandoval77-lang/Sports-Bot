"""Get Kaggle dataset file names through its files API (no large download)."""
import json, subprocess
from datetime import datetime,timezone
from pathlib import Path
OUT=Path("docs/kaggle_nba_file_list.json")
def main():
    data={"checked_at":datetime.now(timezone.utc).isoformat(),
          "source":"chevronronson/nba-stats-dataset",
          "status":"FILE_LIST_UNAVAILABLE","no_archive_download":True}
    try:
        p=subprocess.run(["kaggle","datasets","files",
                "chevronronson/nba-stats-dataset","--page-size","100","--csv"],
                capture_output=True,text=True,timeout=55)
        data["cli_exit_code"]=p.returncode
        if p.returncode==0 and p.stdout.strip():
            lines=p.stdout.splitlines()
            data["status"]="FILE_LIST_RECEIVED"
            data["header"]=lines[0][:600]
            data["file_listing_lines"]=[x[:700] for x in lines[1:201]]
            data["file_count_in_listing"]=max(0,len(lines)-1)
        else:
            data["status"]="CLI_LIST_FAILED"
            # stderr may include paths / credentials; avoid publishing raw error.
    except (OSError,subprocess.TimeoutExpired) as e:
        data["error_type"]=type(e).__name__
    OUT.write_text(json.dumps(data,indent=2)+"\n")
    print("Kaggle files:",data["status"],data.get("file_count_in_listing",0))
if __name__=="__main__":main()
