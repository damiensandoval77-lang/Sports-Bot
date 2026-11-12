"""Compare deployed Dame's Picks feeds with game schedule and frozen records."""
import datetime as dt
import json
import sys
import urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo
ET = ZoneInfo("America/New_York")

SITE="https://damiensandoval77-lang.github.io/Sports-Bot"
FILES=["prizepicks.json","prizepicks_site.json","lagged_matchup_all_market_ledger.json",
       "lagged_matchup_live_all_markets.json","nba_schedule.json",
       "nba_scoreboard_independent.json","nba_player_tracking_independent.json",
       "tonight_capture_gradeability.json","pregame_lifecycle_readiness.json",
       "nightly_grade_health.json"]
REPAIR={"lines_publish":"nba-prizepicks-site-publish.yml",
        "picks_frozen":"nba-new-ai-all-markets.yml",
        "live_scores":"independent_scoreboard_refresh.yml",
        "live_players":"independent_nba_player_boxscores.yml",
        "settlement":"nba-new-ai-multimarket-grade.yml"}
def ts(value):
    try:
        v=dt.datetime.fromisoformat(str(value).replace("Z","+00:00"))
        return v if v.tzinfo else v.replace(tzinfo=dt.timezone.utc)
    except (ValueError,TypeError):return None
def age(now,value):
    v=ts(value)
    return (now-v).total_seconds()/60 if v else None
def check(name,status,detail,recovery_workflow="DEFAULT",**evidence):
    recovery = REPAIR.get(name) if recovery_workflow == "DEFAULT" else recovery_workflow
    return {"stage":name,"status":status,"detail":detail,"recovery_workflow":recovery,"evidence":evidence}
