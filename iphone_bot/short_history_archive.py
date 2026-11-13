"""Append-only prospective research receipts. Never primary picks or official grades."""
from copy import deepcopy
from datetime import datetime, timezone, timedelta
import hashlib
import json
import math
from pathlib import Path
from .live_lagged_matchup_sidecar import stamp
from .short_history_candidate import MODEL
from .live_multimarket_matchup import ET

STATUS = 'SHORT_HISTORY_PROSPECTIVE_RESEARCH_ARCHIVE'

def archive(previous, feed, now=None):
    now = stamp(now or datetime.now(timezone.utc))
    if previous is None:
        previous = {'status': STATUS, 'records': []}
    if previous.get('status') != STATUS or not isinstance(previous.get('records'), list):
        raise ValueError('INVALID_EXISTING_RESEARCH_ARCHIVE')
    records = deepcopy(previous['records'])
    keys = {r['prospective_key'] for r in records}
    if len(keys) != len(records):
        raise ValueError('DUPLICATE_EXISTING_RESEARCH_RECEIPT')
    rejected = 0
    if (feed.get('status') == 'SHORT_HISTORY_TRAINED_RESEARCH_PROJECTIONS'
            and not feed.get('blocker') and feed.get('model') == MODEL):
        for row in feed.get('estimates', []):
            try:
                captured, tip = stamp(row['captured_at']), stamp(row['start'])
                generated, quoted = stamp(feed['generated_at']), stamp(row['market_updated'])
                if not (quoted <= captured <= generated <= now < tip and
                        now-generated <= timedelta(minutes=30)):
                    raise ValueError('NOT_OBSERVED_PRETIP')
                if (row['model'] != MODEL or row['research_only'] is not True or
                        row['trained_model'] is not True or row['primary_model_eligible'] is not False or
                        row['official_grade_eligible'] is not False or row['stat'] not in ('PTS','REB') or
                        row['pickem_tier'] != 'standard' or row['standard_line_two_sided_verified'] is not True or
                        row['source'] != 'INDEPENDENTLY_CROSSCHECKED_PLAYER_HISTORY'):
                    raise ValueError('NOT_ELIGIBLE_RESEARCH')
                if any(row.get(k) is not None for k in ('hit_probability','estimated_hit_chance','calibrated_probability')):
                    raise ValueError('UNSUPPORTED_PROBABILITY')
                if any(type(row[k]) not in (int,float) or not math.isfinite(row[k]) or row[k]<0
                       for k in ('projection','line','descriptive_baseline_projection')):
                    raise ValueError('INVALID_NUMBER')
                if not 3 <= row['prior_games'] <= 7 or len(row['history_dates']) != row['prior_games']:
                    raise ValueError('INVALID_COHORT')
                if len(set(row['history_dates'])) != row['prior_games'] or any(
                        d >= tip.astimezone(ET).date().isoformat() for d in row['history_dates']):
                    raise ValueError('NON_PRIOR_OR_DUPLICATE_HISTORY')
                # Model version + exact offer: first receipt wins across repeat training runs.
                artifact = feed['model_artifact_sha256']
                if len(artifact)!=64 or any(c not in '0123456789abcdef' for c in artifact):
                    raise ValueError('INVALID_ARTIFACT_HASH')
                identity = [MODEL, str(row['player_id']), row['team'], row['opponent'],
                            row['game'], tip.isoformat(), row['stat'], float(row['line'])]
                key = hashlib.sha256(json.dumps(identity,separators=(',',':')).encode()).hexdigest()
                if key in keys:
                    continue
                saved = deepcopy(row)
                saved.update(prospective_key=key, archived_at=now.isoformat(),
                             model_artifact_sha256=artifact, source_generated_at=generated.isoformat())
                records.append(saved);keys.add(key)
            except (ValueError, TypeError, KeyError, OverflowError):
                rejected += 1
    return {'status':STATUS,'records':records,'count':len(records),'rejected_current':rejected,
            'updated_at':now.isoformat(),'primary_model_eligible':False,'official_grade_eligible':False,
            'prospective_validation_verified':False,
            'notice':'Immutable research receipts only. No official grades, hit rates, or promotion implied.'}

def main():
    root=Path(__file__).resolve().parents[1]
    path=root/'docs/short_history_prospective_archive.json'
    previous=json.loads(path.read_text()) if path.exists() else None
    feed=json.loads((root/'docs/short_history_model.json').read_text())
    result=archive(previous,feed)
    path.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('status','count','rejected_current')}))

if __name__=='__main__':main()
