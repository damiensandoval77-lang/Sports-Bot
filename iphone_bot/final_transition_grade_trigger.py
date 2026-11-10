"""One-shot grade wake-up when ESPN scoreboard + matching summary first say final.

This signal never carries a grade or a box-score actual; the separately
executed grader must independently verify final NBA/ESPN player rows.
"""
import argparse
import json
from pathlib import Path

def new_finals(current,previous):
    if current.get("status")!="OBSERVED_ESPN_LIVE_BOX_SCORES_SERVER_FALLBACK":
        return []
    def valid(g,source):
        return (isinstance(g,dict) and source.get("date_eastern")==
                current.get("date_eastern") and g.get("state")=="post" and
                g.get("stale") is False and str(g.get("event_id","")).isdigit() and
                bool(g.get("game")) and bool(g.get("player_rows")) and
                g.get("observed_at")==source.get("captured_at"))
    before={str(g["event_id"]) for g in previous.get("games",[])
            if valid(g,previous)} if previous.get("status")==current.get("status") else set()
    return sorted({str(g["event_id"]) for g in current.get("games",[])
                   if valid(g,current) and str(g["event_id"]) not in before})

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--current",required=True)
    parser.add_argument("--previous",required=True)
    args=parser.parse_args()
    def load(path):
        try:return json.loads(Path(path).read_text())
        except (OSError,ValueError,TypeError):return {}
    changed=new_finals(load(args.current),load(args.previous))
    print("NEW VERIFIED OBSERVED FINAL GAME ID HINTS:",",".join(changed))
    return 0 if changed else 1

if __name__=="__main__":
    raise SystemExit(main())