def evaluate(now,site,espn=None):
    """Fail closed on verified missing sources; show uncertainty as WARN.

    A model can succeed while individual markets are missing, and a line
    collector can fail before any game appears in the line set. Therefore
    schedule coverage is evaluated independently of source and model success.
    """
    out=[]
    pp=site.get("prizepicks.json") or {}
    published=site.get("prizepicks_site.json") or {}
    ledger=site.get("lagged_matchup_all_market_ledger.json") or {}
    ledger_available=isinstance(ledger.get("records"),list)
    ledger_records=ledger["records"] if ledger_available else []
    model=site.get("lagged_matchup_live_all_markets.json") or {}
    schedule=site.get("nba_schedule.json") or {}
    capture=site.get("tonight_capture_gradeability.json") or {}
    readiness=site.get("pregame_lifecycle_readiness.json") or {}
    schedule_games=[g for g in schedule.get("games",[]) if isinstance(g,dict) and g.get("game") and ts(g.get("start"))]
    if not schedule_games:
        out.append(check("schedule","FAIL","Published NBA schedule is missing or unreadable",
                         schedule_status=schedule.get("status"),games=0))
    else:
        out.append(check("schedule","OK" if schedule.get("coverage_complete") is True else "WARN",
                         "Published official season schedule",
                         schedule_status=schedule.get("status"),games=len(schedule_games),
                         coverage_complete=schedule.get("coverage_complete")))
    soon=[]
    for game in schedule_games:
        start=ts(game["start"])
        if -3*3600 <= (start-now).total_seconds() <=6*3600:
            soon.append((game["game"],start,game.get("date_eastern")))
    pretip=[(g,s,d) for g,s,d in soon if 0 <= (s-now).total_seconds() <=6*3600]
    p_at=ts(pp.get("generated_at"))
    s_at=ts(published.get("source_generated_at") or published.get("generated_at"))
    lag=(p_at-s_at).total_seconds()/60 if p_at and s_at else None
    publish_bad=not s_at or (p_at is not None and lag is not None and lag>45)
    out.append(check("lines_publish","FAIL" if publish_bad else "OK",
                     "Published line snapshot freshness",
                     provider_generated_at=pp.get("generated_at"),
                     published_at=published.get("source_generated_at") or published.get("generated_at"),
                     lag_minutes=lag))
    a=age(now,pp.get("generated_at"))
    stale_source=bool(pretip and (a is None or a>240))
    out.append(check("lines_fresh","WARN" if stale_source else "OK",
                     "Source line age; paid provider refresh is alert-only",
                     age_minutes=a,upcoming=len(pretip)))
    board=[v for d in (pp,published) for v in d.get("board_offers",[])
           if isinstance(v,dict) and v.get("game")
           and v.get("more_tier")=="standard" and v.get("less_tier")=="standard"]
    # Exact date pairing prevents yesterday's quotes on the same matchup from
    # satisfying today's game. A missing start is not evidence of coverage.
    def has_lines(game,start):
        return any(x.get("game")==game and ts(x.get("starts_at")) and
                   abs((ts(x["starts_at"])-start).total_seconds())<=1800 for x in board)
    unlined=[(g,s) for g,s,_ in pretip if not has_lines(g,s)]
    line_fail=[f"{g} @ {s.isoformat()}" for g,s in unlined if (s-now).total_seconds()<=90*60]
    line_warn=[f"{g} @ {s.isoformat()}" for g,s in unlined if (s-now).total_seconds()>90*60]
    # Distinguish a true ingestion gap from a provider that did not offer a
    # standard market. Never manufacture missing lines, and don't dispatch
    # another paid collector from the heartbeat.
    out.append(check("lines_coverage","FAIL" if line_fail else "WARN" if line_warn else "OK",
                     "Upcoming fixtures without verified saved standard lines",
                     missing=line_fail+line_warn,within_90m=line_fail,
                     provider_status=pp.get("provider_status"),partial_board=pp.get("partial_board"),
                     recovery_workflow=None))
    frozen={(r.get("game"),ts(r.get("start"))) for r in ledger_records
            if isinstance(r,dict) and ts(r.get("start"))}
    missing=[(g,s) for g,s,_ in soon if has_lines(g,s) and not any(
        name==g and abs((captured_start-s).total_seconds())<=1800
        for name,captured_start in frozen)]
    # Only an actual pretip missing pick can be repaired with a new frozen
    # forecast. Once tipped, new projections must not be backdated as pretip.
    failures=[f"{g} @ {s.isoformat()}" for g,s in missing
              if 0 <= (s-now).total_seconds() <=3*3600]
    posttip=[f"{g} @ {s.isoformat()}" for g,s in missing if (s-now).total_seconds()<0]
    warnings=[f"{g} @ {s.isoformat()}" for g,s in missing if (s-now).total_seconds()>3*3600]
    model_at=ts(model.get("generated_at"))
    current=bool(model_at and s_at and model_at>=s_at)
    st="FAIL" if failures or posttip or not ledger_available else "WARN" if warnings else "OK"
    details={g:(model.get("game_diagnostics") or {}).get(g) for g,s in missing}
    out.append(check("picks_frozen",st,"Saved forecasts missing for verified standard-line games",
                     missing=failures+posttip+warnings,ledger_available=ledger_available,
                     too_late_to_capture=posttip,model_after_lines=current,
                     excluded_by_game=details,
                     recovery_workflow=REPAIR["picks_frozen"] if failures else None))
    # Audit is the authoritative cross-market reconciliation, not the loose
    # "one frozen pick per game" check above.
    scoped_days={d for g,s,d in soon if d}
    audit_day=capture.get("game_date_eastern")
    if scoped_days and audit_day in scoped_days:
        covered=[g for g in capture.get("games",[]) if any(
            g.get("game")==name and ts(g.get("start"))==start for name,start,_ in soon)]
        primary_missing=sum(int(g.get("standard_player_stat_markets_never_primary_frozen") or 0)
                            for g in covered)
        no_receipt=sum(int(g.get("missing_primary_without_any_ai_receipt") or 0)
                       for g in covered)
        if primary_missing:
            state="FAIL"
        elif len(covered)==len(soon) and capture.get("status")=="CAPTURE_VERIFIED":
            state="OK"
        else:
            state="WARN"
        out.append(check("capture_integrity",state,
                         "Original standard market ↔ frozen model reconciliation",
                         primary_unfrozen=primary_missing,
                         without_any_ai_receipt=no_receipt,
                         audit_day=audit_day,
                         audited_games=len(covered),expected_games=len(soon),
                         recovery_workflow=REPAIR["picks_frozen"] if primary_missing and any(s>=now for name,s,_ in soon if any(g.get("game")==name for g in covered)) else None))
    elif soon:
        out.append(check("capture_integrity","WARN",
                         "No same-slate exact market capture audit published",
                         audit_day=audit_day,requested_dates=sorted(scoped_days),
                         recovery_workflow=None))
    # Next-day forecast-only readiness is not proof of offered standard lines.
    next_rows=readiness.get("games",[])
    out.append(check("next_slate","WARN" if readiness.get("status")=="NOT_READY" and next_rows else "OK"
                     if readiness.get("status") in ("READY","NO_SCHEDULED_GAMES") else "WARN",
                     "Next-slate line/forecast source readiness",
                     reported_status=readiness.get("status"),
                     target_date_eastern=readiness.get("target_date_eastern"),
                     missing_lines=[g.get("game") for g in next_rows
                                    if not g.get("captured_line_markets")][:20],
                     recovery_workflow=None))
    live=[]
    if espn is not None:
        for event in (espn or {}).get("events",[]):
            if event.get("status",{}).get("type",{}).get("state")!="in":continue
            comps=event.get("competitions") or [{}]
            competitors=comps[0].get("competitors",[])
            name={c.get("homeAway"):c.get("team",{}).get("displayName") for c in competitors}
            if name.get("away") and name.get("home"):live.append(f"{name['away']} @ {name['home']}")
    scores=site.get("nba_scoreboard_independent.json") or {}
    # The published scoreboard supplies a second observed live reference, but
    # ESPN unreachable is still uncertainty, never a reason for a green check.
    score_games={g.get("game") for g in scores.get("games",[])
                 if g.get("game_state")=="in" and g.get("game")}
    live=sorted(set(live)|score_games)
    score_age=age(now,scores.get("generated_at"))
    in_possible_window=any(-3*3600 <= (s-now).total_seconds()<=0 for g,s,_ in soon)
    unknown=espn is None and (in_possible_window or bool(score_games))
    bad=bool(live and (score_age is None or score_age>30 or not set(live)<=score_games))
    sc_state="FAIL" if bad else "WARN" if unknown else "OK"
    out.append(check("live_scores",sc_state,"Live scoreboard coverage",
                     live=live,age_minutes=score_age,missing=sorted(set(live)-score_games),
                     espn_available=espn is not None,
                     recovery_workflow=REPAIR["live_scores"] if bad else None))
    players=site.get("nba_player_tracking_independent.json") or {}
    per_game={g.get("game"):g for g in players.get("games",[])
              if isinstance(g,dict) and g.get("game")}
    player_age=age(now,players.get("captured_at"))
    missing_players=[g for g in live if not (per_game.get(g) or {}).get("player_rows")]
    stale_players=[g for g in live if g not in missing_players and
                   (age(now,(per_game[g].get("observed_at") or players.get("captured_at"))) is None
                    or age(now,(per_game[g].get("observed_at") or players.get("captured_at")))>30)]
    # The wrapper timestamp can be fresh after a partial collector run while
    # several retained older game boxes are stale. A valid per-game merge
    # preserves real totals, but does not pretend the old rows are live.
    bad=bool(live and (missing_players or stale_players or player_age is None or player_age>30))
    player_state="FAIL" if bad else "WARN" if unknown else "OK"
    out.append(check("live_players",player_state,"Live player-box coverage",
                     age_minutes=player_age,missing=missing_players,
                     stale_game_observations=stale_players,
                     espn_available=espn is not None,
                     recovery_workflow=REPAIR["live_players"] if bad else None))
    # Separate AI-only and standard PrizePicks research ledgers have their
    # own immutable final grading systems. A healthy four-market ledger does
    # NOT imply these archived markets were also graded.
    overnight=site.get("nightly_grade_health.json") or {}
    report_age=age(now,overnight.get("checked_at"))
    if not overnight or report_age is None or report_age>180:
        out.append(check("grading_report","WARN","Overnight grading health is missing or stale",
                         age_minutes=report_age,
                         recovery_workflow=None))
    else:
        prize_overdue=overnight.get("prizepicks_overdue")
        ai_ungraded=overnight.get("ai_forecasts_ungraded")
        out.append(check("prizepicks_grade_backlog","WARN" if prize_overdue is None else "FAIL" if prize_overdue else "OK",
                         "Original standard PrizePicks research settlement",
                         overdue=prize_overdue,
                         games=overnight.get("prizepicks_overdue_games") or {},
                         recovery_workflow="nba-prizepicks-research-ledger.yml" if prize_overdue else None))
        out.append(check("ai_grade_backlog","WARN" if ai_ungraded is None else "FAIL" if ai_ungraded else "OK",
                         "Original AI-only pregame forecast settlement",
                         ungraded=ai_ungraded,recorded=overnight.get("ai_forecasts_recorded"),
                         graded=overnight.get("ai_forecasts_graded"),
                         recovery_workflow="grade_frozen_ai_forecasts.yml" if ai_ungraded else None))
    overdue=[r for r in ledger_records if r.get("grade")=="PENDING"
             and ts(r.get("start")) and (now-ts(r["start"])).total_seconds()>8*3600]
    out.append(check("settlement","FAIL" if overdue or not ledger_available else "OK",
                     "Unsettled authentic pretip picks >8h after tip",
                     count=len(overdue) if ledger_available else None,
                     games=sorted({r.get("game") for r in overdue})[:15],
                     recovery_workflow=REPAIR["settlement"] if overdue else None))
    overall="FAIL" if any(x["status"]=="FAIL" for x in out) else "WARN" if any(
        x["status"]=="WARN" for x in out) else "OK"
    return {"checked_at":now.isoformat(),"overall":overall,"site":SITE,"stages":out}

def fetch(url):
    req=urllib.request.Request(url+"?hb="+str(int(dt.datetime.now().timestamp())),headers={"Cache-Control":"no-cache","User-Agent":"DamesPicks-Heartbeat"})
    with urllib.request.urlopen(req,timeout=20) as response:return json.load(response)
def main():
    site={}
    for name in FILES:
        try:site[name]=fetch(f"{SITE}/{name}")
        except Exception as exc:
            print("Unreadable deployed feed",name,str(exc),file=sys.stderr)
            site[name]=None
    try:espn=fetch("https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard")
    except Exception:espn=None
    result=evaluate(dt.datetime.now(dt.timezone.utc),site,espn)
    dest=Path(sys.argv[1] if len(sys.argv)>1 else "pipeline_heartbeat.json")
    dest.write_text(json.dumps(result,indent=2)+"\n")
    print(result["overall"],[(x["stage"],x["status"]) for x in result["stages"]])
    return 1 if result["overall"]=="FAIL" else 0
if __name__=="__main__":raise SystemExit(main())
