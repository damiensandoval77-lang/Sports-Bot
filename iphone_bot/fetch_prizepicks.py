"""Optional independent PrizePicks board feed alongside existing sportsbook odds.

Never reads PrizePicks private endpoints, never calls demo data for live display,
and never treats pick'em payout multipliers as sportsbook American odds.
Set PRIZEPICKS_API_KEY in GitHub Actions secrets. Server-side only.
"""
import datetime as dt
import json
import math
import os
from pathlib import Path
import unicodedata
import urllib.error
import urllib.parse
import urllib.request

try:
    from iphone_bot.paper_pick_pipeline import expected_opponents, TEAM_ABBREVIATIONS
except ModuleNotFoundError:
    from paper_pick_pipeline import expected_opponents, TEAM_ABBREVIATIONS

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/"docs/prizepicks.json"
BASE="https://prizepicksapi.com/api/v1/projections"
STAT={"points":"PTS","rebounds":"REB","assists":"AST",
      "pts+rebs+asts":"PRA","pts+reb+ast":"PRA","points rebounds assists":"PRA",
      "points+rebounds+assists":"PRA","pts reb ast":"PRA"}
MAX_PAGES=4  # 4 compact pages, up to 4,000 offers; capped at <=40 new-plan credits.
PAGE_SIZE=1000
MAX_TARGETED_READS=3  # At most three additional narrow reads, only inside 24h of tipoff.
TARGETED_PAGE_SIZE=200

def standard_query(*, cursor=None, search=None, limit=PAGE_SIZE):
    """Server-side filter means paid pages are spent on needed standard offers.
    Pagination remains bounded and may still be partial; never claim the
    unrestricted Demon/Goblin board was fully retrieved.
    """
    if not 1<=limit<=PAGE_SIZE:
        raise ValueError("Invalid bounded compact page size")
    params={"league":"NBA","status":"active","tier":"standard",
            "view":"compact","limit":limit}
    if cursor:params["cursor"]=cursor
    if search:params["search"]=search
    return params

def timeparse(value):
    try:
        d=dt.datetime.fromisoformat(str(value).replace("Z","+00:00"))
        return d.astimezone(dt.timezone.utc) if d.tzinfo else None
    except (TypeError,ValueError):return None

def norm(value):
    s=unicodedata.normalize("NFKD",str(value or ""))
    return "".join(c for c in s.lower() if c.isalnum() and not unicodedata.combining(c))

def numeric(value):
    try:
        n=float(value)
        return n if math.isfinite(n) and n>=0 else None
    except (ValueError,TypeError):return None

def team_abbrev(s):
    if isinstance(s,dict):
        return str(s.get("abbreviation") or s.get("team") or "").strip().upper()
    return str(s or "").strip().upper()

