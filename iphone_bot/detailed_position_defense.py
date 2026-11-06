"""Five-position DvP research with lagged L5/L10/L20, minute-normalized rates.

Historical listed positions are NOT observed defender assignments. Do not
impute generic G/F/C labels into PG/SG/SF/PF/C. Features for a game's opponent
use only that defense's games strictly before the prediction date.
"""
import io
import re
import csv
import json
import urllib.request
import pandas as pd
try:
    from .position_defense import API,RAW,SEASONS,HEAD
except ImportError:
    # Direct execution from iphone_bot/ sets that directory on sys.path.
    from position_defense import API,RAW,SEASONS,HEAD

ROLES=("PG","SG","SF","PF","C")
STATS=("PTS","REB","AST","PRA")
WINDOWS=(5,10,20)
# Per-game positional points allowed (per listed player) plus per-36 rates,
# with exposure minutes, for each prior-game window.
DETAILED_COLS=tuple(
    f"DVP5_{stat}_{kind}_L{n}"
    for n in WINDOWS for stat in STATS for kind in ("AVG","PER36")
)+tuple(f"DVP5_GAMES_L{n}" for n in WINDOWS)
DETAILED_COLS+=("DVP5_ROLE_CODE",)
ROLE_CODE={name:i for i,name in enumerate(ROLES)}

def exact_role(value):
    v=str(value or "").strip().upper().replace(" ","")
    return v if v in ROLES else None

def _download(url):
    req=urllib.request.Request(url,headers=HEAD)
    with urllib.request.urlopen(req,timeout=100) as r:
        return r.read()

def fetch_exact_positions():
    items=json.loads(_download(API))
    frames=[]
    diagnostics={}
    for season in SEASONS:
        pattern=re.compile(r"^NBA_players_game_log_"+re.escape(season)+r"_as_of_(\d{4}-\d{2}-\d{2})\.csv$")
        candidates=[(m.group(1),item["name"]) for item in items
                    if (m:=pattern.fullmatch(item.get("name","")))]
        if not candidates:raise ValueError("Missing historical source for "+season)
        filename=max(candidates)[1]
        raw=list(csv.DictReader(io.StringIO(_download(RAW+filename).decode("utf-8-sig"))))
        if not raw or not {"ID","Pos","Date","Team"}.issubset(raw[0]):
            raise ValueError("Position source schema unavailable")
        counts={}
        for r in raw:
            position=str(r["Pos"]).strip().upper()
            counts[position]=counts.get(position,0)+1
            role=exact_role(position)
            if not role:continue
            frames.append({"SEASON_ID":season,"PLAYER_ID":str(r["ID"]).strip(),
                           "EXACT_ROLE":role})
        diagnostics[season]={"source":filename,"raw_position_counts":counts,
                             "records":len(raw)}
    positions=pd.DataFrame(frames)
    if positions.empty:raise ValueError("Source has no exact five-position labels")
    # A player-season must have a single unambiguous primary listed position.
    uniqueness=positions.groupby(["SEASON_ID","PLAYER_ID"])["EXACT_ROLE"].nunique()
    accepted=uniqueness[uniqueness==1].index
    stable=positions.drop_duplicates(["SEASON_ID","PLAYER_ID"]).set_index(
        ["SEASON_ID","PLAYER_ID"]).loc[accepted].reset_index()
    print("Exact position source diagnostics:",json.dumps(diagnostics),flush=True)
    print("Stable exact role counts:",stable["EXACT_ROLE"].value_counts().to_dict(),flush=True)
    return stable,diagnostics

