"""Build authentic PrizePicks-only model comparison input.

Consumes the authenticated independent PrizePicks site export, never invents
American sportsbook odds. Only future, recently observed, scheduled NBA
full-game offers with team/opponent and source identity are eligible.
"""
import json
from datetime import datetime,timezone,timedelta
from pathlib import Path
try:
    from .fetch_prizepicks import timeparse
    from .paper_pick_pipeline import expected_opponents
except ImportError:
    from fetch_prizepicks import timeparse
    from paper_pick_pipeline import expected_opponents

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"docs/prizepicks_site.json"
OUTPUT=ROOT/"docs/prizepicks_model_input.json"
STAT={"PTS":"Points","REB":"Rebounds","AST":"Assists","PRA":"Points Rebounds Assists"}

def convert(source,now=None):
    now=now or datetime.now(timezone.utc)
    base={"is_live":False,"source":"AUTHENTIC_PRIZEPICKS_PICKEM_NO_ODDS",
          "updated_at":now.isoformat(),"picks":[],
          "events_covered":[],"excluded_reasons":{},
          "notice":"Real pick'em line comparisons, NOT sportsbook American odds or calibrated probabilities."}
    if not isinstance(source,dict) or source.get("status")!="LIVE_THIRD_PARTY_PRIZEPICKS_LINES":
        return {**base,"status":"NO_VERIFIED_PROVIDER_BOARD"}
    issued=timeparse(source.get("generated_at"))
    if not issued or issued>now+timedelta(minutes=10) or now-issued>timedelta(hours=6):
        return {**base,"status":"STALE_PROVIDER_BOARD"}
    if source.get("provider_status") not in ("fresh","partial"):
        return {**base,"status":"PROVIDER_NOT_FRESH"}
    offers=source.get("board_offers")
    if not isinstance(offers,list):return {**base,"status":"MISSING_BOARD_OFFERS"}
    seen=set();rows=[];exclusions={}
    for item in offers:
        reason=None
        if not isinstance(item,dict):
            reason="invalid_row"
        else:
            stat=STAT.get(str(item.get("stat","")).upper())
            started=timeparse(item.get("starts_at"))
            observed=timeparse(item.get("observed_at"))
            try:line=float(item["line"])
            except (KeyError,ValueError,TypeError):line=None
            if not stat:reason="unsupported_market"
            elif not isinstance(item.get("game"),str) or not item["game"]:
                reason="unverified_matchup"
            elif not started or started<=now or started>now+timedelta(days=3):
                reason="not_upcoming"
            elif not observed or observed>now+timedelta(minutes=10) or now-observed>timedelta(hours=6):
                reason="not_recent"
            elif line is None or not 0<=line<300:reason="invalid_line"
            elif item.get("is_demo") is not False:reason="unverified_live"
            elif not item.get("team") or not expected_opponents(item["game"],item["team"]):
                reason="wrong_team"
            elif item.get("opponent") and item["opponent"] not in expected_opponents(item["game"],item["team"]):
                reason="wrong_opponent"
            elif not item.get("more_tier") and not item.get("less_tier"):
                reason="no_available_side"
            elif not str(item.get("player","")).strip():reason="no_player"
            else:
                key=(item["game"],started.isoformat(),str(item["player"]).casefold(),stat,line)
                if key in seen:reason="duplicate_player_line"
                else:seen.add(key)
        if reason:
            exclusions[reason]=exclusions.get(reason,0)+1
            continue
        # These are genuine pick'em selectable tiers, not sportsbook odds.
        # Include each offered side for existing model identity validation.
        for direction,tier in (("More",item.get("more_tier")),("Less",item.get("less_tier"))):
            if tier not in ("standard","goblin","demon"):continue
            rows.append({"player":item["player"],"team":item["team"],"stat":stat,
              "game":item["game"],"start":started.isoformat(),
              "market_updated":observed.isoformat(),"line":line,
              "direction":direction,"odds":None,"pickem_tier":tier,
              "source":"independent_prizepicksapi_com"})
    games={x["game"]:x["start"] for x in rows}
    return {**base,"status":"FRESH_AUTHENTIC_PRIZEPICKS_LINES" if rows else "NO_ELIGIBLE_UPCOMING_OFFERS",
        "is_live":bool(rows),"updated_at":issued.isoformat(),
        "picks":rows,"events_covered":[{"game":g,"start":t} for g,t in sorted(games.items())],
        "excluded_reasons":exclusions,"real_player_market_pairs":len(seen),
        "upcoming_games":len(games),"source_generated_at":source.get("generated_at"),
        "is_prizepicks":True,"real_american_odds_provided":False}

def main():
    source=json.loads(SOURCE.read_text()) if SOURCE.exists() else {}
    report=convert(source)
    OUTPUT.write_text(json.dumps(report,indent=2)+"\n")
    print("PrizePicks-only model input:",report["status"],
          "upcoming",report.get("upcoming_games",0),"rows",len(report["picks"]))

if __name__=="__main__":main()
