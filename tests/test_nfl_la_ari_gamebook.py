import copy,json,sys,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import verified_nfl_gamebook as b
import reconcile_nfl_picks as r
GAME='2026_10_LA_ARI'
class RamsCardinalsEvidenceTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.data=json.loads((ROOT/f'docs/nfl/data/boxscores/verified_gamebook_{GAME}.json').read_text())
  cls.schedule={g['game_id']:g for g in json.loads((ROOT/'docs/nfl/data/schedule_2026.json').read_text())['games']}
 def test_complete_totals_fantasy_and_participation(self):
  rows=b.validate(self.data,self.schedule[GAME]);p={x['player']:x for x in rows}
  for n,v in {'Tyler Higbee':10.7,'Colby Parkinson':3.1,'Simi Fehoko':3.1,'Bam Knight':1.9,'Tyler Allgeier':1.4,'Trey McBride':8.7,'Kyren Williams':5.2,'Blake Corum':20.9,'Elijah Higgins':0,'Reggie Virgil':0}.items():
   self.assertAlmostEqual(b.fantasy(p[n]),v)
  self.assertEqual(p['Elijah Higgins']['offensive_snaps'],24)
  self.assertEqual(p['Reggie Virgil']['offensive_snaps'],16)
  self.assertEqual(p['Reggie Virgil']['targets'],0) # Explicitly nullified PBP pass, not a valid target.
  self.assertFalse({'Jacoby Brissett','Gardner Minshew','Michael Wilson'} & set(p))
 def test_tampering_and_wrong_event_rejected(self):
  d=copy.deepcopy(self.data);d['players'][0]['receptions']+=1
  with self.assertRaises(ValueError):b.validate(d,self.schedule[GAME])
  for k,v in [('status','pre'),('home_score',7),('game_id','2026_10_LAC_BAL')]:
   with self.assertRaises(ValueError):b.validate(self.data,{**self.schedule[GAME],k:v})
 def test_zero_stat_substitution_alone_rejected_even_if_review_hash_changed(self):
  d=copy.deepcopy(self.data)
  p=next(x for x in d['players'] if x['player']=='Reggie Virgil')
  p.pop('offensive_snaps',None);p.pop('offensive_starter',None)
  specs=copy.deepcopy(b.REVIEWED_GAMES);specs[GAME]['sha']=b.digest(d)
  with patch.object(b,'REVIEWED_GAMES',specs):
   with self.assertRaisesRegex(ValueError,'offensive participation'):b.validate(d,self.schedule[GAME])
 def test_only_sixteen_standard_pending_rows_change_and_frozen_fields_preserved(self):
  root=ROOT/'docs/nfl/data';history=r.read_csv(root/r.ARCHIVE.name);before=copy.deepcopy(history)
  args=(r.verified_inactives(root),r.verified_zero_snaps(root),r.verified_full_game_scoring(root))
  with patch.object(b,'REVIEWED_GAMES',{k:v for k,v in b.REVIEWED_GAMES.items() if k!=GAME}):
   boxes,bad=r.verified_boxscores(self.schedule,root/'boxscores')
   oldg,oldp,n=r.grade_finals(history,self.schedule,boxes,bad,*args)
  boxes,bad=r.verified_boxscores(self.schedule,root/'boxscores')
  newg,newp,m=r.grade_finals(history,self.schedule,boxes,bad,*args)
  identity=lambda x:tuple(x.get(k) for k in r.KEY)
  old={identity(x):x for x in oldg+oldp};new={identity(x):x for x in newg+newp}
  self.assertEqual(n,m);self.assertEqual(set(old),set(new));self.assertEqual(history,before)
  changed=[(old[k],new[k]) for k in old if old[k]!=new[k]]
  self.assertEqual(len(changed),16)
  for a,c in changed:
   self.assertEqual(c['game_id'],GAME);self.assertEqual(c['odds_type'],'standard');self.assertEqual(c['grade_status'],'graded')
   for field in r.FIELDS:self.assertEqual(a.get(field),c.get(field),field)
  self.assertEqual(sum(x['odds_type']=='standard' for x in oldp)-sum(x['odds_type']=='standard' for x in newp),16)
  self.assertEqual(sum(x['odds_type']=='standard' and x['game_id']==GAME for x in newp),9)
if __name__=='__main__':unittest.main()
