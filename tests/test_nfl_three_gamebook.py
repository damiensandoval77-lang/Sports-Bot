import copy,json,sys,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import verified_nfl_gamebook as b
import reconcile_nfl_picks as r
GAMES={'2026_10_BUF_NYJ':17,'2026_10_SEA_LV':15,'2026_10_MIN_GB':10}
class ThreeReviewedGamebooksTests(unittest.TestCase):
 def test_replay_only_reviewed_standard_outcomes_and_preserve_targets_and_injury_hold(self):
  root=ROOT/'docs/nfl/data';s={x['game_id']:x for x in json.loads((root/'schedule_2026.json').read_text())['games']}
  h=r.read_csv(root/r.ARCHIVE.name);before=copy.deepcopy(h)
  args=(r.verified_inactives(root),r.verified_zero_snaps(root),r.verified_full_game_scoring(root))
  with patch.object(b,'REVIEWED_GAMES',{k:v for k,v in b.REVIEWED_GAMES.items() if k not in GAMES}):
   boxes,bad=r.verified_boxscores(s,root/'boxscores');oldg,oldp,n=r.grade_finals(h,s,boxes,bad,*args)
  boxes,bad=r.verified_boxscores(s,root/'boxscores');newg,newp,m=r.grade_finals(h,s,boxes,bad,*args)
  key=lambda x:tuple(x.get(k) for k in r.KEY)
  old={key(x):x for x in oldg+oldp};new={key(x):x for x in newg+newp}
  self.assertEqual(n,m);self.assertEqual(set(old),set(new));self.assertEqual(h,before)
  changed=[(old[k],new[k]) for k in old if old[k]!=new[k]]
  self.assertEqual(len(changed),42)
  for game,count in GAMES.items():self.assertEqual(sum(c['game_id']==game for a,c in changed),count)
  for a,c in changed:
   self.assertEqual(c['odds_type'],'standard');self.assertNotEqual(c['target'],'TGT');self.assertEqual(c['grade_status'],'graded')
   self.assertNotEqual(c['player_id'],'00-0041511')
   for field in r.FIELDS:self.assertEqual(a.get(field),c.get(field),field)
  self.assertEqual(sum(x['odds_type']=='standard' for x in oldp)-sum(x['odds_type']=='standard' for x in newp),42)
  held=[x for x in newp if x['game_id']=='2026_10_BUF_NYJ' and x['player_id']=='00-0041511' and x['odds_type']=='standard']
  self.assertEqual(len(held),4)
  self.assertNotIn('00-0041391',boxes['2026_10_BUF_NYJ']) # Defender not a fantasy candidate.
 def test_transcripts_and_exact_event_guards(self):
  root=ROOT/'docs/nfl/data';s={x['game_id']:x for x in json.loads((root/'schedule_2026.json').read_text())['games']}
  for game in GAMES:
   d=json.loads((root/'boxscores'/f'verified_gamebook_{game}.json').read_text())
   b.validate(d,s[game])
   with self.assertRaises(ValueError):b.validate(d,{**s[game],'status':'pre'})
   d['players'][0]['fumbles_lost']+=1
   with self.assertRaises(ValueError):b.validate(d,s[game])
if __name__=='__main__':unittest.main()