def clean(row,now,verified_live=False):
    if not isinstance(row,dict) or row.get("is_demo") is True or row.get("status")!="active":return None
    # Compact production rows may omit is_demo. Only accept that case after
    # confirming the authenticated production endpoint meta.mode is live.
    if row.get("is_demo") is None and not verified_live:return None
    if str(row.get("league","")).upper()!="NBA":return None
    player=row.get("player",{})
    event=row.get("event",{})
    market=row.get("market",{})
    if isinstance(player,str):player={"name":player,"team":row.get("team")}
    if player is None:player={"name":row.get("player_name"),"team":row.get("team")}
    if not isinstance(player,dict):return None
    if not isinstance(event,dict):event={}
    if not isinstance(market,dict):market={"stat":row.get("stat") or market,"period":row.get("period")}
    stat=STAT.get(str(market.get("stat") or row.get("stat") or "").lower().strip())
    period=str(market.get("period") or row.get("period") or "").strip().lower()
    if stat is None:return None  # Reject unsupported or undefined markets before mapping posted lines.
    if period not in ("full game","full_game","fullgame"):return None
    raw_starts=event.get("starts_at") or row.get("event_starts_at") or row.get("starts_at")
    starts=timeparse(raw_starts)
    observed=timeparse(row.get("observed_at"))
    if not observed or observed>now+dt.timedelta(minutes=10):return None
    if starts and starts<=now:return None
    # Vendor records may be old even if a cached endpoint says active.
    if now-observed>dt.timedelta(hours=6):return None
    if row.get("is_live") is True or row.get("in_game") is True:return None
    fields=row.get("source_fields") or {}
    if not isinstance(fields,dict):fields={}
    if fields.get("is_promo") is True or row.get("is_promo") is True:return None
    line=numeric(row.get("line"))
    if line is None:return None
    selections=row.get("selections")
    if not isinstance(selections,list):
        selections=[]
        # Compact authenticated board uses sides[] and a top-level tier.
        # Explicit strings represent available sides; source still supplies
        # the real tier instead of inventing American betting odds.
        if isinstance(row.get("sides"),list):
            for entry in row["sides"]:
                if isinstance(entry,str):
                    selections.append({"side":entry,"available":True,"tier":row.get("tier")})
                elif isinstance(entry,dict):
                    selections.append({
                        "side":entry.get("side") or entry.get("name"),
                        "available":entry.get("available",True),
                        "tier":entry.get("tier") or row.get("tier")})
        else:
            for side in ("more","less"):
                if row.get(side+"_available") is True:
                    selections.append({"side":side,"available":True,"tier":row.get(side+"_tier")})
    picks={}
    for sel in selections:
        if not isinstance(sel,dict) or sel.get("available") is not True:continue
        side=str(sel.get("side","")).lower()
        tier=str(sel.get("tier","")).lower()
        if side in ("more","less") and tier in ("standard","goblin","demon"):
            picks[side]=tier
    if not picks:return None
    name=str(player.get("name") or "").strip()
    team=team_abbrev(player.get("team"))
    opponent=team_abbrev(event.get("opponent") or row.get("opponent"))
    if not name or len(team)!=3 or (opponent and team==opponent):return None
    return {"id":str(row.get("id","")),"player":name,"team":team,
            "opponent":opponent,"stat":stat,"line":line,
            "starts_at":starts.isoformat() if starts else None,"observed_at":observed.isoformat(),
            "more_tier":picks.get("more"),"less_tier":picks.get("less"),
            "source":"independent_prizepicksapi_com","is_demo":False}

def match(offer,comparison,now=None):
    """Require team + complete player name + stat + opponent + close start."""
    if norm(offer["player"])!=norm(comparison.get("player")):return False
    if offer["team"]!=str(comparison.get("team","")).upper():return False
    if offer["stat"]!=comparison.get("stat"):return False
    start=timeparse(comparison.get("start"))
    other=timeparse(offer.get("starts_at"))
    if not start or start<=(now or dt.datetime.now(dt.timezone.utc)):return False
    verified=expected_opponents(comparison.get("game"),offer["team"])
    if not verified:return False
    if offer["opponent"] and offer["opponent"] not in verified:return False
    if other:
        if abs((start-other).total_seconds())>3*3600:return False
        return bool(offer["opponent"]) or abs((start-other).total_seconds())<=30*60
    # A third-party offer without a game time can only match a fully named
    # opponent + verified upcoming team game, never player/name alone.
    return bool(offer["opponent"]) and offer["opponent"] in verified

def rejection_hint(row,now,verified_live=False):
    """Count rejection categories without publishing private provider rows."""
    if not isinstance(row,dict):return "non_object"
    if row.get("is_demo") is True or (row.get("is_demo") is None and not verified_live):return "missing_real_provenance"
    if row.get("status")!="active" or str(row.get("league","")).upper()!="NBA":return "inactive_or_not_nba"
    event=row.get("event") if isinstance(row.get("event"),dict) else {}
    start=timeparse(event.get("starts_at") or row.get("event_starts_at") or row.get("starts_at"))
    if start and start<=now:return "game_already_started"
    observed=timeparse(row.get("observed_at"))
    if observed is None:return "missing_observed_time"
    if now-observed>dt.timedelta(hours=6):return "observation_older_than_six_hours"
    market=row.get("market") if isinstance(row.get("market"),dict) else {}
    period=str(market.get("period") or row.get("period") or "").strip().lower()
    if period not in ("full game","full_game","fullgame"):return "not_full_game_market"
    stat=str(market.get("stat") or row.get("stat") or "").lower().strip()
    if stat not in STAT:return "unsupported_stat"
    player=row.get("player")
    team=player.get("team") if isinstance(player,dict) else row.get("team")
    if not team or len(team_abbrev(team))!=3:return "missing_team"
    if not start and not (event.get("opponent") or row.get("opponent")):return "missing_game_time_and_opponent"
    return "invalid_or_unavailable_selection"

