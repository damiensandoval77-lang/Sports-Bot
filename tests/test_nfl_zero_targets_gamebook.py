"""Only two exact complete-allocation target holds may be released."""
import copy,json,sys,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import verified_nfl_gamebook as b
import reconcile_nfl_picks as r
CASES={('2026_10_SEA_LV','00-0040648'),('2026_10_SF_DAL','00-0032775')}
class ZeroTargets(unittest.TestCase):
 def test_delta_exactly_two_standard_targets_no_other_mutation(self):
  root=ROOT/'docs/nfl/data';s={x['game_id']:x for x in json.loads((root/'schedule_2026.json').read_text())['games']}
  h=r.read_csv(root/r.ARCHIVE.name);before=copy.deepcopy(h)
  args=(r.verified_inactives(root),r.verified_zero_snaps(root),r.verified_full_game_scoring(root))
  validate=b.validate
  def held(*args):
   rows=copy.deepcopy(validate(*args))
   for p in rows:p.pop('verified_zero_targets',None)
   return rows
  with patch.object(b,'validate',held):
   boxes,bad=r.verified_boxscores(s,root/'boxscores');oldg,oldp,n=r.grade_finals(h,s,boxes,bad,*args)
  boxes,bad=r.verified_boxscores(s,root/'boxscores');newg,newp,m=r.grade_finals(h,s,boxes,bad,*args)
  key=lambda x:tuple(x.get(k) for k in r.KEY)
  old={key(x):x for x in oldg+oldp};new={key(x):x for x in newg+newp}
  self.assertEqual(n,m);self.assertEqual(set(old),set(new));self.assertEqual(h,before)
  changed=[(old[k],new[k]) for k in old if old[k]!=new[k]]
  self.assertEqual(len(changed),2)
  self.assertEqual({(c['game_id'],c['player_id']) for a,c in changed},CASES)
  for a,c in changed:
   self.assertEqual(c['odds_type'],'standard');self.assertEqual(c['target'],'TGT');self.assertEqual(c['grade_status'],'graded')
   self.assertEqual(float(c['actual']),0)
   for field in r.FIELDS:self.assertEqual(a.get(field),c.get(field),field)
 def test_incomplete_or_mismatched_proof_fails_even_if_repin_review_attempted(self):
  root=ROOT/'docs/nfl/data';s={x['game_id']:x for x in json.loads((root/'schedule_2026.json').read_text())['games']}
  for gid,pid in CASES:
   d=json.loads((root/'boxscores'/f'verified_gamebook_{gid}.json').read_text())
   for field,value in [('player_id','wrong'),('game_id','wrong'),('team_pass_attempts',1),('independent_receiver_ids',[pid]*d['verified_team_totals'][next(p['team'] for p in d['players'] if p['player_id']==pid)]['attempts'])]:
    bad=copy.deepcopy(d);p=next(p for p in bad['players'] if p['player_id']==pid);p['verified_zero_targets'][field]=value
    with patch.dict(b.REVIEWED_GAMES,{gid:{**b.REVIEWED_GAMES[gid],'sha':b.digest(bad)}}):
     with self.assertRaisesRegex(ValueError,'zero target'):b.validate(bad,s[gid])
if __name__=='__main__':unittest.main()
