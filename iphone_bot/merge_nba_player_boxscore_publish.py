"""Safe NBA player boxscore publication: reject malformed observations.

Repair only the known trailing literal backslash-n artifact from an old
workflow. All other malformed JSON fails closed. Never overwrite a newer
verified snapshot or downgrade a same-date live snapshot to pregame.
"""
import argparse
import datetime as dt
import json
from pathlib import Path

def parse(raw, *, allow_legacy_suffix=False):
    text=raw
    if allow_legacy_suffix and text.rstrip().endswith(r"\n"):
        text=text.rstrip()[:-2]
    payload=json.loads(text)
    if not isinstance(payload,dict) or not isinstance(payload.get("games"),list):
        raise ValueError("NBA_PLAYER_BOXSCORE_INVALID_SCHEMA")
    return payload

def stamp(obj):
    raw=obj.get("captured_at") or obj.get("checked_at")
    if not raw:return None
    try:
        t=dt.datetime.fromisoformat(str(raw).replace("Z","+00:00"))
        return t.astimezone(dt.timezone.utc) if t.tzinfo else None
    except (TypeError,ValueError):
        return None

def merge(old_raw,new_raw):
    new=parse(new_raw)
    old=parse(old_raw,allow_legacy_suffix=True) if old_raw is not None else None
    if stamp(new) is None:
        raise ValueError("NBA_PLAYER_BOXSCORE_INCOMING_TIMESTAMP_INVALID")
    if old:
        prior,now=stamp(old),stamp(new)
        if prior and prior>now:
            return old
        if (old.get("date_eastern")==new.get("date_eastern")
            and old.get("status")=="OBSERVED_NBA_LIVEDATA_PLAYER_BOXSCORES"
            and new.get("status")=="WAITING_FOR_SCHEDULED_TIPOFF"):
            return old
        # Never replace a populated observation with an empty/failed fetch
        # on the same day, even when the wrapper timestamp advanced.
        if (old.get("date_eastern")==new.get("date_eastern")
            and len(old["games"])>0 and not new["games"]):
            return old
    return new

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--current",required=True)
    parser.add_argument("--incoming",required=True)
    args=parser.parse_args()
    path=Path(args.current)
    new=Path(args.incoming).read_text(encoding="utf-8")
    old=path.read_text(encoding="utf-8") if path.exists() else None
    result=merge(old,new)
    path.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("Independent NBA player snapshot published:",result.get("status"),
          len(result["games"]),"games")

if __name__=="__main__":
    main()
