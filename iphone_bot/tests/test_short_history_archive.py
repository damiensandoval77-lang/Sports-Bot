import unittest
from copy import deepcopy
from datetime import datetime, timezone
from iphone_bot.short_history_archive import archive, MODEL
NOW=datetime(2026,11,13,12,tzinfo=timezone.utc)
def feed():
    return {'status':'SHORT_HISTORY_TRAINED_RESEARCH_PROJECTIONS','model':MODEL,
      'generated_at':'2026-11-13T11:55:00Z','model_artifact_sha256':'a'*64,
      'estimates':[{'model':MODEL,'player_id':'1','player':'Player','team':'BOS','opponent':'NYK',
       'game':'BOS @ NYK','start':'2026-11-14T00:00:00Z','stat':'PTS','line':12.5,'projection':11.,
       'captured_at':'2026-11-13T11:55:00Z','market_updated':'2026-11-13T11:50:00Z',
       'research_only':True,'trained_model':True,'primary_model_eligible':False,'official_grade_eligible':False,
       'pickem_tier':'standard','standard_line_two_sided_verified':True,
       'source':'INDEPENDENTLY_CROSSCHECKED_PLAYER_HISTORY','prior_games':3,
       'history_dates':['2026-11-01','2026-11-03','2026-11-05']} ]}
class ArchiveTests(unittest.TestCase):
    def test_first_receipt_immutable(self):
        f=feed();a=archive(None,f,NOW);old=deepcopy(a['records']);f['estimates'][0]['projection']=99
        f['model_artifact_sha256']='b'*64
        b=archive(a,f,NOW);self.assertEqual(b['records'],old);self.assertEqual(b['count'],1)
    def test_threshold_versions_distinct(self):
        f=feed();a=archive(None,f,NOW);f['estimates'][0]['line']=13.5
        self.assertEqual(archive(a,f,NOW)['count'],2)
    def test_posttip_or_old_observation_never_backfilled(self):
        for now in (datetime(2026,11,14,tzinfo=timezone.utc),datetime(2026,11,13,13,tzinfo=timezone.utc)):
            self.assertEqual(archive(None,feed(),now)['count'],0)
    def test_invalid_and_ineligible_fail_closed(self):
        for k,v in [('stat','AST'),('primary_model_eligible',True),('official_grade_eligible',True),
                    ('research_only',False),('hit_probability',.8),('line',float('nan')),
                    ('standard_line_two_sided_verified',False),('history_dates',['2026-11-13']*3)]:
            f=feed();f['estimates'][0][k]=v;self.assertEqual(archive(None,f,NOW)['count'],0,(k,v))
    def test_blocked_feed_preserves_old(self):
        f=feed();a=archive(None,f,NOW);f['blocker']='STALE';f['estimates']=[]
        self.assertEqual(archive(a,f,NOW)['records'],a['records'])
    def test_bad_archive_cannot_be_reset(self):
        with self.assertRaises(ValueError):archive({'records':[]},feed(),NOW)
    def test_future_receipt_rejected(self):
        f=feed();f['estimates'][0]['captured_at']='2026-11-13T12:01:00Z'
        self.assertEqual(archive(None,f,NOW)['count'],0)
if __name__=='__main__':unittest.main()
