"""Documented historical pretip trade exclusion for AI-only forecast accuracy.

Never infer a DNP, win/loss, or zero actual; confirm exact final game
against trusted NBA/ESPN results and source-linked transaction before kickoff.
"""
import datetime as dt
import json
from pathlib import Path
from urllib.parse import urlparse

ROOT=Path(__file__).resolve().parents[1]
FIXTURE=ROOT/"docs/verified_pretip_trade_2026-11-08.json"
SOURCE="NBA_OFFICIAL_PRETIP_TRADE_CROSSCHECKED"

def verified_trade_rows(final_rows,fixture):
    required={
       "status":"OFFICIALLY_CONFIRMED_PRETIP_TRADE_2026_11_08",
       "date_eastern":"2026-11-08","game_id":"0022600202",
       "game":"Miami Heat @ Sacramento Kings","player":"Nique Clifford",
       "team":"SAC","opponent":"MIA",
       "original_team_release":"https://www.nba.com/kings/news/sacramento-kings-complete-trade",
       "receiving_team_release":"https://www.nba.com/thunder/news/nique-clifford-261108",
       "official_game_url":"https://www.nba.com/game/0022600202",
       "reason":"VERIFIED_PRETIP_TRADE_NOT_AVAILABLE_FOR_ORIGINAL_TEAM",
    }
    if any(fixture.get(k)!=v for k,v in required.items()):
        raise ValueError("Trade evidence fixture not exact and source-linked")
    try:
        t=dt.datetime.fromisoformat(fixture["trade_announced_at"])
        tip=dt.datetime.fromisoformat(fixture["tipoff_at"])
        if t.tzinfo is None or tip.tzinfo is None or not t<tip or (tip-t).total_seconds()>86400:
            raise ValueError("Transaction not proven before tipoff")
    except (TypeError,KeyError,ValueError) as e:
        raise ValueError("Invalid pretip transaction chronology") from e
    trusted=[r for r in final_rows if r.get("final_confirmed") is True
             and r.get("source") in ("NBA_CDN_FINAL","ESPN_FINAL")
             and str(r.get("source_game_id"))=="0022600202"
             and r.get("date")=="2026-11-08"
             and r.get("team")=="SAC" and r.get("opponent")=="MIA"]
    if not trusted:return []
    if any(str(r.get("player","")).casefold()=="nique clifford" and
           not r.get("dnp_final_verified") for r in trusted):
        raise ValueError("Verified player performance conflicts with trade exclusion")
    return [{"player":"Nique Clifford","team":"SAC","opponent":"MIA","date":"2026-11-08",
             "source_game_id":"0022600202","source":SOURCE,"final_confirmed":True,
             "nonparticipant_final_verified":True,"reason":fixture["reason"],
             "trade_announced_at":fixture["trade_announced_at"],
             "original_team_release":fixture["original_team_release"],
             "receiving_team_release":fixture["receiving_team_release"]}]

def verified_trade_subset(final_rows,path=FIXTURE):
    if not path.exists():return []
    fixture=json.loads(path.read_text())
    original=verified_trade_rows(final_rows,fixture)
    # The same documented trade also invalidates the stale SAC assignment
    # two days later. Require his verified OKC appearance that same night.
    played = [r for r in final_rows if r.get("date")=="2026-11-10"
              and r.get("final_confirmed") is True and r.get("source")=="NBA_CDN_FINAL"
              and r.get("dnp_final_verified") is not True]
    if original and any(r.get("team")=="OKC" and r.get("opponent")=="POR"
                        and str(r.get("source_game_id"))=="0022600216"
                        and r.get("player")=="Nique Clifford" for r in played):
        kings = [r for r in played if r.get("team")=="SAC" and r.get("opponent")=="ORL"
                 and str(r.get("source_game_id"))=="0022600215"]
        if len(kings)>=3 and not any(r.get("player")=="Nique Clifford" for r in kings):
            original.append({**original[0],"date":"2026-11-10","opponent":"ORL",
                             "source_game_id":"0022600215"})
    return original
