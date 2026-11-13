"""Minutes V3: strictly pregame minutes, schedule load, and verified teammate splits.

No same-game box score, invented starter status or retrospective injury status.
Research-only; any teammate adjustment requires independently documented OUT
status for the target game AND both prior played/absent comparison groups.
"""
import math
from collections import defaultdict
from datetime import date
from statistics import mean
try:
 from .minutes_model_v2 import forecast as minutes_v2, numeric_minutes
except ImportError:
 from minutes_model_v2 import forecast as minutes_v2, numeric_minutes

VERSION="MINUTES_V3_ROTATION_WOWY_RESEARCH"
def team_context(rows):
    """Build per-team game dates and teammate presence with full-team coverage."""
    teams=defaultdict(lambda:defaultdict(set))
    for r in rows:
        d=r.get("date");team=r.get("team");pid=r.get("id") or r.get("player_id")
        if d and team and pid is not None and numeric_minutes(r.get("MIN")) is not None:
            teams[str(team)][str(d)].add(str(pid))
    return {t:dict(d) for t,d in teams.items()}

def forecast(history, day, team, *, player_id=None, verified_out_ids=(),
             team_games=None, pretip_injury_verified=False):
    base=minutes_v2(history,day,team)
    result={"status":"INSUFFICIENT_PRIOR_MINUTES","model":VERSION,
            "expected_minutes":None,"baseline_v2":base.get("expected_minutes"),
            "rotation_adjustment":0,"teammate_adjustment":0,
            "teammates_evaluated":0,"verified_out_context_applied":False,
            "season_rest_days":None,"production_applied":False,
            "prospective_calibrated":False,"last_prior_date":base.get("last_observed_date")}
    b=base.get("expected_minutes")
    if b is None:return result
    prior=sorted((r for r in history if r.get("team")==team and
                  isinstance(r.get("date"),str) and r["date"]<day and
                  numeric_minutes(r.get("MIN")) is not None),
                 key=lambda r:r["date"])
    if len(prior)<8:return result
    # Past-only recent rotation trend, bounded at two minutes. The V2 forecast
    # already weights recent minutes; V3 only adds a small conservative change.
    last3=mean(numeric_minutes(x["MIN"]) for x in prior[-3:])
    last10=mean(numeric_minutes(x["MIN"]) for x in prior[-10:])
    rotation=max(-2.,min(2.,.35*(last3-last10)))
    rest=(date.fromisoformat(day)-date.fromisoformat(prior[-1]["date"])).days-1
    # Avoid attributing a changed role to injury without official evidence.
    adj=0.
    eligible=0
    if pretip_injury_verified and team_games and verified_out_ids and player_id is not None:
        days=team_games.get(team,{})
        played_dates=[r["date"] for r in prior if r["date"] in days
                      and len(days[r["date"]])>=7]
        for tid in sorted({str(v) for v in verified_out_ids
                           if str(v)!=str(player_id)})[:3]:
            with_minutes=[numeric_minutes(r["MIN"]) for r in prior
                    if r["date"] in played_dates and tid in days[r["date"]]]
            without_minutes=[numeric_minutes(r["MIN"]) for r in prior
                    if r["date"] in played_dates and tid not in days[r["date"]]]
            if len(with_minutes)<5 or len(without_minutes)<5:continue
            raw=mean(without_minutes[-10:])-mean(with_minutes[-10:])
            adj+=max(-1.5,min(1.5,.25*raw))
            eligible+=1
        adj=max(-2.,min(2.,adj))
    estimate=max(0.,min(46.,b+rotation+adj))
    return {**result,"status":"PREGAME_MINUTES_V3_RESEARCH",
            "expected_minutes":round(estimate,3),
            "rotation_adjustment":round(rotation,3),
            "teammate_adjustment":round(adj,3),
            "teammates_evaluated":eligible,
            "verified_out_context_applied":eligible>0,
            "season_rest_days":rest,
            "historical_role_games":len(prior),
            "no_inferred_starts_or_fouls":True,
            "method":"V2_PLUS_BOUNDED_PRIOR_ROTATION_AND_VERIFIED_OUT_OBSERVATIONAL_WOWY"}
