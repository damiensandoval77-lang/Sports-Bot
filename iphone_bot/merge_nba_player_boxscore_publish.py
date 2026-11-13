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

def game_key(game):
    """Stable official event ID; only use the matchup when ID is unavailable."""
    if game.get("id") is not None:
        return "id:"+str(game["id"])
    if game.get("game"):
        return "game:"+str(game["game"])
    raise ValueError("NBA_PLAYER_BOXSCORE_GAME_IDENTITY_MISSING")

def game_observed(game,parent):
    """Do not mark retained old games fresh with the new wrapper timestamp."""
    return stamp({"captured_at":game.get("observed_at")}) or stamp(parent)

def merge(old_raw,new_raw):
    new=parse(new_raw)
    old=parse(old_raw,allow_legacy_suffix=True) if old_raw is not None else None
    if stamp(new) is None:
        raise ValueError("NBA_PLAYER_BOXSCORE_INCOMING_TIMESTAMP_INVALID")
    if not old:return new
    prior_time,new_time=stamp(old),stamp(new)
    if prior_time and prior_time>new_time:
        return old
    if (old.get("date_eastern")==new.get("date_eastern")
        and old.get("status")=="OBSERVED_NBA_LIVEDATA_PLAYER_BOXSCORES"
        and new.get("status")=="WAITING_FOR_SCHEDULED_TIPOFF"):
        return old
    if old.get("date_eastern")!=new.get("date_eastern"):
        # Different dates are not combined: old finals belong to their date.
        return new
    if old["games"] and not new["games"]:
        # An unavailable/empty fetch is never allowed to erase observations.
        return old

    # A partial valid run is valuable but cannot erase other games from the
    # same Eastern slate. Keep each game with its original observed timestamp
    # and take only a genuinely newer observation for that exact identity.
    by_id={}
    matchup_ids={}
    for game in old["games"]:
        if not isinstance(game,dict):raise ValueError("NBA_PLAYER_BOXSCORE_INVALID_GAME")
        k=game_key(game)
        if k in by_id:raise ValueError("NBA_PLAYER_BOXSCORE_DUPLICATE_GAME")
        by_id[k]=game
        if game.get("game") and game.get("id") is not None:
            matchup_ids[str(game["game"])]=str(game["id"])
    incoming_ids=set()
    rejected_observations=set()
    for game in new["games"]:
        if not isinstance(game,dict):raise ValueError("NBA_PLAYER_BOXSCORE_INVALID_GAME")
        k=game_key(game)
        if k in incoming_ids:raise ValueError("NBA_PLAYER_BOXSCORE_DUPLICATE_GAME")
        incoming_ids.add(k)
        if game.get("game") and game.get("id") is not None:
            previous_id=matchup_ids.get(str(game["game"]))
            if previous_id and previous_id!=str(game["id"]):
                raise ValueError("NBA_PLAYER_BOXSCORE_GAME_ID_MISMATCH")
        prior=by_id.get(k)
        if prior is not None:
            if prior.get("game") and game.get("game") and prior["game"]!=game["game"]:
                raise ValueError("NBA_PLAYER_BOXSCORE_GAME_IDENTITY_CONFLICT")
            # Never turn a final verified box back into a live snapshot.
            if prior.get("state") in ("post","final") and game.get("state")=="in":
                rejected_observations.add(k)
                continue
            # An empty or older observation cannot overwrite real player rows.
            if prior.get("player_rows") and not game.get("player_rows"):
                rejected_observations.add(k)
                continue
            older=game_observed(prior,old)
            current=game_observed(game,new)
            if older and current and older>current:
                rejected_observations.add(k)
                continue
        by_id[k]=game
    merged={**new,"games":list(by_id.values())}
    retained=sum(1 for k in by_id if k not in incoming_ids or k in rejected_observations)
    # The original source's coverage flags cannot be promoted to complete when
    # missing games were rescued from an older run.
    coverage={**(new.get("coverage") or {})}
    coverage["observed_game_count"]=len(merged["games"])
    coverage["retained_prior_game_count"]=retained
    coverage["complete"]=bool(coverage.get("complete") and retained==0)
    merged["coverage"]=coverage
    if retained:
        merged["status"]="PARTIAL_NBA_PLAYER_BOXSCORES"
        errors=list(new.get("errors") or [])
        if "RETAINED_PRIOR_OBSERVATIONS" not in errors:
            errors.append("RETAINED_PRIOR_OBSERVATIONS")
        merged["errors"]=errors
    return merged

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
