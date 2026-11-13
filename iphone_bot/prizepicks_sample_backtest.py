"""Historical PrizePicks Free sample: strictly pretip, like-for-like comparison.

No live changes. Use only explicitly confirmed game logs older than target.
Closing line and final result are labels, never model features.
"""
import csv,json,math
from datetime import date,datetime
from collections import Counter,defaultdict
from statistics import mean
from pathlib import Path
FIELDS={"Points":"points","Rebounds":"rebounds","Assists":"assists"}
def value(x):
    if x in ("",None) or isinstance(x,bool):return None
    try:
        y=float(x)
        return y if math.isfinite(y) and y>=0 else None
    except (ValueError,TypeError):return None
def parsedate(x):
    try:return date.fromisoformat(str(x)[:10])
    except (ValueError,TypeError):return None
def normalized(x):return " ".join(str(x or "").casefold().split())
def evaluate(training,logs,min_games=3):
    grouped=defaultdict(dict);exclusions=Counter();joined=[]
    for game in logs:
        player=normalized(game.get("player"));team=str(game.get("team") or "").strip().upper()
        d=parsedate(game.get("game_date"))
        if not player or not team or not d or str(game.get("confirmed","")).lower() not in ("true","1","yes"):
            continue
        record=grouped[(player,team)]
        if d in record and record[d]!=game:record[d]=None
        elif d not in record:record[d]=game
    for prop in training:
        target=FIELDS.get(prop.get("stat"))
        if not target:
            exclusions["UNSUPPORTED_MARKET"]+=1;continue
        game_date=parsedate(prop.get("game_date"))
        line=value(prop.get("closing_line"));actual=value(prop.get("actual_value"))
        try:
            observed=datetime.fromisoformat(str(prop["closing_observed_at"]).replace("Z","+00:00"))
            tip=datetime.fromisoformat(str(prop["starts_at"]).replace("Z","+00:00"))
            if not observed.tzinfo or not tip.tzinfo or observed>tip:raise ValueError
        except (KeyError,TypeError,ValueError):
            exclusions["NOT_VERIFIED_PRETIP_LINE"]+=1;continue
        if game_date is None or line is None or actual is None:
            exclusions["INCOMPLETE_GRADED_PROP"]+=1;continue
        key=(normalized(prop.get("player")),str(prop.get("team") or "").strip().upper())
        history=sorted([(day,g) for day,g in grouped.get(key,{}).items()
            if day<game_date and g is not None and value(g.get(target)) is not None],
            key=lambda z:z[0])
        if len(history)<min_games:
            exclusions["INSUFFICIENT_CONFIRMED_PRIOR_GAMES"]+=1;continue
        previous=history[-5:]
        baseline=mean(value(g[target]) for _,g in previous)
        paired=[(value(g[target]),value(g.get("minutes"))) for _,g in previous]
        paired=[(y,m) for y,m in paired if y is not None and m is not None and m>0]
        candidate=(sum(y for y,m in paired)/sum(m for y,m in paired)*
            mean(m for y,m in paired)) if len(paired)>=min_games else None
        actual_side="PUSH" if actual==line else ("OVER" if actual>line else "UNDER")
        if str(prop.get("result") or "").upper()!=actual_side:
            exclusions["PROVIDER_LABEL_MISMATCH"]+=1;continue
        side=lambda x:"OVER" if x>line else "UNDER" if x<line else "NO_LEAN"
        joined.append({"player":prop.get("player"),"team":key[1],
            "stat":prop.get("stat"),"game_date":str(game_date),
            "observed_at":prop.get("closing_observed_at"),"line":line,
            "actual":actual,"prior_games":len(previous),
            "last_prior_game":str(previous[-1][0]),
            "baseline_projection":round(baseline,4),"baseline_direction":side(baseline),
            "rate_projection":round(candidate,4) if candidate is not None else None,
            "rate_direction":side(candidate) if candidate is not None else None,
            "actual_direction":actual_side,
            "baseline_abs_error":round(abs(actual-baseline),4),
            "rate_abs_error":round(abs(actual-candidate),4) if candidate is not None else None,
            "no_leakage":all(day<game_date for day,g in previous)})
    def score(prefix):
        eligible=[r for r in joined if r.get(prefix+"_direction") not in (None,"NO_LEAN") and r["actual_direction"]!="PUSH"]
        wins=sum(r[prefix+"_direction"]==r["actual_direction"] for r in eligible)
        errors=[r[prefix+"_abs_error"] for r in joined if r[prefix+"_abs_error"] is not None]
        return {"graded":len(eligible),"wins":wins,"losses":len(eligible)-wins,
                "hit_rate":round(wins/len(eligible),4) if eligible else None,
                "mae":round(mean(errors),4) if errors else None}
    return {"status":"SMALL_FREE_SAMPLE_RESEARCH_ONLY",
        "training_rows":len(training),"game_log_rows":len(logs),
        "usable_market_rows":len(joined),
        "distinct_game_dates":len({r["game_date"] for r in joined}),
        "exclusions":dict(exclusions),"baseline":score("baseline"),
        "rate_candidate":score("rate"),"verified_edge":False,
        "live_model_changed":False,
        "limitation":"Tiny selected sample; cannot establish prospective accuracy, calibration or EV.",
        "joined_rows":joined}
def csvread(path):
    with Path(path).open(newline="",encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))
def run(training,logs,out):
    report=evaluate(csvread(training),csvread(logs))
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    (out/"backtest_report.json").write_text(json.dumps(report,indent=2)+"\n")
    if report["joined_rows"]:
        with (out/"pretip_feature_joins.csv").open("w",newline="",encoding="utf-8") as f:
            writer=csv.DictWriter(f,fieldnames=list(report["joined_rows"][0]))
            writer.writeheader();writer.writerows(report["joined_rows"])
    return report
if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser();p.add_argument("training");p.add_argument("logs");p.add_argument("out")
    a=p.parse_args();result=run(a.training,a.logs,a.out)
    print(json.dumps({k:v for k,v in result.items() if k!="joined_rows"}))
