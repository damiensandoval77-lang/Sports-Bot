"""Validate a rights-cleared, normalized WOWY export for local shadow research.

No API fetching. Never publish private licensed rows to docs/ or git. The
provider's own export must first be normalized to the documented schema.
The separate approval manifest is a manual record, not legal verification.
"""
import argparse
import json
import sys
from pathlib import Path

try:
    from .lineup_onoff_research import utc,positive,MARKETS,MIN_GAMES_EACH,MIN_MINUTES_EACH
except ImportError:
    from lineup_onoff_research import utc,positive,MARKETS,MIN_GAMES_EACH,MIN_MINUTES_EACH

ROOT=Path(__file__).resolve().parents[1]
FORM=ROOT/"docs/current_form.json"
PRIVATE=ROOT/"data/nba/private/lineup_onoff_research.json"
STATS=("PTS","REB","AST")

def validate(export,approval,form):
    """Fail closed on ambiguous IDs, dates, low exposure, and missing rights."""
    errors=[]
    if not isinstance(export,dict) or not isinstance(approval,dict) or not isinstance(form,dict):
        raise ValueError("Export, approval and current-form files must be JSON objects")
    if approval.get("reviewed_for_betting_analytics") is not True:
        errors.append("Manual review must affirm permitted use for betting analytics")
    if approval.get("allowed_use")!="NBA_PROP_RESEARCH":
        errors.append("Approval permitted use must include NBA_PROP_RESEARCH specifically")
    if approval.get("reviewer_confirmation")!="MANUALLY_VERIFIED":
        errors.append("Approval must explicitly be manually verified")
    if not str(approval.get("permission_reference","")).strip():
        errors.append("Missing agreement/permission reference")
    if export.get("season")!="2026-27":
        errors.append("Unsupported NBA season")
    if not str(export.get("source","")).strip():
        errors.append("Missing source identity")
    try:
        generated=utc(export["generated_at"])
    except (KeyError,TypeError,ValueError):
        generated=None
        errors.append("Export generation timestamp must have UTC offset")
    names={}
    for p in form.get("players",[]):
        pid=str(p.get("player_id",""))
        names.setdefault(pid,set()).add(p.get("team"))
    observations=[]
    seen=set()
    for idx,r in enumerate(export.get("observations",[])):
        if not isinstance(r,dict):
            errors.append(f"row {idx}: invalid object")
            continue
        pid=str(r.get("player_id",""))
        tid=str(r.get("teammate_id",""))
        team=str(r.get("team",""))
        identifier=(pid,tid,team)
        if not pid.isdecimal() or not tid.isdecimal() or pid==tid or not team:
            errors.append(f"row {idx}: bad player/teammate/team identifier")
            continue
        if team not in names.get(pid,set()) or team not in names.get(tid,set()):
            errors.append(f"row {idx}: IDs must match exact active-season roster team")
            continue
        if identifier in seen:
            errors.append(f"row {idx}: duplicate ambiguous on/off pair")
            continue
        seen.add(identifier)
        try:
            cutoff=utc(r["observed_through_at"])
            from datetime import date
            through=date.fromisoformat(r["data_through"])
            if generated is None or cutoff>generated or through>cutoff.date():
                raise ValueError("source cutoff chronology")
        except (KeyError,ValueError,TypeError):
            errors.append(f"row {idx}: unverified observation date/cutoff")
            continue
        obs={"player_id":pid,"teammate_id":tid,"team":team,
             "season":"2026-27",
             "data_through":through.isoformat(),
             "observed_through_at":cutoff.isoformat()}
        good=True
        for gname in ("with","without"):
            data=r.get(gname)
            if not isinstance(data,dict):
                errors.append(f"row {idx}: missing {gname} group")
                good=False;break
            n=data.get("games")
            exposure=positive(data.get("minutes"))
            if not isinstance(n,int) or isinstance(n,bool) or n<MIN_GAMES_EACH or exposure is None or exposure<MIN_MINUTES_EACH:
                errors.append(f"row {idx}: insufficient {gname} games/minutes")
                good=False;break
            stats={stat+"_per36":positive(data.get(stat+"_per36")) for stat in STATS}
            if any(v is None for v in stats.values()):
                errors.append(f"row {idx}: missing/invalid {gname} PTS/REB/AST per36")
                good=False;break
            obs[gname]={"games":n,"minutes":exposure,**stats}
        if good:observations.append(obs)
    if not isinstance(export.get("observations"),list) or not export["observations"]:
        errors.append("No actual provider observations present")
    if errors:raise ValueError("WOWY import refused: "+"; ".join(errors[:12]))
    return {"status":"LICENSED_ON_OFF_VERIFIED","licensed_use_verified":True,
       "source":export["source"],"generated_at":generated.isoformat(),
       "authorization":{k:approval[k] for k in
          ("reviewed_for_betting_analytics","allowed_use",
           "reviewer_confirmation","permission_reference")},
       "observations":observations}

def main(argv=None):
    parser=argparse.ArgumentParser(description="Validate pre-authorized WOWY JSON export without network requests")
    parser.add_argument("--export",type=Path,required=True)
    parser.add_argument("--approval",type=Path,required=True)
    parser.add_argument("--form",type=Path,default=FORM)
    parser.add_argument("--output",type=Path,default=PRIVATE)
    args=parser.parse_args(argv)
    output=args.output.resolve()
    if not output.is_relative_to((ROOT/"data/nba/private").resolve()):
        parser.error("Private WOWY data must remain under data/nba/private (gitignored)")
    try:
        cleaned=validate(json.loads(args.export.read_text()),
              json.loads(args.approval.read_text()),
              json.loads(args.form.read_text()))
    except (ValueError,OSError,json.JSONDecodeError) as exc:
        parser.error(str(exc))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(cleaned,indent=2)+"\n")
    print("Authorized private WOWY feed validated locally:",
          len(cleaned["observations"]),"player/teammate pairs; no API requests or public uploads")

if __name__=="__main__":main()
