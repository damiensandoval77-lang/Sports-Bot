"""Lock a coherent PRA research challenger beside original, independent PRA.

This is not an automatic fix: PTS, REB, AST and PRA use separately trained
estimators; coherence is a hypothesis. Freeze additive challenger pretip and
grade later against an observed final, without altering the original model.
"""
import json
from datetime import datetime,timezone
from pathlib import Path
try:
    from .cross_market_coherence import number
except ImportError:
    from cross_market_coherence import number

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"docs/ai_projection_fallback.json"
PREGAME_ARCHIVE=ROOT/"docs/ai_no_line_pregame_archive.json"
ARCHIVE=ROOT/"docs/pra_coherence_shadow.json"

def iso(value):
    d=datetime.fromisoformat(str(value).replace("Z","+00:00"))
    if d.tzinfo is None:raise ValueError("timezone required")
    return d.astimezone(timezone.utc)

def candidates(predictions):
    groups={}
    for p in predictions:
        try:
            k=(str(p["start"]),str(p["game"]),str(p["player_id"]),
               str(p["team"]),str(p["captured_at"]))
            stat=p["stat"]
            if stat not in ("PTS","REB","AST","PRA"):continue
            if iso(p["captured_at"])>=iso(p["start"]):continue
            val=number(p.get("projection"))
            if val is None:continue
            group=groups.setdefault(k,{})
            if stat in group and group[stat]!=val:
                group["invalid"]=True
            else:group[stat]=val
        except (KeyError,TypeError,ValueError):continue
    output=[]
    for k,vals in sorted(groups.items()):
        if vals.get("invalid") or not all(s in vals for s in ("PTS","REB","AST","PRA")):
            continue
        additive=round(vals["PTS"]+vals["REB"]+vals["AST"],3)
        original=round(vals["PRA"],3)
        output.append({"event_start":k[0],"game":k[1],"player_id":k[2],
             "team":k[3],"captured_at":k[4],
             "original_pra_forecast":original,"additive_pra_forecast":additive,
             "difference":round(additive-original,3),
             "original_frozen_pretip":True,
             "challenger_derived_from_frozen_pretip_components":True,
             "research_only":True,"live_model_applied":False})
    return output

def merge(old,new):
    bykey={}
    for row in old:
        try:
            key=(row["event_start"],row["game"],str(row["player_id"]),row["team"],row["captured_at"])
            if not row.get("original_frozen_pretip"):continue
            if iso(row["captured_at"])>=iso(row["event_start"]):continue
            if number(row["original_pra_forecast"]) is None or number(row["additive_pra_forecast"]) is None:continue
            bykey[key]=row
        except (KeyError,TypeError,ValueError):continue
    for row in new:
        key=(row["event_start"],row["game"],str(row["player_id"]),row["team"],row["captured_at"])
        bykey.setdefault(key,row)
    return [bykey[k] for k in sorted(bykey)]

def main():
    obj=json.loads(SOURCE.read_text())
    # Archive current standalone model forecasts only if they were captured
    # prior to the exact event, never infer a game outcome or bookmaker line.
    live=obj.get("predictions",[])
    locked=json.loads(PREGAME_ARCHIVE.read_text()).get("predictions",[])
    old=json.loads(ARCHIVE.read_text()).get("records",[]) if ARCHIVE.exists() else []
    # Derived from already-frozen pretip component estimates; capture is
    # retrospective arithmetic, not a backdated newly trained model forecast.
    data=merge(old,candidates(locked+live))
    report={"status":"RESEARCH_ONLY_ADD_COMPONENTS_PRA_CHALLENGER",
            "updated_at":datetime.now(timezone.utc).isoformat(),
            "records":data,"original_pra_changed":False,
            "calibrated_probability_available":False,
            "original_pra_vs_additive_accuracy_not_established":True,
            "archive_derivation_is_retrospective_arithmetic":True,
            "warning":"Additive PRA is a pregame challenger, not a verified improvement or bet recommendation"}
    ARCHIVE.write_text(json.dumps(report,indent=2)+"\n")
    print("PRA ADDITIVE SHADOW",len(data),"frozen paired forecasts")

if __name__=="__main__":main()
