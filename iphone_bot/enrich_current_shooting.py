"""Safely enrich local 2026-27 NBA player games with verified shot makes.

Separate authorized public parquet. No rewriting published observed form,
no overwrite of baseline game stats, no model promotion or odds fetching.
Require exact player ID, team and date plus matching points/rebounds/assists.
Reject conflicting duplicates and impossible scoring totals.
"""
import json,math
from collections import defaultdict
from datetime import date,datetime,timezone
from io import BytesIO
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
GAMES=ROOT/"data/nba/current/current_games.json"
STATUS=ROOT/"docs/current_shooting_coverage.json"
URL=("https://huggingface.co/datasets/cbratkovics/nba-game-logs/"
     "resolve/main/game_logs/game_logs_2026-27.parquet")
COLS={"FGM":"fgm","FG3M":"fg3m","FTM":"ftm","FTA":"fta",
      "FGA":"fga","FG3A":"fg3a"}
ALIASES={"SAN":"SAS","PHO":"PHX","BRK":"BKN","NO":"NOP","NY":"NYK","GS":"GSW"}
def finite(x):
    if x is None or isinstance(x,bool):return None
    try:
        v=float(x)
        return v if math.isfinite(v) and v>=0 else None
    except (ValueError,TypeError):return None
def keyed(row):
    pid=str(row.get("id") or row.get("player_id") or "")
    d=str(row.get("date") or row.get("game_date") or "")[:10]
    team=ALIASES.get(str(row.get("team") or "").strip().upper(),
                     str(row.get("team") or "").strip().upper())
    return pid,d,team
def overlay(local, source, today=None):
    today=today or date.today()
    indexed={};conflicts=set()
    reject=defaultdict(int)
    for row in source:
        k=keyed(row)
        try:
            d=date.fromisoformat(k[1])
        except ValueError:
            reject["INVALID_DATE"]+=1;continue
        if not k[0].isdigit() or len(k[2])!=3 or d>today:
            reject["WRONG_ID_OR_FUTURE_GAME"]+=1;continue
        if str(row.get("season","2026-27"))!="2026-27":
            reject["WRONG_SEASON"]+=1;continue
        shots={k2:finite(row.get(v)) for k2,v in COLS.items()}
        if any(v is None for v in shots.values()):
            reject["INCOMPLETE_SHOOTING"]+=1;continue
        m=finite(row.get("minutes"))
        if m is None or not 0<m<=60 or shots["FGM"]>shots["FGA"] or shots["FG3M"]>shots["FG3A"] or shots["FG3M"]>shots["FGM"] or shots["FTM"]>shots["FTA"]:
            reject["IMPOSSIBLE_ATTEMPTS"]+=1;continue
        two_m=shots["FGM"]-shots["FG3M"]
        if two_m>shots["FGA"]-shots["FG3A"]:
            reject["IMPOSSIBLE_TWO_POINT_MAKES"]+=1;continue
        pts=2*two_m+3*shots["FG3M"]+shots["FTM"]
        if abs(pts-float(row.get("pts",-999)))>.001:
            reject["SCORING_IDENTITY_MISMATCH"]+=1;continue
        normalized={**shots,"PTS":pts,
           "REB":finite(row.get("reb")),"AST":finite(row.get("ast")),
           "MIN":m,"opponent":ALIASES.get(str(row.get("opponent","")).upper(),
                                           str(row.get("opponent","")).upper())}
        if any(normalized[x] is None for x in ("REB","AST")):
            reject["MISSING_BOX_SCORE"]+=1;continue
        if k in indexed and indexed[k]!=normalized:conflicts.add(k)
        else:indexed[k]=normalized
    results=[]
    matched=0
    for row in local:
        changed=dict(row)
        key=keyed(row)
        candidate=indexed.get(key)
        if key in conflicts:
            reject["CONFLICTING_SOURCE_DUPLICATE"]+=1
        elif candidate is not None:
            if (any(finite(row.get(stat)) is None or
                abs(finite(row[stat])-candidate[stat])>.001
                for stat in ("PTS","REB","AST")) or
                (finite(row.get("MIN")) is None or
                 abs(finite(row["MIN"])-candidate["MIN"])>2.5) or
                (row.get("opponent") and
                 str(row["opponent"]).upper()!=candidate["opponent"]) or
                (finite(row.get("FGA")) is not None and
                 abs(finite(row["FGA"])-candidate["FGA"])>.001) or
                (finite(row.get("FG3A")) is not None and
                 abs(finite(row["FG3A"])-candidate["FG3A"])>.001)):
                reject["CROSS_SOURCE_BOX_SCORE_MISMATCH"]+=1
            else:
                for stat in COLS:changed[stat]=candidate[stat]
                changed["shooting_source"]="CROSSCHECKED_HF_PLAYER_GAME_BOX_SCORE"
                matched+=1
        results.append(changed)
    health={"status":"MATCHED_SHOOTING_AVAILABLE" if matched else "NO_MATCHES",
        "completed_local_rows":len(local),"source_valid_rows":len(indexed),
        "matched_player_games":matched,
        "source_rejections":dict(reject),
        "source_url":URL,
        "source_format":"2026-27 game-level parquet (personal research use)",
        "source_contains_only_observed_completed_game_shooting":True,
        "no_same_or_future_game_features_allowed":True,
        "live_model_changed":False,"archive_to_public_repository":False}
    return results,health
def main():
    import pandas as pd,requests
    if not GAMES.exists():raise FileNotFoundError("No current player logs to enrich")
    raw=json.loads(GAMES.read_text())
    r=requests.get(URL,timeout=(12,45),headers={"User-Agent":"SportsBot-Shooting-Research/1.0"})
    r.raise_for_status()
    if len(r.content)>8_000_000:raise ValueError("Shooting source unexpectedly oversized")
    df=pd.read_parquet(BytesIO(r.content))
    need={"player_id","game_date","season","team","opponent","minutes",
          "pts","reb","ast",*COLS.values()}
    if not need.issubset(df.columns):raise ValueError("Missing required shooting fields")
    df["date"]=pd.to_datetime(df["game_date"],errors="raise").dt.strftime("%Y-%m-%d")
    df["id"]=df["player_id"].astype(str)
    enriched,health=overlay(raw,df.to_dict(orient="records"))
    health["updated_at"]=datetime.now(timezone.utc).isoformat()
    GAMES.write_text(json.dumps(enriched))
    STATUS.parent.mkdir(parents=True,exist_ok=True)
    STATUS.write_text(json.dumps(health,indent=2)+"\n")
    print("Validated shooting player-games:",health["matched_player_games"],
          "of",health["completed_local_rows"],"cross-source boxes")
if __name__=="__main__":main()
