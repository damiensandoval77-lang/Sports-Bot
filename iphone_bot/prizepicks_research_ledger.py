"""Freeze and grade independent PrizePicks AI research against completed player logs.

Separate from paid sportsbook ledger. Only pre-tip snapshots already published
and time-stamped before an NBA matchup are eligible. No imagined prices, no
retrospective changes to forecasts, no false ROI or hit probabilities.
"""
import json
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"docs/prizepicks_ai_research.json"
LEDGER=ROOT/"docs/prizepicks_research_ledger.json"
RESULTS=ROOT/"docs/prizepicks_research_results.json"
CURRENT=ROOT/"data/nba/current/current_games.json"
SUPPORTED=("PTS","REB","AST","PRA")

def utc(s):
    try:
        v=datetime.fromisoformat(str(s).replace("Z","+00:00"))
        return v.astimezone(timezone.utc) if v.tzinfo is not None else None
    except (ValueError,TypeError):return None

def identity(row):
    return "|".join(str(row.get(k,"")) for k in (
        "provider_projection_id","player_id","team","game","start","stat","line"))

def freeze(existing,source):
    records={identity(x):x for x in existing.get("records",[]) if identity(x)}
    added=0
    snapshot=utc(source.get("generated_at"))
    if source.get("status")!="PRIZEPICKS_AI_RESEARCH_ONLY_NOT_SPORTSBOOK_ODDS" or not snapshot:
        return {"records":list(records.values()),"new":0}
    for row in source.get("comparisons",[]):
        start=utc(row.get("start"))
        captured=utc(row.get("captured_at"))
        if not start or not captured or start<=snapshot or start<=captured:continue
        try:
            fields=("provider_projection_id","player_id","player","team","game",
                    "start","stat","line","combined_projection","original_projection")
            if any(row.get(x) in (None,"") for x in fields):continue
            if row["stat"] not in SUPPORTED or len(str(row["team"]))!=3:continue
            if not 0<=float(row["line"])<300:continue
            if not 0<=float(row["combined_projection"])<300:continue
            if not 0<=float(row["original_projection"])<300:continue
            stored={k:row.get(k) for k in fields}
            stored.update({
                "opponent_aware_projection":row.get("opponent_aware_projection"),
                "observed_at":row.get("observed_at"),
                "captured_at":row["captured_at"],
                "snapshot_generated_at":source["generated_at"],
                "source":"PUBLISHED_PRETIP_PRIZEPICKS_AI_RESEARCH",
                "status":"PENDING",
                "actual":None,"result":None,
                "settlement_source":None,
                "not_sportsbook_odds":True,"verified_ev":False})
            key=identity(stored)
            if key not in records:
                records[key]=stored
                added+=1
        except (TypeError,ValueError):continue
    return {"records":list(records.values()),"new":added}

def settle(ledger,games,now=None):
    now=now or datetime.now(timezone.utc)
    games_by={}
    for g in games:
        try:
            player=str(g.get("id") or g.get("player_id"))
            team=str(g["team"]).upper()
            date=str(g["date"])
            if not player or not team or not date:continue
            key=(player,team,date)
            if key in games_by and games_by[key]!=g:
                games_by[key]=None
            elif key not in games_by:games_by[key]=g
        except (KeyError,TypeError):continue
    out=[]
    for record in ledger.get("records",[]):
        row=dict(record)
        if row.get("status")=="SETTLED":
            out.append(row)
            continue
        if row.get("status")!="PENDING":
            out.append(row)
            continue
        start=utc(row.get("start"))
        if not start or now<start:
            out.append(row)
            continue
        date=start.astimezone(ZoneInfo("America/New_York")).date().isoformat()
        actual_row=games_by.get((str(row.get("player_id")),str(row.get("team")).upper(),date))
        if not actual_row:
            out.append(row)
            continue
        # Verify the actual opponent matches the original, exact scheduled game.
        try:
            from .paper_pick_pipeline import expected_opponents
        except ImportError:
            from paper_pick_pipeline import expected_opponents
        expected=expected_opponents(row.get("game"),row.get("team"))
        if not expected or str(actual_row.get("opponent","")).upper() not in expected:
            out.append(row)
            continue
        try:
            value=float(actual_row[row["stat"]])
            if not 0<=value<300:raise ValueError
            line=float(row["line"])
            prediction=float(row["combined_projection"])
        except (KeyError,TypeError,ValueError):
            out.append(row)
            continue
        result="PUSH" if value==line else (
            "WIN" if (prediction>line and value>line) or
                     (prediction<line and value<line) else
            "LOSS" if prediction!=line else "NO_LEAN")
        row.update(status="SETTLED",actual=value,result=result,
                   settlement_source="HISTORICAL_CSV_COMPLETED_GAME",
                   settled_game_date=date)
        out.append(row)
    return {"records":out}

def summarize(ledger,now=None):
    now=now or datetime.now(timezone.utc)
    rows=ledger.get("records",[])
    settled=[r for r in rows if r.get("status")=="SETTLED"]
    eligible=[r for r in settled if r.get("result") in ("WIN","LOSS")]
    by={}
    for stat in SUPPORTED:
        group=[r for r in eligible if r.get("stat")==stat]
        by[stat]={"graded":len(group),"wins":sum(r["result"]=="WIN" for r in group),
                  "hit_rate":round(sum(r["result"]=="WIN" for r in group)/len(group),4) if group else None,
                  "distinct_game_dates":len({r.get("settled_game_date") for r in group})}
    return {"status":"PRIZEPICKS_PRETIP_RESEARCH_GRADED_NOT_ODDS",
            "updated_at":now.isoformat(),"saved":len(rows),
            "settled":len(settled),"pending":sum(r.get("status")=="PENDING" for r in rows),
            "independent_player_market_count":len({(r.get("player_id"),r.get("game"),r.get("stat"))
                   for r in rows}),
            "by_market":by,"wager_roi":None,"verified_ev":False,
            "notice":"Research-only pregame directions; multiple PrizePicks thresholds are correlated and not independent observations."}

def main():
    old=json.loads(LEDGER.read_text()) if LEDGER.exists() else {"records":[]}
    source=json.loads(SOURCE.read_text()) if SOURCE.exists() else {}
    frozen=freeze(old,source)
    games=json.loads(CURRENT.read_text()) if CURRENT.exists() else []
    graded=settle(frozen,games)
    if (graded["records"]==old.get("records",[]) and LEDGER.exists() and
        RESULTS.exists()):
        print("PrizePicks research ledger unchanged; no redundant publication")
        return
    graded["updated_at"]=datetime.now(timezone.utc).isoformat()
    LEDGER.parent.mkdir(parents=True,exist_ok=True)
    LEDGER.write_text(json.dumps(graded,indent=2)+"\n")
    RESULTS.write_text(json.dumps(summarize(graded),indent=2)+"\n")
    print("PrizePicks research ledger:",len(graded["records"]),
          "new:",frozen["new"],"settled:",
          sum(r.get("status")=="SETTLED" for r in graded["records"]))
if __name__=="__main__":main()
