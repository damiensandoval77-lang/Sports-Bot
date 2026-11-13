"""Isolated descriptive pretip estimates for 3-7 verified prior team games.

Not a trained model, calibrated probability, primary forecast, or official grade.
This module writes ONLY its separate live artifact. No performance metrics or
ledger exist until a distinct, prospectively validated grading path is built.
"""
import argparse
import json
import math
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from statistics import mean

from .live_lagged_matchup_sidecar import current_games, stamp
from .live_multimarket_matchup import ET, STATS, normalized_player_name, resolve_current_roster_identity, select_standard
from .new_ai_injury_context import injury_adjustment
from .multimarket_forecast_ledger import valid as primary_valid

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'docs/provisional_short_history.json'
STATUS = 'PROVISIONAL_SHORT_HISTORY_DESCRIPTIVE_BASELINE'
COHORT = 'PROVISIONAL_SHORT_HISTORY'
METHOD = 'ARITHMETIC_MEAN_PRIOR_SAME_TEAM_GAMES'
NOTICE = ('Provisional descriptive averages from 3-7 independently crosschecked prior team games. '
          'Not trained-model picks, injury-adjusted projections, betting probabilities or official grades. '
          'Excluded from primary coverage and all performance metrics.')


def empty_report(now, blocker=None):
    report = {'status': STATUS, 'cohort': COHORT, 'generated_at': stamp(now).isoformat(),
              'official_report_issued_at': None, 'trained_model': False,
              'primary_model_eligible': False, 'official_grade_eligible': False,
              'performance_metrics': None, 'estimates': [], 'count': 0,
              'excluded': {}, 'notice': NOTICE}
    if blocker:
        report['blocker'] = blocker
    return report


