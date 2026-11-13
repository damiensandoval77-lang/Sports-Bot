"""Strict externally sourced *pregame* matchup context contract.

This is a validation/gating layer, NOT an inference or data collection client.
It accepts only caller-provided research records with event-specific provenance;
postgame lineup absences, implied defenders and unlicensed usage are not
silently substituted. Current trained model does not consume these covariates.
"""
from datetime import datetime,timezone
import math

class ContextRejected(ValueError):
    pass

def utc(x):
    try:
        t=datetime.fromisoformat(str(x).replace("Z","+00:00"))
        if t.tzinfo is None or t.utcoffset() is None:raise ValueError
        return t.astimezone(timezone.utc)
    except (ValueError,TypeError) as exc:
        raise ContextRejected("Timezone-aware source timestamps required") from exc

def context(row,*,player_id,team,opponent,game_id,event_start,as_at):
    if not isinstance(row,dict):raise ContextRejected("Missing context record")
    cutoff=utc(as_at)
    tip=utc(event_start)
    if cutoff>=tip:raise ContextRejected("After-tip capture rejected")
    for k,v in (("player_id",player_id),("team",team),("opponent",opponent),("game_id",game_id)):
        if not str(v).strip() or str(row.get(k) or "")!=str(v):
            raise ContextRejected("Mismatch in "+k)
    status={"status":"VERIFIED_PREGAME_CONTEXT_AUDIT",
            "recorded_before_tip":True,"usage_pct":None,
            "verified_out_player_ids":[],
            "position_role":None,"position_defense_sample":None,
            "apply_to_trained_matchup_model":False,
            "reason_codes":[]}
    def eligible(k,allowed_sources):
        field=row.get(k)
        if field is None:return None
        if not isinstance(field,dict):raise ContextRejected(k+" must carry source metadata")
        if field.get("source") not in allowed_sources:
            status["reason_codes"].append(k.upper()+"_SOURCE_UNVERIFIED")
            return None
        if field.get("rights_confirmed") is not True:
            status["reason_codes"].append(k.upper()+"_RIGHTS_UNVERIFIED")
            return None
        t=utc(field.get("published_at"))
        if t>cutoff or t>=tip:
            status["reason_codes"].append(k.upper()+"_NOT_AVAILABLE_AT_CAPTURE")
            return None
        if field.get("game_id")!=game_id:
            status["reason_codes"].append(k.upper()+"_GAME_MISMATCH")
            return None
        return field
    use=eligible("usage",{"LICENSED_PLAYER_USAGE","OFFICIAL_NBA_ADVANCED"})
    if use is not None:
        try: val=float(use["pct"])
        except (KeyError,ValueError,TypeError): val=math.nan
        if math.isfinite(val) and 0<=val<=100:
            status["usage_pct"]=val
        else:status["reason_codes"].append("USAGE_INVALID")
    injuries=eligible("injuries",{"OFFICIAL_NBA_INJURY_REPORT"})
    if injuries is not None:
        if injuries.get("team")!=team:
            status["reason_codes"].append("INJURY_TEAM_MISMATCH")
        else:
            out=injuries.get("out_player_ids",[])
            if isinstance(out,list) and all(str(x).strip() for x in out):
                status["verified_out_player_ids"]=sorted(set(map(str,out)))
            else:status["reason_codes"].append("INJURY_INVALID_OUT_LIST")
    role=eligible("position",{"LICENSED_ROLE_DATA","OFFICIAL_NBA_ROSTER"})
    if role is not None and role.get("player_id")==str(player_id):
        v=role.get("role")
        if v in ("G","F","C"):status["position_role"]=v
        else:status["reason_codes"].append("ROLE_UNSUPPORTED")
    defense=eligible("position_defense",{"LICENSED_POSITION_ALLOWANCE"})
    if defense is not None:
        if defense.get("opponent")!=opponent or defense.get("role")!=status["position_role"]:
            status["reason_codes"].append("DVP_ROLE_OR_TEAM_MISMATCH")
        else:
            sample=defense.get("sample_games")
            try: sample=int(sample)
            except (TypeError,ValueError): sample=0
            if sample>=5 and defense.get("latest_game_date","")<tip.date().isoformat():
                status["position_defense_sample"]=sample
            else:status["reason_codes"].append("DVP_NOT_SAFELY_SAMPLED")
    return status
