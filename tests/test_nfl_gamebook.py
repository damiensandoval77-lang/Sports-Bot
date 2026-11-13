import copy,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import verified_nfl_gamebook as b
import reconcile_nfl_picks as r
class OfficialGamebookTests(unittest.TestCase):
 def setUp(self):
  self.data=json.loads((ROOT/'docs/nfl/data/boxscores'/b.FILE).read_text())
  self.schedule={g['game_id']:g for g in json.loads((ROOT/'docs/nfl/data/schedule_2026.json').read_text())['games']}
 def test_complete_source_and_exact_fantasy(self):
  rows=b.validate(self.data,self.schedule[b.GAME]);players={p['player']:p for p in rows}
  for name,value in {'Jayden Daniels':22.76,'J.J. McCarthy':18.12,'Malik Nabers':8.4,'Isaiah Likely':27.7,'Devin Singletary':.3,'Van Jefferson':0}.items():self.assertAlmostEqual(b.fantasy(players[name]),value)
  self.assertEqual(players['John Bates']['receiving_yards'],0)
  self.assertEqual(players['Devin Singletary']['receiving_yards'],0)
 def test_unreviewed_transcription_rejected(self):
  self.data['players'][0]['passing_yards']+=1
  with self.assertRaises(ValueError):b.validate(self.data,self.schedule[b.GAME])
 def test_wrong_final_event_or_schedule_rejected(self):
  for key,value in [('status','live'),('home_score',22),('week',11),('kickoff_utc','2026-11-14T01:15Z')]:
   scheduled={**self.schedule[b.GAME],key:value}
   with self.assertRaises(ValueError):b.validate(self.data,scheduled)
 def test_complete_ledger_invariants_independently(self):
  for mutate in [lambda d:d['players'][0].update(participation_page=2),lambda d:d['players'][0].update(passing_yards=None),lambda d:d['verified_team_totals']['WAS'].update(passing_yards=250),lambda d:d['category_membership']['rushing']['WAS'].pop(),lambda d:d['verified_game_scoring']['two_point_conversions'].append({}),lambda d:d['verified_game_scoring']['touchdowns'].pop(),lambda d:d['verified_fumbles_lost']['NYG'].update(player_lost=[]),lambda d:d['verified_game_scoring']['field_goals'].clear()]:
   data=copy.deepcopy(self.data);mutate(data)
   with patch.object(b,'REVIEWED_SHA',b.digest(data)):
    with self.assertRaises(ValueError):b.validate(data,self.schedule[b.GAME])
 def test_source_conflict_fails_without_overwrite(self):
  with tempfile.TemporaryDirectory() as d:
   Path(d,b.FILE).write_text(json.dumps(self.data))
   boxes={b.GAME:{self.data['players'][0]['player_id']:{**self.data['players'][0],'passing_yards':999}}}
   before=copy.deepcopy(boxes)
   with self.assertRaises(ValueError):b.supplement(d,self.schedule,boxes)
   self.assertEqual(boxes,before)
 def test_every_frozen_standard_line_settles_without_evidence_change(self):
  history=r.read_csv(ROOT/'docs/nfl/data'/r.ARCHIVE.name);before=copy.deepcopy(history)
  boxes,bad=r.verified_boxscores(self.schedule,ROOT/'docs/nfl/data/boxscores')
  grades,pending,_=r.grade_finals(history,self.schedule,boxes,bad)
  official=[x for x in grades if x['game_id']==b.GAME and x['odds_type']=='standard']
  self.assertEqual(len(official),74);self.assertFalse([x for x in pending if x['game_id']==b.GAME and x['odds_type']=='standard'])
  self.assertEqual(len({tuple(x[k] for k in r.KEY[1:]) for x in official}),74)
  self.assertEqual(sum(x['result']=='Push' for x in official),2)
  self.assertTrue(all(x['won']=='' for x in official if x['result']=='Push'))
  self.assertEqual(history,before)
if __name__=='__main__':unittest.main()