def build_detailed_dvp(raw,positions):
    needed={"SEASON_ID","PLAYER_ID","GAME_DATE","TEAM_ABBREVIATION","MATCHUP",
            "PTS","REB","AST","MIN"}
    if not needed.issubset(raw):raise ValueError("Historical logs need minutes and stat totals")
    df=raw.copy()
    df["SEASON_ID"]=df["SEASON_ID"].astype(str)
    df["PLAYER_ID"]=df["PLAYER_ID"].astype(str).str.replace(r"\.0$","",regex=True)
    df["GAME_DATE"]=pd.to_datetime(df["GAME_DATE"])
    df["OPPONENT"]=df["MATCHUP"].astype(str).str.rsplit(" ",n=1).str[-1]
    df=df.merge(positions[["SEASON_ID","PLAYER_ID","EXACT_ROLE"]],
                on=["SEASON_ID","PLAYER_ID"],how="left",validate="many_to_one")
    df=df[df["SEASON_ID"].isin(SEASONS)].copy()
    for stat in ("PTS","REB","AST","MIN"):
        df[stat]=pd.to_numeric(df[stat],errors="coerce")
    df["PRA"]=df["PTS"]+df["REB"]+df["AST"]
    df["DVP5_ROLE_CODE"]=df["EXACT_ROLE"].map(ROLE_CODE)
    valid=df[df["EXACT_ROLE"].notna() & (df["MIN"]>0)].copy()
    group=["SEASON_ID","GAME_DATE","TEAM_ABBREVIATION","OPPONENT","EXACT_ROLE"]
    aggregations={s:(s,"sum") for s in STATS}
    aggregations.update({"TOTAL_MIN":("MIN","sum"),"ROLE_PLAYERS":("PLAYER_ID","count")})
    games=valid.groupby(group,as_index=False).agg(**aggregations)
    games=games.rename(columns={"TEAM_ABBREVIATION":"OFFENSE_TEAM",
                                "OPPONENT":"DEFENSE_TEAM"})
    # Each matchup has one positional role row per offense and date.
    if games.duplicated(["SEASON_ID","GAME_DATE","DEFENSE_TEAM","EXACT_ROLE"]).any():
        raise ValueError("Multiple games for a defense and exact position on the same date")
    games=games.sort_values(["SEASON_ID","DEFENSE_TEAM","EXACT_ROLE","GAME_DATE"])
    defense=games.groupby(["SEASON_ID","DEFENSE_TEAM","EXACT_ROLE"],sort=False)
    # Use each game's player mean and total exposure for a per-36 estimate.
    # This is observed box-score production, not actual defensive assignments.
    for stat in STATS:
        games[f"{stat}_AVG"]=games[stat]/games["ROLE_PLAYERS"]
        games[f"{stat}_PER36"]=36*games[stat]/games["TOTAL_MIN"]
    for n in WINDOWS:
        for stat in STATS:
            for kind in ("AVG","PER36"):
                name=f"DVP5_{stat}_{kind}_L{n}"
                games[name]=defense[f"{stat}_{kind}"].transform(
                    lambda x:x.shift(1).rolling(n,min_periods=max(3,n//2)).mean())
        games[f"DVP5_GAMES_L{n}"]=defense.cumcount().clip(upper=n)
    # Exact role used only to join the target offense role to opponent defense.
    right=games.rename(columns={"DEFENSE_TEAM":"OPPONENT"})
    keys=["SEASON_ID","GAME_DATE","OPPONENT","EXACT_ROLE"]
    result=df.merge(right[keys+[c for c in DETAILED_COLS if c!="DVP5_ROLE_CODE"]],
                    on=keys,how="left",validate="many_to_one")
    return result[["SEASON_ID","PLAYER_ID","GAME_DATE","TEAM_ABBREVIATION",
                   "EXACT_ROLE",*DETAILED_COLS]].copy()

def merge_detailed(training,features):
    left=training.copy()
    left["SEASON_ID"]=left["SEASON_ID"].astype(str)
    left["PLAYER_ID"]=left["PLAYER_ID"].astype(str).str.replace(r"\.0$","",regex=True)
    left["GAME_DATE"]=pd.to_datetime(left["GAME_DATE"])
    keys=["SEASON_ID","PLAYER_ID","GAME_DATE","TEAM_ABBREVIATION"]
    right=features[keys+["EXACT_ROLE",*DETAILED_COLS]]
    if right.duplicated(keys).any():raise ValueError("Duplicated detailed positional rows")
    result=left.merge(right,on=keys,how="left",validate="one_to_one")
    if len(result)!=len(training):raise ValueError("Detailed positional merge changed rows")
    return result
