import copy
import unittest
from iphone_bot.fetch_final_boxscores import gather, final_espn_scoreboard_hints, ESPN_SCORE, ESPN_BOX, NBA_SCOREBOARD, NBA_BOX
from iphone_bot.tests.test_direct_espn_final_recovery import IDENT, EVENT_ID, WHEN, NOW, summary, pending


def board():
    s=summary()
    return {'events':[{'id':EVENT_ID,'date':WHEN,'status':{'type':{'completed':True}},'competitions':s['header']['competitions']}]}

class SecondaryDiscovery(unittest.TestCase):
    def test_hint_rejects_wrong_date_incomplete_and_conflicting_ids(self):
        self.assertEqual(final_espn_scoreboard_hints(board(),IDENT[0]),{IDENT:EVENT_ID})
        b=board(); b['events'][0]['date']='2026-11-11T00:00:00Z'
        self.assertEqual(final_espn_scoreboard_hints(b,IDENT[0]),{})
        b=board(); b['events'][0]['status']['type']['completed']=False
        self.assertEqual(final_espn_scoreboard_hints(b,IDENT[0]),{})
        b=board();other=copy.deepcopy(b['events'][0]);other['id']='401999999';b['events'].append(other)
        self.assertEqual(final_espn_scoreboard_hints(b,IDENT[0]),{})

    def run_recovery(self, summary_change=None, board_change=None):
        event={'gameId':'0022600204','gameStatus':3,'gameTimeUTC':WHEN,
               'awayTeam':{'teamTricode':'CLE'},'homeTeam':{'teamTricode':'CHA'}}
        game=copy.deepcopy(event)
        for side,name in [('awayTeam','Sample Player'),('homeTeam','Home Player')]:
            game[side]['players']=[{'name':name,'statistics':{'points':26,'reboundsTotal':5,'assists':4,'minutes':'31:00'}}]
        called=[]
        def request(url):
            called.append(url)
            if url==NBA_SCOREBOARD:return {'scoreboard':{'games':[event]}}
            if url==NBA_BOX.format('0022600204'):return {'game':game}
            if url.startswith(ESPN_SCORE):
                b=board()
                if board_change:board_change(b)
                return b
            if url.startswith(ESPN_BOX):
                s=summary();s['boxscore']['players'][0]['statistics'][0]['athletes'].append({'athlete':{'displayName':'Missing Guard'},'didNotPlay':True,'reason':"Coach's Decision",'stats':[]})
                if summary_change:summary_change(s)
                return s
            raise AssertionError(url)
        rows,health=gather(pending(),now=NOW,request=request,known_espn_games={},supplemental_espn_dnp_names={IDENT:{('missingguard','CLE')}})
        return [r for r in rows if r.get('dnp_final_verified')],health,called

    def test_discovers_final_after_schedule_rollover_without_hint(self):
        rows,h,c=self.run_recovery()
        self.assertEqual([r['player'] for r in rows],['Missing Guard'])
        self.assertEqual(h['secondary_espn_dnp_discovered_game_hints'],1)
        self.assertEqual(sum(u.startswith(ESPN_SCORE) for u in c),1)
        self.assertEqual(rows[0]['source_game_id'],EVENT_ID)

    def test_summary_must_independently_match(self):
        for change in [lambda s:s['header'].update(id='999'),lambda s:s['header']['competitions'][0].update(date='2026-11-11T00:00:00Z'),lambda s:s['header']['competitions'][0]['status']['type'].update(completed=False),lambda s:s['header']['competitions'][0]['competitors'][0]['team'].update(abbreviation='BOS')]:
            with self.subTest(change=change):self.assertEqual(self.run_recovery(summary_change=change)[0],[])

    def test_positive_stats_cannot_be_voided_even_with_zero_minutes(self):
        def contradictory(s):s['boxscore']['players'][0]['statistics'][0]['athletes'][-1]['stats']=['0:00','0','0','2']
        self.assertEqual(self.run_recovery(summary_change=contradictory)[0],[])

    def test_no_reason_cannot_be_voided(self):
        def remove(s):s['boxscore']['players'][0]['statistics'][0]['athletes'][-1].pop('reason')
        self.assertEqual(self.run_recovery(summary_change=remove)[0],[])

if __name__=='__main__':unittest.main()
