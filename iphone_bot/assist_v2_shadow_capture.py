"""Lock research-only assist V2 snapshots from verified pretip AI board.

Append-only: original snapshots are never recalculated or overwritten.
"""
import json
import argparse
from datetime import datetime, timezone
from pathlib import Path
try:
    from .assist_v2_research import forecast
    from .opportunity_backtest import histories, opportunity
    from .paper_pick_pipeline import utc, expected_opponents, identity, settle, payout
except ImportError:
    from assist_v2_research import forecast
    from opportunity_backtest import histories, opportunity
    from paper_pick_pipeline import utc, expected_opponents, identity, settle, payout

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"docs/assist_v2_shadow_ledger.json"
BOARD=ROOT/"docs/ai_comparisons.json"
GAMES=ROOT/"data/nba/current/current_games.json"

def capture(board,games,existing,now=None):
    stamp=utc(now or datetime.now(timezone.utc).isoformat())
    generated=utc(board["generated_at"])
    if board.get("status")!="EXPERIMENTAL_NON_CALIBRATED" or board.get("verified_current_matchups") is not True:
        raise ValueError("Unverified AI board")
    if not 0 <= (stamp-generated).total_seconds() <= 45*60:
        raise ValueError("Board is not fresh")
    index=histories(games)
    result=list(existing)
    seen={identity({**r,"market":r.get("market","AST")}) for r in result}
    for row in board.get("comparisons",[]):
        if row.get("stat")!="AST":continue
        try:
            start=utc(row["start"])
            if stamp>=start:continue
            pid=str(row["player_id"]);team=str(row["team"])
            if not expected_opponents(row["game"],team):continue
            base=float(row["combined_projection"])
            day=start.astimezone(__import__("zoneinfo").ZoneInfo("America/New_York")).date().isoformat()
            hist=index.get((pid,team),[])
            minutes=opportunity(hist,day,team).get("expected_minutes")
            for quote in row.get("book_quotes",[]):
                line=float(quote["line"])
                key="|".join((start.isoformat(),pid,team.upper(),"AST",str(quote["name"]).casefold(),format(line,".10g")))
                if key in seen:continue
                prediction=forecast(hist,day,team,minutes,baseline=base,line=line)
                if prediction["status"]!="RESEARCH_FORECAST":continue
                if prediction["projection"]==line:continue
                side="OVER" if prediction["projection"]>line else "UNDER"
                odds=quote.get("over" if side=="OVER" else "under")
                try:payout(odds)
                except (TypeError,ValueError):continue
                result.append({"side":side,"american_odds":int(odds),"event_start":start.isoformat(),"captured_at":stamp.isoformat(),
                  "player_id":pid,"player":row["player"],"team":team,
                  "game":row["game"],"market":"AST","bookmaker":str(quote["name"]),
                  "line":line,"baseline_projection":base,
                  "v2_projection":prediction["projection"],
                  "v2_over_probability_uncalibrated":prediction["over_probability"],
                  "v2_push_probability_uncalibrated":prediction["push_probability"],
                  "over_odds":quote.get("over"),"under_odds":quote.get("under"),
                  "prior_latest_date":prediction["latest_prior_date"],
                  "status":"PENDING","paper_only":True,"model":"ASSIST_V2_SHADOW_RESEARCH",
                  "production_applied":False,"simulations":prediction["simulations"]})
                seen.add(key)
        except (KeyError,TypeError,ValueError,OverflowError):
            continue
    return result

