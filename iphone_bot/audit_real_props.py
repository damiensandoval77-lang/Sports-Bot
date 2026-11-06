"""Audit real NBA prop quotes against independently downloaded box scores.

No API-key use. Never equate multiple sportsbook quotes with independent games.
Produce match status and observed result only where unique player, date and
provider game ID match. If game ID formats differ, flag rather than guess.
"""
import json
import re
from collections import Counter
from pathlib import Path
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
ODDS=ROOT/"data/nba/odds/observed_props.csv"
LOGS=ROOT/"data/nba/raw/raw_game_logs.csv"
OUT=ROOT/"models/nba/real_market/quote_audit.json"
MARKETS={"PTS","REB","AST","PRA"}

def normalize(name):
    return re.sub(r"[^a-z0-9]","",str(name).casefold())

def main():
    quotes=pd.read_csv(ODDS,dtype={"game":"string"},low_memory=False)
    logs=pd.read_csv(LOGS,dtype={"GAME_ID":"string"},low_memory=False)
    required={"game_date","player_name","market","bookmaker","line",
              "over_odds","under_odds","captured_at","event_start","game"}
    missing=required-set(quotes.columns)
    if missing:raise ValueError(f"Missing quote columns: {sorted(missing)}")
    if not {"GAME_DATE","PLAYER_NAME","GAME_ID","PLAYER_ID","PTS","REB","AST"}.issubset(logs):
        raise ValueError("Box-score data missing identity/stat fields")
    quotes["game_date"]=pd.to_datetime(quotes["game_date"],errors="coerce").dt.date.astype(str)
    logs["game_date"]=pd.to_datetime(logs["GAME_DATE"],errors="coerce").dt.date.astype(str)
    quotes["name_key"]=quotes["player_name"].map(normalize)
    logs["name_key"]=logs["PLAYER_NAME"].map(normalize)
    quotes["provider_game_key"]=quotes["game"].astype("string").str.strip()
    # Verified cross-provider game ID: DunkAPI/ESPN 401810837 is UTA @ SAC,
    # NBA ID 0022500982 on March 15 2026, confirmed via NBA official box score.
    verified_ids={("2026-03-15","401810837"):"0022500982"}
    quotes["game_key"]=[verified_ids.get((date,g),g) for date,g in
                        zip(quotes["game_date"],quotes["provider_game_key"])]
    logs["game_key"]=logs["GAME_ID"].astype("string").str.strip()
    quotes["captured_at"]=pd.to_datetime(quotes["captured_at"],utc=True,errors="coerce")
    quotes["event_start"]=pd.to_datetime(quotes["event_start"],utc=True,errors="coerce")
    bad_times=quotes["captured_at"].isna()|quotes["event_start"].isna()|(
        quotes["captured_at"]>=quotes["event_start"])
    quotes["market"]=quotes["market"].astype(str).str.upper()
    quotes["line"]=pd.to_numeric(quotes["line"],errors="coerce")
    bad_quote=bad_times|~quotes.market.isin(MARKETS)|quotes.line.isna()
    # Distinguish true ID matches from same-date/name matches.
    exact=quotes.merge(logs,on=["game_date","name_key","game_key"],how="left",
                       indicator=True,suffixes=("","_box"))
    # If provider and dataset have different IDs, do not silently grade.
    found=exact["_merge"].eq("both")
    # A verified ID map must still resolve to exactly the scheduled matchup.
    # A player with a matching name on the wrong team should never be graded.
    expected_matchup={"0022500982": {"SAC","UTA"}}
    for gid,teams in expected_matchup.items():
        mask=exact["game_key"].eq(gid)&found
        if mask.any():
            matchup_ok=exact.loc[mask,"MATCHUP"].astype(str).apply(
                lambda s:any(s.startswith(t+" ") for t in teams) and
                any(s.endswith(t) for t in teams))
            found.loc[mask] = matchup_ok.to_numpy()
    ambiguous=exact.duplicated(["game_date","name_key","game_key","market","bookmaker","line","captured_at"],keep=False)
    eligible=found&~ambiguous&~bad_quote.reindex(exact.index,fill_value=True)
    graded=exact.loc[eligible].copy()
    if len(graded):
        graded["ACTUAL_PRA"]=graded["PTS"]+graded["REB"]+graded["AST"]
        graded["actual"]=graded.apply(lambda r:r["ACTUAL_PRA"] if r["market"]=="PRA" else r[r["market"]],axis=1)
        graded["over_hit"]=graded["actual"]>graded["line"]
        graded["under_hit"]=graded["actual"]<graded["line"]
    uniq=len(quotes[["game_date","name_key","game_key","market"]].drop_duplicates())
    examples=[]
    for _,row in graded.head(8).iterrows():
        examples.append({"player":row["player_name"],"market":row["market"],
                         "line":float(row["line"]),"actual":float(row["actual"]),
                         "bookmaker":row["bookmaker"]})
    # Name/date match is only diagnostic; NOT enough to count as matched.
    nd=quotes.merge(logs[["game_date","name_key","game_key"]].drop_duplicates(),
        on=["game_date","name_key"],how="left",suffixes=("","_box"))
    report={
        "quotes":int(len(quotes)),
        "unique_player_game_market_outcomes":int(uniq),
        "unique_games_quoted":int(quotes[["game_date","game_key"]].drop_duplicates().shape[0]),
        "unique_players_quoted":int(quotes.name_key.nunique()),
        "bookmakers":sorted(quotes.bookmaker.dropna().astype(str).unique().tolist()),
        "invalid_time_or_market_quotes":int(bad_quote.sum()),
        "verified_cross_provider_game_ids":{"401810837":"0022500982"},
        "exact_or_verified_game_id_player_date_matches":int(found.sum()),
        "unambiguous_graded_quotes":int(len(graded)),
        "name_date_potential_matches_NOT_GRADED":int(nd["game_key_box"].notna().sum()),
        "different_game_id_examples":[{"player":r["player_name"],"provider_game_id":str(r["game_key"]),
                "box_score_game_id":str(r["game_key_box"])} for _,r in
                nd.loc[nd.game_key_box.notna() & (nd.game_key!=nd.game_key_box)].head(5).iterrows()],
        "graded_examples":examples,
        "warning":"Cross-provider ID mapping is verified for UTA @ SAC only. Multiple books quote same outcomes. No profitability estimate."
    }
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2),flush=True)
    if len(graded)==0:
        print("NO VALIDATED RESULTS: check game-ID mapping and player attribution before spending any more credits.",flush=True)

if __name__=="__main__":
    main()