def publish(raw_pages,comparisons,now=None,schedule=None):
    now=now or dt.datetime.now(dt.timezone.utc)
    offers=[]
    raw_count=0
    from collections import Counter
    rejection_reasons=Counter()
    statuses=[]
    cursors=[]
    for page in raw_pages:
        meta=page.get("meta",{})
        if meta.get("mode")!="live":raise ValueError("Refuse demo or unknown mode")
        if meta.get("source_status") in ("failed","stale"):
            raise ValueError("Provider source is not fresh")
        statuses.append(meta.get("source_status","unknown"))
        cursors.append(meta.get("next_cursor"))
        rows=page.get("data",[])
        if not isinstance(rows,list):raise ValueError("Invalid projection rows")
        raw_count+=len(rows)
        for row in rows:
            cleaned=clean(row,now,verified_live=True)
            if cleaned:offers.append(cleaned)
            else:rejection_reasons[rejection_hint(row,now,verified_live=True)]+=1
    distinct={o["id"]:o for o in offers if o["id"]}
    # Collect genuine PrizePicks lines independently of the priced sportsbook
    # AI board, which may be empty when The Odds API credits run out.
    schedule_games=(schedule or {}).get("games",[])
    board_offers=[]
    ambiguous=0
    assignment_reasons=Counter()
    for original in distinct.values():
        item=dict(original)
        possibilities=[]
        same_team=0
        opponent_valid=0
        time_valid=0
        for game in schedule_games:
            try:
                start=timeparse(game.get("start"))
                if not start or start<=now:continue
                opponents=expected_opponents(game.get("game"),item["team"])
                if not opponents:continue
                same_team+=1
                if item["opponent"] and item["opponent"] not in opponents:continue
                opponent_valid+=1
                stated=timeparse(item.get("starts_at"))
                if stated and abs((start-stated).total_seconds())>30*60:continue
                time_valid+=1
                if not item["opponent"] and not stated:continue
                possibilities.append(game)
            except (TypeError,ValueError,KeyError):continue
        if len(possibilities)==1:
            game=possibilities[0]
            item["game"]=game["game"]
            item["starts_at"]=item["starts_at"] or game["start"]
            item["event_start_source"]="provider" if original["starts_at"] else "verified_internal_schedule"
            board_offers.append(item)
        elif len(possibilities)>1:
            ambiguous+=1
            assignment_reasons["ambiguous_multiple_games"]+=1
        elif not item["opponent"] and not item["starts_at"]:
            assignment_reasons["missing_opponent_and_tipoff"]+=1
        elif same_team==0:
            assignment_reasons["team_not_in_future_schedule"]+=1
        elif opponent_valid==0:
            assignment_reasons["opponent_mismatch"]+=1
        elif time_valid==0:
            assignment_reasons["tipoff_time_mismatch"]+=1
        else:
            assignment_reasons["no_unique_verified_fixture"]+=1
    matched=[]
    unmatched=0
    for comparison in comparisons:
        suitable=[o for o in distinct.values() if match(o,comparison,now=now)]
        if not suitable:
            unmatched+=1
            continue
        # The same projection may carry multiple selectable tiers; preserve them.
        for o in suitable:
            projection=numeric(comparison.get("combined_projection"))
            if projection is None:projection=numeric(comparison.get("projection"))
            matched.append(dict(o,starts_at=o["starts_at"] or comparison["start"],
                event_start_source="provider" if o["starts_at"] else "verified_internal_schedule",
                combined_projection=projection,
                difference=round(projection-o["line"],2) if projection is not None else None,
                ai_direction="MORE" if projection is not None and projection>o["line"] else
                             "LESS" if projection is not None and projection<o["line"] else "NO LEAN"))
    status=("LIVE_THIRD_PARTY_PRIZEPICKS_LINES" if matched or board_offers
            else "LIVE_NO_MATCHED_PRIZEPICKS_LINES")
    return {"status":status,
        "source":"Independent prizepicksapi.com (not affiliated with PrizePicks)",
        "source_url":"https://prizepicksapi.com/docs",
        "generated_at":now.isoformat(),
        "provider_status":"partial" if "partial" in statuses else statuses[0] if statuses else "unknown",
        "pages_read":len(raw_pages),"partial_board":bool(cursors and cursors[-1]),
        "raw_rows_read":raw_count,"eligible_upcoming_offers":len(distinct),
        "filtered_out_reasons":dict(sorted(rejection_reasons.items())),
        "match_method":"EXACT_PLAYER_TEAM_STAT_AND_VERIFIED_SCHEDULE_OR_30_MIN_TIPOFF",
        "matched_count":len(matched),"unmatched_ai_comparisons":unmatched,
        "independent_board_count":len(board_offers),
        "games_with_independent_lines":len({o["game"] for o in board_offers}),
        "unassigned_or_ambiguous_events":len(distinct)-len(board_offers),
        "ambiguous_event_matches":ambiguous,
        "unassigned_reason_counts":dict(sorted(assignment_reasons.items())),
        "board_offers":board_offers,
        "offers":matched,
        "notice":"Read-only third-party observations. May lag the app. FanDuel odds and EV are separate; PrizePicks pick'em lines are NOT American-odds quotes."}

