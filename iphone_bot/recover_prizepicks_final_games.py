"""Recover final verified player boxes for outstanding pretip PrizePicks research.

Game discovery is restricted to PENDING previously saved records, dated within
the last 3 Eastern days. Actual outcomes require final NBA/ESPN boxscores.
Never turns an AI forecast into a boxscore or makes a paid odds request.
"""
import datetime as dt
import json
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from iphone_bot.official_game_id_index import recovery_game_ids
from iphone_bot.archived_espn_game_ids import archived_espn_hints
from iphone_bot.fetch_final_boxscores import gather, request_json, NBA_SCOREBOARD, NBA_BOX, NBA_SCHEDULE, NBA_SCHEDULE_ALT
from iphone_bot.prizepicks_research_ledger import LEDGER, ROOT, utc, settle
from iphone_bot.verified_prizepicks_inactives import verified_inactive_subset
from iphone_bot.verified_nov9_nonparticipants import load_nonparticipants
from iphone_bot.verified_final_cache import read_cache, merge_rows
from iphone_bot.verified_gamebook_inactives import load_gamebook_inactives

OUT=ROOT/"data/nba/current/prizepicks_verified_final_games.json"
STATUS=ROOT/"docs/prizepicks_final_recovery_status.json"
ET=ZoneInfo("America/New_York")
S3_BASE="https://nba-prod-us-east-1-mediaops-stats.s3.amazonaws.com/NBA/liveData/"

def merge_cached_finals(records, fetched, cached, now=None):
    """Reuse verified final observations for exact pending fixtures after rollover.

    The AI grader may already have obtained an explicit ESPN DNP that a later
    NBA-only response omits. Missing rows must not erase that source evidence.
    Conflicting cache/fetch observations remain rejected by merge_rows.
    """
    from iphone_bot.paper_pick_pipeline import expected_opponents
    now=now or dt.datetime.now(dt.timezone.utc)
    fixtures=set()
    for r in records:
        start=utc(r.get('start'))
        if r.get('status')!='PENDING' or not start or start>=now:
            continue
        for opponent in expected_opponents(r.get('game'),r.get('team')):
            day=start.astimezone(ET).date().isoformat()
            fixtures.add((day,r['team'],opponent))
            fixtures.add((day,opponent,r['team']))
    selected=[r for r in cached
              if (r.get('date'),r.get('team'),r.get('opponent')) in fixtures]
    return merge_rows(selected,fetched)

def multi_origin_request(url, requester=request_json):
    """Retry NBA and ESPN JSON through their own provider mirrors."""
    candidates=[url]
    if url == NBA_SCOREBOARD:
        candidates=[S3_BASE+"scoreboard/todaysScoreboard_00.json",url]
    elif url.startswith(NBA_BOX.split("{}")[0]):
        filename=url.rsplit("/",1)[-1]
        candidates=[S3_BASE+"boxscore/"+filename,url]
    elif url.startswith("https://site.api.espn.com/apis/site/v2/"):
        candidates.append(url.replace("https://site.api.espn.com/", "https://site.web.api.espn.com/", 1))
    errors=[]
    for candidate in candidates:
        try:
            return requester(candidate,timeout=7)
        except (OSError,TimeoutError,ValueError,RuntimeError) as err:
            reason=getattr(err,"code",type(err).__name__)
            errors.append(f"{urlsplit(candidate).hostname}: {reason}")
    raise OSError("Final data request failed: "+", ".join(errors)) from None

def pending_matchup_requests(records,now=None,max_matchups=12,days_back=3):
    now=now or dt.datetime.now(dt.timezone.utc)
    minimum=(now.astimezone(ET).date()-dt.timedelta(days=days_back)).isoformat()
    matchups={}
    for r in records:
        if r.get("status")!="PENDING":continue
        start=utc(r.get("start"))
        if start is None or (now-start).total_seconds()<2*3600:continue
        date=start.astimezone(ET).date().isoformat()
        if date<minimum or not r.get("game") or not r.get("team"):continue
        key=(date,r["game"])
        matchups.setdefault(key,{"status":"PENDING","event_start":r["start"],
                                  "game":r["game"],"team":r["team"],
                                  "player_id":str(r.get("player_id") or "")})
    if len(matchups)>max_matchups:
        # Fail closed: never falsely claim a complete recovery if over budget.
        raise ValueError("Pending finals exceed safe per-run matchup cap")
    return list(matchups.values())