def verified_completed_games(root=ROOT):
    """Reuse production's verified sources; never infer a final score from time."""
    try:
        from .paper_pick_pipeline import (cross_checked_final_boxscores,
            fantasydata_cross_checked_final, official_web_cross_checked_final)
    except ImportError:
        from paper_pick_pipeline import (cross_checked_final_boxscores,
            fantasydata_cross_checked_final, official_web_cross_checked_final)

    def read_array(path):
        if not path.exists():return []
        data=json.loads(path.read_text())
        if not isinstance(data,list):
            raise ValueError("Invalid completed player-game source: "+str(path))
        return data

    completed=read_array(root/"data/nba/current/current_games.json")
    completed+=read_array(root/"data/nba/current/final_boxscores.json")
    completed+=cross_checked_final_boxscores(root/"docs/verified_postgame_boxscores.json")
    completed+=fantasydata_cross_checked_final(root/"docs/verified_wizards_hawks_boxscores.json")
    completed+=official_web_cross_checked_final(root/"docs/verified_spurs_kings_boxscores.json")
    completed+=read_array(root/"data/nba/current/cbs_final_boxscores.json")
    return completed

def grade(records,completed_games,now=None):
    """Use the production verifier without changing pretip V2 predictions."""
    return settle(records,completed_games,now=now)

def summary(records):
    """One observation per event/player/stat/line; same locked V2 and baseline."""
    unique={}
    for r in sorted(records,key=lambda r:r.get("captured_at","")):
        if r.get("status")!="SETTLED":continue
        key=(utc(r["event_start"]).isoformat(),str(r["player_id"]),r["team"],
             r["market"],float(r["line"]))
        unique.setdefault(key,r)
    decisions=[r for r in unique.values() if r.get("result") in ("WIN","LOSS")]
    baseline_wins=baseline_losses=0
    v2_error=baseline_error=0.
    for r in decisions:
        actual=float(r["actual"]);line=float(r["line"])
        v2_error+=abs(float(r["v2_projection"])-actual)
        baseline_error+=abs(float(r["baseline_projection"])-actual)
        b=float(r["baseline_projection"])
        if b==line:continue
        if (actual>line)==(b>line):baseline_wins+=1
        else:baseline_losses+=1
    n=len(decisions)
    bn=baseline_wins+baseline_losses
    return {"captured":len(records),"settled":sum(r.get("status")=="SETTLED" for r in records),
            "pending":sum(r.get("status")=="PENDING" for r in records),
            "independent_settled_markets":len(unique),
            "v2_direction_eligible":n,
            "wins":sum(r["result"]=="WIN" for r in decisions),
            "losses":sum(r["result"]=="LOSS" for r in decisions),
            "hit_rate":round(sum(r["result"]=="WIN" for r in decisions)/n,4) if n else None,
            "v2_mae":round(v2_error/n,4) if n else None,
            "baseline_wins":baseline_wins,"baseline_losses":baseline_losses,
            "baseline_hit_rate":round(baseline_wins/bn,4) if bn else None,
            "baseline_mae":round(baseline_error/n,4) if n else None,
            "research_only":True,"prospective_pretip_locked":True}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--mode",choices=("capture","settle"),required=True)
    args=parser.parse_args()
    old=json.loads(OUT.read_text()).get("records",[]) if OUT.exists() else []
    if args.mode=="capture":
        if not BOARD.exists() or not GAMES.exists():
            raise RuntimeError("Missing pregame board or history")
        board=json.loads(BOARD.read_text())
        try:
            records=capture(board,json.loads(GAMES.read_text()),old)
        except ValueError as exc:
            if str(exc)!="Board is not fresh":raise
            print("SKIP_STALE_BOARD: retaining locked predictions")
            records=old
    else:
        try:
            from .fetch_final_boxscores import gather
        except ImportError:
            from fetch_final_boxscores import gather
        observed,report=gather(old)
        # A direct NBA/ESPN 403 or timeout must not block independently
        # verified CBS finals or completed CSV game logs already used by
        # the production settlement pipeline.
        completed=verified_completed_games()
        records=grade(old,completed+observed)
        print("Verified final-game fetch:",json.dumps(report,sort_keys=True),
              "additional trusted player-game rows:",len(completed))
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps({"version":1,"records":records},indent=2)+"\n")
    (ROOT/"docs/assist_v2_shadow_results.json").write_text(json.dumps(summary(records),indent=2)+"\n")
    print("V2 SHADOW:",json.dumps(summary(records),sort_keys=True))

if __name__=="__main__":main()