def estimates(records, feed, *, primary=None, now=None, injuries=None, news=None, free_watch=None):
    """Consume current_games() crosschecks, never CSV-only recovery or models."""
    now = stamp(now or datetime.now(timezone.utc))
    injuries, news, free_watch = injuries or {}, news or {}, free_watch or {}
    result = empty_report(now)
    # Read-only exclusion prevents a second, contradictory estimate beside
    # an already frozen primary pick. Never infer this from history counts.
    if (not isinstance(primary, dict) or primary.get('status') != 'FROZEN_NEW_AI_ALL_MARKET'
            or not isinstance(primary.get('records'), list)):
        return empty_report(now, 'PRIMARY_LEDGER_UNAVAILABLE_OR_INVALID')
    primary_keys = {(str(row['player_id']), row['team'], row['game'], stamp(row['start']),
                     row['stat'], float(row['line']))
                    for row in primary['records'] if primary_valid(row)}
    if (feed.get('source') != 'AUTHENTIC_PRIZEPICKS_PICKEM_NO_ODDS' or
            feed.get('status') != 'FRESH_AUTHENTIC_PRIZEPICKS_LINES' or feed.get('is_live') is not True):
        return empty_report(now, 'VERIFIED_STANDARD_FEED_UNAVAILABLE')
    try:
        feed_time = stamp(feed['updated_at'])
        if not timedelta(0) <= now-feed_time <= timedelta(hours=6):
            raise ValueError('stale')
    except (ValueError, KeyError, TypeError):
        return empty_report(now, 'FEED_TIMESTAMP_INVALID_OR_STALE')
    try:
        issued = stamp(injuries['report_issued_at'])
        if (injuries.get('status') != 'OFFICIAL_NBA_REPORT_VERIFIED' or
                injuries.get('injury_data_verified') is not True or
                not timedelta(0) <= now-issued <= timedelta(hours=6)):
            raise ValueError('unverified')
    except (ValueError, KeyError, TypeError):
        return empty_report(now, 'INJURY_CONTEXT_UNVERIFIED_OR_STALE')
    result['official_report_issued_at'] = issued.isoformat()
    selected, exclusions = select_standard(feed.get('picks', []))
    excluded = Counter(exclusions)
    output = []
    seen_offers = set()
    for offer in selected:
        try:
            tip, observed = stamp(offer['start']), stamp(offer['market_updated'])
            if not (observed <= now < tip and observed < tip and now-observed <= timedelta(hours=6)):
                raise ValueError('late')
        except (KeyError, ValueError, TypeError):
            excluded['LATE_INVALID_OR_STALE_QUOTE'] += 1
            continue
        day = tip.astimezone(ET).date().isoformat()
        if day != now.astimezone(ET).date().isoformat():
            excluded['OUTSIDE_TODAY_EASTERN_SLATE'] += 1
            continue
        # Construct identity exclusively as of this fixture. Same-day or later
        # appearances must not alter roster identity, eligibility or averages.
        prior = []
        bad_ids = set()
        by_day = defaultdict(list)
        names_by_id = defaultdict(set)
        for row in records:
            if not isinstance(row, dict):
                continue
            pid = str(row.get('id') or '')
            try:
                row_day = date.fromisoformat(str(row.get('date'))).isoformat()
            except (ValueError, TypeError):
                if pid: bad_ids.add(pid)
                continue
            if row_day >= day:
                continue
            by_day[(pid, row_day)].append(row)
            if row.get('history_source_confidence'):
                # Never elevate the existing CSV fallback into an independent
                # crosscheck just to reach this separate cohort's minimum.
                continue
            try:
                vals = {key: float(row[key]) for key in ('PTS', 'REB', 'AST', 'MIN')}
                if (not pid.isdigit() or not row.get('player') or not row.get('team') or
                        any(isinstance(row[key], bool) for key in vals) or
                        not all(math.isfinite(v) and v >= 0 for v in vals.values()) or
                        not 1 <= vals['MIN'] <= 60 or vals['PTS'] > 150 or
                        vals['REB'] > 50 or vals['AST'] > 40):
                    raise ValueError('invalid')
            except (ValueError, KeyError, TypeError):
                bad_ids.add(pid)
                continue
            names_by_id[pid].add(normalized_player_name(row['player']))
            prior.append({**row, 'id': pid, 'date': row_day, **vals})
        # Duplicate dates include same-ID different-team conflicts. Do not
        # silently deduplicate data into a seemingly eligible sample.
        bad_ids.update(pid for (pid, _), rows in by_day.items() if len(rows) != 1)
        bad_ids.update(pid for pid, names in names_by_id.items() if len(names) != 1)
        roster = defaultdict(set)
        latest = {}
        for row in prior:
            pid, team = row['id'], row['team']
            roster[normalized_player_name(row['player'])].add((pid, team))
            if pid not in latest or row['date'] > latest[pid][0]:
                latest[pid] = (row['date'], team)
        identity, reason = resolve_current_roster_identity(
            offer.get('player'), offer.get('game'), roster,
            {pid: value[1] for pid, value in latest.items()})
        if reason:
            excluded[reason] += 1
            continue
        pid, team, opponent = identity
        if (pid, team, offer['game'], tip, STATS[offer['stat']], float(offer['line'])) in primary_keys:
            excluded['ALREADY_PRIMARY_EXACT_IDENTITY'] += 1
            continue
        if offer.get('team') != team:
            excluded['QUOTE_TEAM_MISMATCH'] += 1
            continue
        if pid in bad_ids:
            excluded['INVALID_OR_DUPLICATE_PRIOR_HISTORY'] += 1
            continue
        history = sorted((row for row in prior if row['id'] == pid and row['team'] == team),
                         key=lambda row: row['date'])
        if not 3 <= len(history) < 8:
            excluded['OUTSIDE_PROVISIONAL_HISTORY_COHORT'] += 1
            continue
        # Explicit own QUESTIONABLE/DOUBTFUL/etc. is uncertainty, not available.
        own_statuses = {str(row.get('status', '')).upper() for row in injuries.get('players', [])
                        if str(row.get('player_id')) == pid and row.get('team') == team
                        and row.get('game_date') == day}
        if own_statuses - {'AVAILABLE'}:
            excluded['PLAYER_INJURY_STATUS_WITHHELD'] += 1
            continue
        components = {stat: mean(row[stat] for row in history) for stat in ('PTS', 'REB', 'AST')}
        context = injury_adjustment(components, pid, team, opponent, day, offer['start'], now,
                                    injuries, news, prior, free_watch=free_watch)
        if context.get('status') != 'NO_REPORTED_OUT' or context.get('factor') != 1.0:
            excluded['INJURY_AFFECTED_OR_UNCERTAIN_ESTIMATE_WITHHELD'] += 1
            continue
        stat = STATS[offer['stat']]
        key = (pid, team, offer['game'], tip.isoformat(), stat, float(offer['line']))
        if key in seen_offers:
            continue
        seen_offers.add(key)
        value = sum(components.values()) if stat == 'PRA' else components[stat]
        output.append({'player': offer['player'], 'player_id': pid, 'team': team,
                       'opponent': opponent, 'game': offer['game'], 'start': tip.isoformat(),
                       'stat': stat, 'line': float(offer['line']), 'projection': round(value, 3),
                       'captured_at': now.isoformat(), 'market_updated': observed.isoformat(),
                       'prior_games': len(history), 'history_dates': [row['date'] for row in history],
                       'method': METHOD, 'cohort': COHORT, 'label': 'Provisional estimate',
                       'research_only': True, 'trained_model': False, 'primary_model_eligible': False,
                       'official_grade_eligible': False, 'estimated_hit_chance': None,
                       'calibrated_probability': None, 'hit_probability': None,
                       'injury_context_status': context['status'],
                       'source': 'INDEPENDENTLY_CROSSCHECKED_PLAYER_HISTORY',
                       'pickem_tier': 'standard', 'standard_line_two_sided_verified': True})
    result.update(estimates=output, count=len(output), excluded=dict(excluded))
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--blocked', help='Publish an empty artifact instead of stale estimates')
    args = parser.parse_args()
    now = datetime.now(timezone.utc)
    failed = bool(args.blocked)
    if args.blocked:
        report = empty_report(now, args.blocked)
    else:
        try:
            import pandas as pd
            import requests
            from io import BytesIO
            def read(path):
                return json.loads((ROOT/path).read_text())
            # Source fetch is public, credit-free, and bounded. No model load,
            # training call, primary output write, or probability simulation.
            url = 'https://huggingface.co/datasets/cbratkovics/nba-game-logs/resolve/main/game_logs/game_logs_2026-27.parquet'
            response = requests.get(url, timeout=(12,45), headers={'User-Agent':'SportsBot-Provisional-History/1.0'})
            response.raise_for_status()
            if len(response.content) > 12_000_000:
                raise ValueError('Unexpected history size')
            source = pd.read_parquet(BytesIO(response.content))
            source = source.rename(columns={'player_id':'id', 'game_date':'date'})
            source['date'] = pd.to_datetime(source['date'], errors='raise').dt.strftime('%Y-%m-%d')
            form = read('docs/current_form.json')
            last_day = date.fromisoformat(form['latest_game_date'])
            if not 0 <= (now.astimezone(ET).date()-last_day).days <= 5:
                raise ValueError('Current history stale')
            records, coverage = current_games(read('data/nba/current/current_games.json'), source.to_dict(orient='records'))
            report = estimates(records, read('docs/prizepicks_model_input.json'), now=now,
                               primary=read('docs/lagged_matchup_all_market_ledger.json'),
                               injuries=read('docs/injury_context.json'),
                               news=read('docs/underdog_nba_injury_alerts.json'),
                               free_watch=read('docs/free_nba_injury_watch.json'))
            report['source_coverage'] = coverage
            failed = 'blocker' in report
        except Exception as exc:
            failed = True
            report = empty_report(now, 'SOURCE_OR_VALIDATION_ERROR:'+type(exc).__name__)
    OUTPUT.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({'status': report['status'], 'count': report['count'],
                      'blocker': report.get('blocker'), 'excluded': report['excluded']}))
    return 1 if failed else 0


if __name__ == '__main__':
    raise SystemExit(main())