def recover(records,now=None,request=None):
    pending=pending_matchup_requests(records,now=now)
    if not pending:
        return [],{"status":"NO_ELIGIBLE_RECENT_PRIZEPICKS_PENDING_GAMES",
                   "requested_matchups":0,"verified_rows":0,"errors":[]}
    if request is None:
        # The daily schedule rolls forward before all pending research settles.
        # Reuse immutable ESPN fixture IDs solely as hints; gather independently
        # checks FINAL status, game ID, Eastern date, and exact teams.
        days={utc(r["event_start"]).astimezone(ET).date().isoformat()
              for r in pending}
        espn_ids=archived_espn_hints(dates=days)
        found,report=gather(pending,now=now,request=multi_origin_request,
                            known_game_ids=recovery_game_ids(ROOT/"docs/official_nba_game_ids.json",
                                          ROOT/"docs/verified_official_final_game_ids.json"),
                            known_espn_games=espn_ids)
        report["archived_espn_game_id_hints"]=len(espn_ids)
    else:
        found,report=gather(pending,now=now,request=request)
    seen=set()
    verified=[]
    for row in found:
        if row.get("final_confirmed") is not True:
            continue
        if row.get("source") not in ("NBA_CDN_FINAL","ESPN_FINAL"):
            continue
        ident=(row.get("source_game_id"),row.get("player"),row.get("team"),row.get("date"))
        if ident in seen:continue
        seen.add(ident)
        verified.append(row)
    report["requested_matchups"]=len(pending)
    report["verified_rows"]=len(verified)
    report["verified_dnp_rows"]=sum(row.get("dnp_final_verified") is True for row in verified)
    report["verified_played_rows"]=sum(row.get("dnp_final_verified") is not True for row in verified)
    report["recovery_source"]="VERIFIED_FINAL_BOXSCORES_ONLY"
    return verified,report

