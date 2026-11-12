"""Recover complete, internally consistent player-games already present in public CSV.

The current-form CSV includes FGM/FGA/3PM/3PA/FTM/FTA/offensive and defensive
rebounds, but the importer previously discarded several fields. This fallback
ONLY accepts observed CSV cells with exact scoring and rebounding arithmetic.
It does not override a conflicting independently crosschecked parquet row,
and explicitly marks every recovered row as SINGLE_SOURCE (not equivalent to
a verified two-source box). No APIs or paid calls.
"""
from collections import Counter

REQUIRED=("id","team","opponent","date","player","PTS","REB","AST","MIN",
          "FGM","FGA","FG3M","FG3A","FTM","FTA","OREB","DREB","TOV")

def _clean(r):
    if any(r.get(k) is None for k in REQUIRED):return None
    pid=str(r["id"])
    team,opp=str(r["team"]),str(r["opponent"])
    date=str(r["date"])
    if not pid.isdigit() or len(team)!=3 or len(opp)!=3 or team==opp:
        return None
    if len(date)!=10 or not ("2026-10-20"<=date<="2027-06-30") or not r.get("player"):
        return None
    try:
        vals={k:float(r[k]) for k in REQUIRED if k not in
              ("id","team","opponent","date","player")}
    except (ValueError,TypeError):return None
    import math
    if any(not math.isfinite(v) or v<0 for v in vals.values()):return None
    if not (1<=vals["MIN"]<=60 and vals["PTS"]<=150 and
            vals["REB"]<=50 and vals["AST"]<=40 and vals["FGA"]<=60 and
            vals["FTA"]<=60 and vals["OREB"]<=30 and vals["TOV"]<=30):
        return None
    if not (vals["FG3M"]<=vals["FG3A"]<=vals["FGA"] and
            vals["FG3M"]<=vals["FGM"]<=vals["FGA"] and
            vals["FTM"]<=vals["FTA"]):
        return None
    # Published per-game totals must reconcile exactly before entering the
    # model as a lower-confidence single-source fallback.
    if abs(vals["PTS"]-(2*vals["FGM"]+vals["FG3M"]+vals["FTM"]))>0.01:
        return None
    if abs(vals["REB"]-(vals["OREB"]+vals["DREB"]))>0.01:
        return None
    return {**r,"id":pid,"season":"2026-27",
            "history_source_confidence":"SINGLE_SOURCE_PUBLIC_CSV_ARITHMETIC_VALIDATED"}

def recover(local,matched,secondary):
    """Append only missing player/team/date rows; conflicting parquet source
    keys are quarantined, not silently overwritten. Retain existing rows.
    """
    occupied={(str(r["id"]),r["team"],r["date"]) for r in matched}
    seen_secondary={(str(r.get("player_id") or r.get("id") or ""),
                     str(r.get("team") or "").upper(),
                     str(r.get("game_date") or r.get("date") or "")[:10])
                    for r in secondary}
    # Never use a CSV-only row where the independent parquet already claims
    # the same identity; a rejected crosscheck may indicate conflicting stats.
    groups={}
    conflicting=set()
    for raw in local:
        key=(str(raw.get("id")),str(raw.get("team")),str(raw.get("date")))
        if key in occupied or key in seen_secondary:continue
        cleaned=_clean(raw)
        if cleaned is None:continue
        prior=groups.get(key)
        if prior is not None and prior!=cleaned:conflicting.add(key)
        groups[key]=cleaned
    addition=[r for key,r in groups.items() if key not in conflicting]
    output=list(matched)+addition
    return output,{"status":"SINGLE_SOURCE_CSV_ARITHMETIC_VALIDATED",
                   "recovered":len(addition),
                   "conflicting_rows_rejected":len(conflicting),
                   "source":"public 2026-27 player game CSV",
                   "not_independently_crosschecked":True}