def read_url(url,key):
    req=urllib.request.Request(url,headers={
        "Authorization":"Bearer "+key,
        "Accept":"application/json",
        "X-User-Request":"Read NBA PrizePicks lines for Sports-Bot dashboard comparison"})
    with urllib.request.urlopen(req,timeout=30) as reply:
        data=json.load(reply)
        if isinstance(data,dict):
            # Provider-reported credit accounting only; never publish keys.
            for header,field in (("X-Credits-Cost","charged_credits"),
                                ("X-Credits-Remaining","remaining_credits"),
                                ("X-Usage-Unit","usage_unit")):
                value=reply.headers.get(header)
                if value is not None:
                    data.setdefault("_client_credit_usage",{})[field]=str(value)[:45]
        return data

def quota_guard(saved,health,now,topup=None):
    """Protect the monthly allowance while recognizing separately funded top-ups.

    A newly successful authenticated probe can verify manual replenishment.
    Old 429 retry hints are not proof the user's account is still exhausted
    after a verified later provider check. Monthly rollover may also restore
    credits. Unknown evidence fails closed on confirmed depletion.
    """
    checked=timeparse(health.get("checked_at"))
    old=timeparse(saved.get("generated_at"))
    recovered=(health.get("status")=="API_ACCESS_CONFIRMED"
               and checked is not None and old is not None and checked>old)
    remaining=saved.get("remaining_provider_credits")
    # An HTTP 200 charged read proves the vendor is accepting account
    # requests despite a zero monthly header. It does not disclose the
    # remaining purchased top-up balance. Budget: MAX_PAGES=4 at no more than
    # the published 10-credit compact-page cost, no more often than 6h.
    # Stop when the vendor itself rejects the paid request with HTTP 429.
    # Require a *newer* one-shot authenticated successful read and only
    # authorize the immediately following bounded full-slate refresh.
    proof=topup if isinstance(topup,dict) else {}
    confirmed=timeparse(proof.get("checked_at"))
    topup_access=(proof.get("status")=="LIVE_READ_SUCCEEDED"
        and proof.get("http_status")==200 and proof.get("provider_mode")=="live"
        and proof.get("provider_source_status")=="fresh"
        and isinstance(proof.get("returned_rows"),int)
        and proof["returned_rows"]>0
        and isinstance(proof.get("request_cost"),int)
        and 0<proof["request_cost"]<=10
        and confirmed is not None and confirmed<=now
        and 0<=(now-confirmed).total_seconds()<36*3600)
    # Avoid exhausting finite purchased credits by rebuilding the full board
    # after every unrelated repository commit or twice within one slate.
    if (topup_access and old and 0<=(now-old).total_seconds()<6*3600
        and saved.get("status")=="LIVE_THIRD_PARTY_PRIZEPICKS_LINES"):
        return "TOPUP_REFRESH_COOLDOWN_PRESERVE"
    if (saved.get("status")=="LIVE_THIRD_PARTY_PRIZEPICKS_LINES"
        and remaining is not None and str(remaining).isdigit()
        and int(remaining)<=0):
        if old and (now.year,now.month)!=(old.year,old.month):
            return "MONTH_ROLLOVER_RECHECK_ALLOWED"
        return ("REPLENISHED_ACCESS_CONFIRMED" if recovered else
                "TOPUP_PAID_READ_CONFIRMED" if topup_access else
                "ZERO_PROVIDER_CREDITS_PRESERVE")
    if saved.get("status")=="PROVIDER_RATE_LIMITED" and saved.get("provider_error_code")=="MONTHLY_QUOTA_EXCEEDED":
        if recovered:return "REPLENISHED_ACCESS_CONFIRMED"
        if topup_access:return "TOPUP_PAID_READ_CONFIRMED"
        if old and (now.year,now.month)!=(old.year,old.month):
            return "MONTH_ROLLOVER_RECHECK_ALLOWED"
        return "QUOTA_LOCKED_PRESERVE"
    return "REQUEST_ALLOWED"