def main():
    records=json.loads(LEDGER.read_text()).get("records",[]) if LEDGER.exists() else []
    try:
        rows,report=recover(records)
    except (OSError,ValueError,TypeError,KeyError,RuntimeError) as e:
        rows=[]
        report={"status":"PRIZEPICKS_FINAL_RECOVERY_FAILED","requested_matchups":None,
                "verified_rows":0,"errors":[type(e).__name__]}
    historical=read_cache(ROOT/"docs/verified_final_player_cache.json")
    before_cache=len(rows)
    rows=merge_cached_finals(records,rows,historical)
    report['verified_cache_rows_reused']=max(0,len(rows)-before_cache)
    # Supplement missing official feed inactivity only with manually verified
    # NBA/club postgame source links and a matching independently final game ID.
    # A failed cross-check NEVER creates a DNP or changes a settled record.
    try:
        checked_inactives=verified_inactive_subset(rows)
    except (OSError,ValueError,TypeError,KeyError) as error:
        checked_inactives=[]
        report.setdefault("errors",[]).append("OFFICIAL_INACTIVE_CROSSCHECK_"+type(error).__name__)
    rows.extend(checked_inactives)
    # An independently verified FINAL player cache can establish exact game
    # completion for historical source-confirmed nonparticipants. A cache
    # never supplies an absent player's made-up points or a betting win/loss.
    checked_historical=load_nonparticipants(historical+rows)
    existing={(x.get("source_game_id"),x.get("team"),x.get("player")) for x in rows}
    checked_historical=[r for r in checked_historical
                        if (r.get("source_game_id"),r.get("team"),r.get("player")) not in existing]
    rows.extend(checked_historical)
    rows.extend(load_gamebook_inactives(historical + rows))
    report["historical_source_confirmed_dnp_rows"]=len(checked_historical)
    report["manual_crosschecked_official_inactive_rows"]=len(checked_inactives)
    report["verified_rows"]=len(rows)
    report["verified_dnp_rows"]=sum(r.get("dnp_final_verified") is True for r in rows)
    # Preview only: no mutation to the immutable research ledger here.
    today = dt.datetime.now(ET).date()
    target_dates = {(today-dt.timedelta(days=i)).isoformat() for i in range(4)}
    now = dt.datetime.now(dt.timezone.utc)
    pending = [r for r in records if r.get("status")=="PENDING" and
               (start:=utc(r.get("start"))) and
               (now-start).total_seconds()>=4*3600 and
               start.astimezone(ET).date().isoformat() in target_dates]
    preview = settle({"records":pending},[],final_games=rows)
    graded = [r for r in preview["records"] if r.get("status")=="SETTLED"]
    voided=[r for r in preview["records"] if r.get("status")=="VOID_DNP"]
    unresolved=[r for r in preview["records"] if r.get("status")=="PENDING"]
    if (report['status']=='PRIZEPICKS_FINAL_RECOVERY_FAILED' and pending and
            not unresolved and report['verified_cache_rows_reused']):
        report['status']='VERIFIED_FINAL_CACHE_RECOVERY'
    report["recent_research_pending_before_recovery"]=len(pending)
    report["recent_research_settlement_matches"]=len(graded)
    report["recent_research_verified_dnp_voids"]=len(voided)
    report["recent_research_unmatched_after_recovery"]=len(unresolved)
    report["unmatched_player_stat_markets"]=len({(r.get("game"),r.get("player_id"),r.get("stat")) for r in unresolved})
    report["unmatched_games"]=dict(sorted(__import__("collections").Counter(r.get("game","UNKNOWN") for r in unresolved).items()))
    from iphone_bot.paper_pick_pipeline import strict_player_name, expected_opponents
    reason_counts=__import__("collections").Counter()
    samples={}
    for p in unresolved:
        st=utc(p.get("start"))
        date=st.astimezone(ET).date().isoformat() if st else ""
        name=strict_player_name(p.get("player"))
        team=str(p.get("team","")).upper()
        opponents=expected_opponents(p.get("game"),team)
        date_rows=[g for g in rows if g.get("date")==date]
        team_rows=[g for g in date_rows if g.get("team")==team]
        opponent_rows=[g for g in team_rows if g.get("opponent") in opponents]
        name_rows=[g for g in opponent_rows if strict_player_name(g.get("player"))==name]
        if not date_rows:reason="NO_FINAL_FOR_EASTERN_DATE"
        elif not team_rows:reason="TEAM_NOT_FOUND_IN_FINALS"
        elif not opponent_rows:reason="OPPONENT_MISMATCH"
        elif not name_rows:reason="PLAYER_NAME_MISMATCH"
        elif len(name_rows)>1:reason="DUPLICATE_PLAYER_IDENTITY"
        else:reason="MATCHED_BUT_SETTLEMENT_REJECTED"
        reason_counts[reason]+=1
        if reason not in samples:
            samples[reason]={
                "sample_research_name":p.get("player"),
                "game":p.get("game"),
                "sample_official_names":[g.get("player") for g in opponent_rows[:4]],
                "research_team":team,
                "date":date,
            }
    report["unmatched_distinct_players_by_game"]={
        game: sorted({r.get("player","") for r in unresolved if r.get("game")==game})
        for game in sorted({r.get("game") for r in unresolved}) if game
    }
    report["unmatched_reason_counts"]=dict(reason_counts)
    report["unmatched_reason_examples"]=samples
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(rows,indent=2)+"\n")
    STATUS.write_text(json.dumps({**report,
        "checked_at":dt.datetime.now(dt.timezone.utc).isoformat()},indent=2)+"\n")
    print("PrizePicks verified final recovery:",json.dumps({
        "status":report["status"],"requested_matchups":report["requested_matchups"],
        "verified_rows":len(rows),"errors":len(report.get("errors",[]))}))
    if report["status"]=="PRIZEPICKS_FINAL_RECOVERY_FAILED":
        raise SystemExit(1)

if __name__=="__main__":
    main()
