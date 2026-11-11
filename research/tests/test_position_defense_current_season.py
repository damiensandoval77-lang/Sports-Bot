import copy
import unittest
from datetime import datetime,timedelta,timezone
from research.position_defense_current_season import build

FREEZE="2026-11-11T20:00:00Z"
ROLES=("PG","SG","SF","PF","C","SG","SF","PF")

def logs(days=7,extra=0):
    result=[]
    def pair(day,a,b):
        for team,opp in ((a,b),(b,a)):
            for n,pos in enumerate(ROLES):
                pts=10+n
                result.append({"date":day,"id":team+str(n),"team":team,"opponent":opp,
                    "position":pos,"PTS":pts,"REB":4,"AST":2,"PRA":pts+6,"MIN":24})
    base=datetime(2026,10,20,tzinfo=timezone.utc)
    for i in range(days):pair((base+timedelta(days=i)).date().isoformat(),"BOS","NYK")
    for i in range(extra):pair((base+timedelta(days=days+i)).date().isoformat(),"LAL","CHI")
    return result

def form():
    return {"season":"2026-27","updated_at":"2026-11-11T18:00:00Z",
        "source_url":"https://github.com/example/source"}

def schedule():
    return {"generated_at":"2026-11-11T19:00:00Z",
        "source_url":"https://example.org/fixtures",
        "games":[{"id":"g1","start":"2026-11-12T00:00:00Z",
            "date_eastern":"2026-11-11",
            "away_abbreviation":"BOS","home_abbreviation":"NYK"}]}

class PositionalResearchTests(unittest.TestCase):
    def test_real_listed_position_is_distinct_from_defender_assignment(self):
        r=build(logs(7,10),form(),schedule(),captured_at=FREEZE)
        self.assertEqual(r["reciprocal_completed_games"],17)
        self.assertTrue(r["position_context_with_samples"]>0)
        self.assertFalse(r["actual_defender_assignments_available"])
        self.assertFalse(r["production_hit_estimate_eligible"])
        player=r["future_games"][0]["player_positional_context"][0]
        self.assertEqual(player["listed_position"],"PG")
        self.assertEqual(player["defense_games"],5)
        self.assertEqual(player["status"],"THIRD_PARTY_LISTED_POSITION_ALLOWANCE_RESEARCH")

    def test_early_low_league_sample_fails_closed(self):
        r=build(logs(7),form(),schedule(),captured_at=FREEZE)
        self.assertEqual(r["position_context_with_samples"],0)

    def test_missing_position_never_guessed(self):
        games=logs(7,10)
        for row in games:
            if row["id"]=="BOS0":row["position"]="G"
        r=build(games,form(),schedule(),captured_at=FREEZE)
        self.assertFalse(any(x["player_id"]=="BOS0" for x in r["future_games"][0]["player_positional_context"]))

    def test_inconsistent_role_rejected(self):
        games=logs(7,10)
        games[-(10*2*8+16)]["position"]="C"
        # Explicitly corrupt a final BOS game role for the player.
        for row in games:
            if row["id"]=="BOS0" and row["date"]=="2026-10-25":row["position"]="C"
        r=build(games,form(),schedule(),captured_at=FREEZE)
        self.assertFalse(any(x["player_id"]=="BOS0" for x in r["future_games"][0]["player_positional_context"]))

    def test_pretip_source_timestamp_required(self):
        f=form();f["updated_at"]="2026-11-11T21:00:00Z"
        with self.assertRaises(ValueError):build(logs(),f,schedule(),captured_at=FREEZE)

    def test_pregame_schedule_timestamp_required(self):
        s=schedule();s["generated_at"]="2026-11-11T21:00:00Z"
        with self.assertRaises(ValueError):build(logs(),form(),s,captured_at=FREEZE)

    def test_started_game_not_backfilled(self):
        s=schedule();s["games"][0]["start"]="2026-11-11T19:00:00Z"
        self.assertEqual(build(logs(),form(),s,captured_at=FREEZE)["future_game_count"],0)

    def test_same_day_games_not_used_for_future_defense_at_same_date(self):
        games=logs(7,10)
        baseline=build(games,form(),schedule(),captured_at=FREEZE)
        additions=logs(1)
        for x in additions:
            x["date"]="2026-11-11"
        games+=additions
        changed=build(games,form(),schedule(),captured_at=FREEZE)
        self.assertEqual(changed["reciprocal_completed_games"],baseline["reciprocal_completed_games"]+1)
        base_players=baseline["future_games"][0]["player_positional_context"]
        new_players=changed["future_games"][0]["player_positional_context"]
        a={x["player_id"]:x.get("defense_last5_per_listed_player") for x in base_players}
        b={x["player_id"]:x.get("defense_last5_per_listed_player") for x in new_players}
        self.assertEqual(a,b)

    def test_duplicate_player_row_not_double_counted(self):
        games=logs(7,10);games.append(copy.deepcopy(games[0]))
        r=build(games,form(),schedule(),captured_at=FREEZE)
        self.assertGreater(r["rejections"].get("duplicate_observation",0),0)

    def test_bad_pra_row_does_not_create_fake_stat(self):
        games=logs(7,10);games[0]["PRA"]=99
        r=build(games,form(),schedule(),captured_at=FREEZE)
        self.assertGreater(r["rejections"].get("invalid_pra",0),0)

    def test_no_current_season_data_rejected(self):
        f=form();f["season"]="2025-26"
        with self.assertRaises(ValueError):build(logs(),f,schedule(),captured_at=FREEZE)

if __name__=="__main__":unittest.main()
