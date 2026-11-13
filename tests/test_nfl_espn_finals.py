import copy,json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import export_nfl_espn_finals as e
import reconcile_nfl_picks as r
class FinalTests(unittest.TestCase):
    def setUp(self):
        self.g=dict(game_id='2026_10_WAS_NYG',week=10,home='NYG',away='WAS',home_score=21,away_score=24,kickoff_utc='2026-11-13T01:15:00+00:00',status='final')
        c=dict(id='123',date=self.g['kickoff_utc'],boxscoreAvailable=True,status={'type':{'completed':True,'state':'post'}},competitors=[{'homeAway':a,'team':{'abbreviation':b},'score':s} for a,b,s in [('home','NYG',21),('away','WSH',24)]])
        self.p={'header':{'id':'123','season':{'year':2026,'type':2},'week':10,'competitions':[c]},'boxscore':{'players':[{'team':{'abbreviation':team},'statistics':[{'name':'passing','labels':['C/ATT','YDS','TD','INT'],'athletes':[{'athlete':{'id':aid,'displayName':name},'stats':['20/30','250','2','0']}]}]} for team,aid,name in [('NYG','1','One Player'),('WSH','2','Two Player')]]}}
        self.ids=e.identities('espn_id,gsis_id,display_name\n1,00-0001,One Player\n2,00-0002,Two Player\n')
    def build(self):return e.build_game(self.p,self.g,self.ids,'2026-11-13T05:00:00+00:00')
    def test_explicit_zero_not_missing_zero(self):
        game=self.build();e.validate_stored(game,self.g);p=game['players'][0]
        self.assertEqual(r.actual_for('PASS_INT',p),0);self.assertEqual(r.actual_for('PASS_YDS',p),250)
        self.assertIsNone(r.actual_for('REC_YDS',p));self.assertIsNone(r.actual_for('PASS_RUSH_YDS',p));self.assertIsNone(r.actual_for('FPTS',p))
    def test_rejects_nonfinal_and_identity_mismatches(self):
        for path,value in [('completed',False),('state','in')]:
            original=copy.deepcopy(self.p);self.p['header']['competitions'][0]['status']['type'][path]=value
            with self.assertRaises(ValueError):self.build()
            self.p=original
        for key,value in [('week',9),('id','456')]:
            original=copy.deepcopy(self.p);self.p['header'][key]=value
            with self.assertRaises(ValueError):self.build()
            self.p=original
        for key,value in [('date','2026-11-12T01:15Z'),('boxscoreAvailable',False)]:
            original=copy.deepcopy(self.p);self.p['header']['competitions'][0][key]=value
            with self.assertRaises(ValueError):self.build()
            self.p=original
        self.p['header']['competitions'][0]['competitors'][0]['score']=22
        with self.assertRaises(ValueError):self.build()
    def test_duplicate_and_wrong_names_fail_closed(self):
        self.p['boxscore']['players'][0]['statistics'][0]['athletes']*=2
        with self.assertRaises(ValueError):self.build()
        self.setUp();self.ids['1']['display_name']='Someone Else'
        with self.assertRaises(ValueError):self.build()
        with self.assertRaises(ValueError):e.identities('espn_id,gsis_id\n1,00-1\n1,00-2\n')
    def test_integrity_and_grader(self):
        game=self.build()
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'manifest.json').write_text('{"season":2026}')
            (p/'espn_verified_finals.json').write_text(json.dumps({'season':2026,'games':[game]}))
            boxes,bad=r.verified_boxscores({self.g['game_id']:self.g},p)
            self.assertFalse(bad);self.assertEqual(len(boxes[self.g['game_id']]),2)
            game['players'][0]['passing_yards']=999
            (p/'espn_verified_finals.json').write_text(json.dumps({'season':2026,'games':[game]}))
            boxes,bad=r.verified_boxscores({self.g['game_id']:self.g},p)
            self.assertFalse(boxes);self.assertIn(self.g['game_id'],bad)
if __name__=='__main__':unittest.main()
