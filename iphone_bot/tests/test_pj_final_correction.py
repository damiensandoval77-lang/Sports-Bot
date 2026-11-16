"""Auditable one-off correction, not a relaxed general conflict override."""
import copy
import gzip
import hashlib
import json
import unittest
from pathlib import Path
from iphone_bot.fetch_final_boxscores import nba_boxscore_rows, espn_boxscore_rows
from iphone_bot.grade_frozen_ai_forecasts import settle_predictions
from iphone_bot.verified_final_cache import merge_rows, verified_row

ROOT=Path(__file__).resolve().parents[2]
EVIDENCE=ROOT/'research/final-corrections/2026-11-16-pj-washington-0022600232'

class PjFinalCorrectionTests(unittest.TestCase):
    def setUp(self):
        self.receipt=json.loads((EVIDENCE/'receipt.json').read_text())
        self.raw={}
        for source in self.receipt['sources']:
            if 'raw_gzip_file' not in source:continue
            raw=gzip.decompress((EVIDENCE/source['raw_gzip_file']).read_bytes())
            self.assertEqual(hashlib.sha256(raw).hexdigest(),source['raw_sha256'])
            self.raw[source['source']]=json.loads(raw)

    def test_official_final_exact_identity_derives_corrected_row(self):
        b=self.raw['nba_s3'];g=b['game']
        self.assertEqual(g['gameId'],'0022600232');self.assertEqual(g['gameStatus'],3)
        rows=[r for r in nba_boxscore_rows(g,b) if r.get('nba_person_id')=='1629023']
        self.assertEqual(rows,[self.receipt['corrected_row']])
        self.assertEqual((rows[0]['date'],rows[0]['team'],rows[0]['opponent']),('2026-11-14','DAL','CLE'))
        self.assertTrue(verified_row(rows[0]))

    def test_independent_espn_final_agrees_by_athlete_and_matchup(self):
        s=self.raw['espn'];h=s['header'];c=h['competitions'][0]
        self.assertEqual(h['id'],'401909981');self.assertTrue(c['status']['type']['completed'])
        found=[(group,table,a) for group in s['boxscore']['players'] for table in group['statistics'] for a in table['athletes'] if a['athlete']['id']=='4278078']
        self.assertEqual(len(found),1);group,table,a=found[0]
        self.assertEqual(group['team']['abbreviation'],'DAL')
        lookup=dict(zip(table['names'],a['stats']))
        self.assertEqual([float(lookup[k]) for k in ('PTS','REB','AST')],[10,3,1])
        event={'id':h['id'],'date':c['date'],'status':c['status'],'competitions':[c]}
        row=next(r for r in espn_boxscore_rows(event,s) if r['player']==a['athlete']['displayName'])
        for key in ('date','team','opponent','PTS','REB','AST','PRA'):
            self.assertEqual(row[key],self.receipt['corrected_row'][key])

    def test_superseded_evidence_retained_and_generic_conflict_still_rejected(self):
        old,new=self.receipt['superseded_row'],self.receipt['corrected_row']
        self.assertEqual((old['REB'],old['PRA']),(4,15))
        self.assertEqual({k for k in old.keys()|new.keys() if old.get(k)!=new.get(k)},set(self.receipt['changed_fields']))
        self.assertEqual(merge_rows([old],[new]),[])
        self.assertEqual(merge_rows([new],[new]),[new])

    def test_four_pending_resolve_by_person_id_without_rewriting_forecasts_or_existing_grades(self):
        forecasts=copy.deepcopy(self.receipt['original_forecasts']);before=copy.deepcopy(forecasts)
        existing=[{'status':'GRADED','player_id':'other','player':'Other','team':'BOS','game':'Other game','start':'2026-11-15T00:00:00Z','stat':'PTS','captured_at':'2026-11-14T00:00:00Z','actual':99,'projection':88,'error':-11}]
        prior=copy.deepcopy(existing)
        self.assertEqual(settle_predictions(forecasts,[self.receipt['superseded_row']],existing)['new_grades'],0)
        result=settle_predictions(forecasts,[self.receipt['corrected_row']],existing)
        self.assertEqual(result['new_grades'],4)
        self.assertEqual(forecasts,before);self.assertEqual(existing,prior)
        for row in prior:self.assertIn(row,result['records'])
        new=[r for r in result['records'] if r.get('player_id')=='1629023']
        self.assertEqual({r['stat']:r['actual'] for r in new},{'PTS':10,'REB':3,'AST':1,'PRA':14})
        for row in new:
            original=next(p for p in before if p['stat']==row['stat'])
            for key in ('projection','captured_at','start','game','player','team'):self.assertEqual(row[key],original[key])
        self.assertEqual(settle_predictions(forecasts,[self.receipt['corrected_row']],result['records'])['records'],result['records'])