def targeted_team_searches(schedule, board, now, limit=MAX_TARGETED_READS):
    """Select urgent uncovered matchups for narrowly filtered paid reads.

    Only schedule-confirmed games tipping within 24h are eligible. Never
    pretend the partial four-page board proves that later games have no lines.
    Each selected team is queried once; the provider may still return no data.
    """
    if not isinstance(schedule,dict) or not isinstance(board,dict):return []
    observed={str(row.get("game")) for row in board.get("board_offers",[])
              if isinstance(row,dict) and row.get("game")}
    missing=[]
    seen=set()
    for game in schedule.get("games",[]):
        if not isinstance(game,dict):continue
        name=game.get("game")
        start=timeparse(game.get("start"))
        if not isinstance(name,str) or name in observed or not start:continue
        seconds=(start-now).total_seconds()
        if not 0<seconds<=24*3600:continue
        teams=name.split(" @ ")
        if len(teams)!=2:continue
        for team in teams:
            code=TEAM_ABBREVIATIONS.get(team.strip())
            if not code or code in seen:continue
            seen.add(code)
            missing.append((seconds,code))
    return [code for _,code in sorted(missing)[:max(0,int(limit))]]

def main():
    key=os.environ.get("PRIZEPICKS_API_KEY","").strip()
    if not key:
        out={"status":"NOT_CONFIGURED","generated_at":dt.datetime.now(dt.timezone.utc).isoformat(),
             "offers":[],"matched_count":0,
             "notice":"Add PRIZEPICKS_API_KEY as a GitHub Actions repository secret to enable this independent feed. FanDuel continues unchanged."}
        DEST.write_text(json.dumps(out,indent=2)+"\n")
        print("PrizePicks API key missing; publishing NOT_CONFIGURED status, no vendor request.",flush=True)
        return
    if DEST.exists() and os.environ.get("PRIZEPICKS_FORCE_REFRESH")!="1":
        # Monthly credit header may read zero while separately purchased
        # top-up credits are available. A single billed compact read is the
        # only reliable proof; do not treat zero monthly credits as a hard lock.
        try:
            saved_check=json.loads(DEST.read_text())
            topup_path=ROOT/"docs/prizepicks_topup_probe.json"
            proof=json.loads(topup_path.read_text()) if topup_path.exists() else {}
            verified=timeparse(proof.get("checked_at"))
            now_check=dt.datetime.now(dt.timezone.utc)
            old_monthly=saved_check.get("remaining_provider_credits")
            if (str(old_monthly)=="0" and
                (verified is None or (now_check-verified).total_seconds()>36*3600)):
                from probe_prizepicks_topup import probe
                new_proof=probe(key)
                topup_path.write_text(json.dumps(new_proof,indent=2)+"\n")
                print("Top-up probe:",new_proof.get("status"),
                      "HTTP:",new_proof.get("http_status"),
                      "charged:",new_proof.get("request_cost"),
                      "(the exhausted monthly balance may exclude purchased top-ups)")
        except (OSError,ValueError,TypeError,ImportError) as error:
            print("Top-up probe unavailable:",type(error).__name__)

        try:
            saved=json.loads(DEST.read_text())
            health_path=ROOT/"docs/prizepicks_connection_health.json"
            health=json.loads(health_path.read_text()) if health_path.exists() else {}
            topup_path=ROOT/"docs/prizepicks_topup_probe.json"
            topup=json.loads(topup_path.read_text()) if topup_path.exists() else {}
            decision=quota_guard(saved,health,dt.datetime.now(dt.timezone.utc),topup=topup)
            if decision in ("ZERO_PROVIDER_CREDITS_PRESERVE","QUOTA_LOCKED_PRESERVE","TOPUP_REFRESH_COOLDOWN_PRESERVE"):
                print("PrizePicks quota guard:",decision,
                      "- zero API calls; authentic last-observed board preserved.",
                      flush=True)
                return
        except (ValueError,TypeError,KeyError,FileNotFoundError):
            print("Quota status could not be inspected; authentic file retained.",flush=True)
            return
    comp=json.loads((ROOT/"docs/ai_comparisons.json").read_text())
    if comp.get("status")!="EXPERIMENTAL_NON_CALIBRATED":
        raise ValueError("AI comparison source invalid")
    # Use cursor pagination over all active NBA offers, not a 3-player sample.
    pages=[]
    requested=[]
    cursor=None
    seen_cursors=set()
    try:
        for index in range(MAX_PAGES):
            params=standard_query(cursor=cursor)
            page=read_url(BASE+"?"+urllib.parse.urlencode(params),key)
            if not isinstance(page,dict) or not isinstance(page.get("meta"),dict):
                raise ValueError("Invalid authenticated PrizePicks page")
            pages.append(page)
            requested.append(index+1)
            cursor=page["meta"].get("next_cursor")
            if not cursor:break
            if cursor in seen_cursors:raise ValueError("Repeated PrizePicks page cursor")
            seen_cursors.add(cursor)
    except urllib.error.HTTPError as err:
        # Do not retry 429: it can signal monthly credits, not just a minute.
        if err.code!=429:raise
        try:
            problem=json.loads(err.read().decode("utf-8"))
        except (ValueError,UnicodeError):
            problem={}
        detail=problem.get("error",{})
        code=detail.get("code","HTTP_429") if isinstance(detail,dict) else "HTTP_429"
        retry_after=err.headers.get("Retry-After")
        out={"status":"PROVIDER_RATE_LIMITED","generated_at":dt.datetime.now(dt.timezone.utc).isoformat(),
             "offers":[],"matched_count":0,
             "provider_error_code":str(code)[:80],
             "retry_after_seconds":retry_after if retry_after and str(retry_after).isdigit() else None,
             "pages_read":len(pages),
             "notice":"Independent PrizePicks provider returned 429; no live lines displayed. Check plan quota or Retry-After. FanDuel remains separate."}
        if DEST.exists():
            try:
                saved=json.loads(DEST.read_text())
                if saved.get("status")=="LIVE_THIRD_PARTY_PRIZEPICKS_LINES" and saved.get("board_offers"):
                    print("Independent PrizePicks rate limited:",out["provider_error_code"],
                          "- preserving the last verified snapshot, never publishing stale offers as fresh.",flush=True)
                    return
            except (OSError,ValueError,TypeError):pass
        DEST.write_text(json.dumps(out,indent=2)+"\n")
        print("Independent PrizePicks rate limited:",out["provider_error_code"],
              "retry after:",out["retry_after_seconds"],flush=True)
        return
    schedule_path=ROOT/"docs/nba_schedule.json"
    schedule=json.loads(schedule_path.read_text()) if schedule_path.exists() else {}
    # GitHub-hosted NBA/ESPN schedule endpoints can fail independently while
    # authenticated PrizePicks returns 4,000 real upcoming player props.
    # Recover only exact fixture identities/time from an EARLIER VERIFIED
    # authentic PrizePicks event archive, never its expired player lines.
    valid_now=dt.datetime.now(dt.timezone.utc)
    known_events=ROOT/"docs/prizepicks_model_input.json"
    previous=json.loads(known_events.read_text()) if known_events.exists() else {}
    old_observation=timeparse(previous.get("source_generated_at"))
    independent=(previous.get("source")=="AUTHENTIC_PRIZEPICKS_PICKEM_NO_ODDS"
        and old_observation and 0<=(valid_now-old_observation).total_seconds()<=36*3600)
    fixture_keys={(x.get("game"),str(x.get("start"))) for x in schedule.get("games",[])
                  if isinstance(x,dict)}
    if independent:
        appended=[]
        for event in previous.get("events_covered",[]):
            if not isinstance(event,dict):continue
            game=event.get("game")
            start=timeparse(event.get("start"))
            if not game or not start or not valid_now<start<valid_now+dt.timedelta(hours=30):
                continue
            if not expected_opponents(game,"BOS") and not any(
                expected_opponents(game,t) for t in ("ATL","BKN","CHA","CHI","CLE",
                "DAL","DEN","DET","GSW","HOU","IND","LAC","LAL","MEM","MIA",
                "MIL","MIN","NOP","NYK","OKC","ORL","PHI","PHX","POR",
                "SAC","SAS","TOR","UTA","WAS")):
                continue
            canonical=(game,start.isoformat())
            if canonical in fixture_keys:continue
            appended.append({"game":game,"start":start.isoformat(),
                "game_state":"pre","fixture_source":
                "PRIOR_VERIFIED_PRIZEPICKS_EVENT_TIME_NOT_STALE_LINE"})
            fixture_keys.add(canonical)
        if appended:
            schedule={**schedule,"games":list(schedule.get("games",[]))+appended,
                "coverage_complete":False}
            print("Recovered exact verified provider matchup times:",len(appended),
                  "from prior authentic fixture archive; not reusing old lines")
    # Prefer a few near-tipoff teams missing from the truncated 4-page
    # board. Search is a documented vendor-side team/player filter, not a
    # workaround for authentication or payment. Do not spend credits for
    # games over 24 hours away or rerun the entire source again.
    full_board_partial=bool(cursor)
    baseline=publish(pages,[],schedule=schedule)
    targeted_queries=(targeted_team_searches(schedule,baseline,valid_now)
                      if full_board_partial else [])
    targeted_attempts=[]
    for code in targeted_queries:
        try:
            query=standard_query(search=code,limit=TARGETED_PAGE_SIZE)
            target=read_url(BASE+"?"+urllib.parse.urlencode(query),key)
            if not isinstance(target,dict) or not isinstance(target.get("meta"),dict):
                raise ValueError("Malformed targeted PrizePicks page")
            if target["meta"].get("mode")!="live" or target["meta"].get("source_status") in ("failed","stale"):
                raise ValueError("Unverified targeted source")
            pages.append(target)
            requested.append("search:"+code)
            targeted_attempts.append({"team":code,"status":"RETURNED",
                                      "rows":len(target.get("data",[]))
                                      if isinstance(target.get("data"),list) else None,
                                      "partial":bool(target["meta"].get("next_cursor"))})
        except urllib.error.HTTPError as err:
            targeted_attempts.append({"team":code,"status":"HTTP_ERROR",
                                      "http_status":err.code})
            # Provider quota enforcement is authoritative: never retry 429.
            if err.code in (402,403,429):break
        except (ValueError,TypeError,urllib.error.URLError,TimeoutError):
            targeted_attempts.append({"team":code,"status":"INVALID_OR_UNAVAILABLE"})
    out=publish(pages,comp["comparisons"],schedule=schedule)
    out["partial_board"]=out["partial_board"] or full_board_partial
    out["targeted_team_queries"]=targeted_attempts
    out["targeted_reads_attempted"]=len(targeted_attempts)
    usage=[p.get("_client_credit_usage",{}) for p in pages]
    out["total_provider_charged_credits"]=sum(int(x["charged_credits"]) for x in usage
        if str(x.get("charged_credits","")).isdigit())
    out["remaining_provider_credits"]=next((int(x["remaining_credits"]) for x in reversed(usage)
        if str(x.get("remaining_credits","")).isdigit()),None)
    out["provider_usage_units"]=sorted(set(x.get("usage_unit") for x in usage if x.get("usage_unit")))
    out["page_size_requested"]=PAGE_SIZE
    out["page_view"]="compact"
    out["max_pages_budget"]=MAX_PAGES
    out["source_query"]="NBA_ACTIVE_STANDARD_TIER_CURSOR_PAGED"
    out["board_coverage_scope"]="NBA_ACTIVE_STANDARD_TIER_ONLY"
    out["complete_provider_board"]=not out["partial_board"] and out["provider_status"]=="fresh"
    out["pages_requested"]=len(requested)
    # Always record the actual paid API outcome, even if it supplied no
    # authentic upcoming rows. Do not mask a failed refresh as successful.
    health_path=ROOT/"docs/prizepicks_refresh_health.json"
    diagnostic={"checked_at":dt.datetime.now(dt.timezone.utc).isoformat(),
        "status":"FRESH_LINES_PUBLISHED" if out["independent_board_count"]>0 else
                 "PAID_READ_NO_FRESH_USABLE_OFFERS",
        "api_requests_made":len(requested),
        "provider_pages_read":out["pages_read"],
        "provider_status":out["provider_status"],
        "raw_rows":out["raw_rows_read"],
        "eligible_upcoming_offers":out["eligible_upcoming_offers"],
        "matched_upcoming_offers":out["independent_board_count"],
        "rejected_by_reason":out["filtered_out_reasons"],
        "unassigned_or_ambiguous_events":out["unassigned_or_ambiguous_events"],
        "unassigned_reason_counts":out["unassigned_reason_counts"],
        "credits_reported_charged":out["total_provider_charged_credits"],
        "monthly_credits_header":out["remaining_provider_credits"],
        "topup_balance_not_exposed_by_monthly_header":True,
        "targeted_team_queries":out["targeted_team_queries"],
        "targeted_reads_attempted":out["targeted_reads_attempted"],
        "source_board_remains_partial":out["partial_board"],
        "stale_quotes_published_as_current":False}
    health_path.write_text(json.dumps(diagnostic,indent=2)+"\n")
    print("PrizePicks authenticated paid-read result:",
          diagnostic["status"],"requests:",len(requested),
          "returned:",diagnostic["raw_rows"],
          "verified upcoming:",diagnostic["eligible_upcoming_offers"],
          "rejections:",diagnostic["rejected_by_reason"],
          "charged:",diagnostic["credits_reported_charged"],
          flush=True)
    if out["independent_board_count"]==0 and out["matched_count"]==0 and DEST.exists():
        print("No fresh eligible PrizePicks events; preserving previous feed as stale.",flush=True)
        return
    DEST.write_text(json.dumps(out,indent=2)+"\n")
    print("PrizePicks matched observations:",out["matched_count"],
          "raw rows:",out["raw_rows_read"],"eligible:",out["eligible_upcoming_offers"],
          "pages:",out["pages_read"],"partial board:",out["partial_board"],
          "rejections:",out["filtered_out_reasons"],flush=True)

if __name__=="__main__":main()
