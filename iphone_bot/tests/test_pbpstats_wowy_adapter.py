"""Provider response structure validated without network or licensed data."""
import unittest
from iphone_bot.pbpstats_wowy_adapter import normalize_pair
from iphone_bot.pbpstats_request_plan import request_plan

def record(points=80):
    return {"multi_row_table_data":[
        {"EntityId":"100","Points":points,"Rebounds":20,"Assists":16,
         "SecondsPlayed":10800,"Minutes":180},
        {"EntityId":"102","Points":99,"Rebounds":18,"Assists":9,
         "SecondsPlayed":10000}
    ]}
def proof(kind="with"):
    return {"verified_completed_games":True,
            "request_params":request_plan("100","900","BOS",cutoff_date="2026-11-06")["requests"][kind],
            "game_dates":[f"2026-10-{d:02d}" for d in range(2,8)]}
def normalized(on=None,off=None,**kw):
    args=dict(player_id="100",teammate_id="900",team="BOS",season="2026-27",
        provider_generated_at="2026-11-07T18:00:00Z",
        observed_through_at="2026-11-07T17:00:00Z",data_through="2026-11-06",
        with_provenance=proof("with"),without_provenance=proof("without"))
    args.update(kw)
    return normalize_pair(on if on is not None else record(),
                          off if off is not None else record(100),**args)

class ProviderMapperTests(unittest.TestCase):
    def test_real_field_names_and_exact_entity_id_mapping(self):
        r=normalized()
        self.assertEqual(r["with"]["games"],6)
        self.assertEqual(r["with"]["minutes"],180)
        self.assertEqual(r["with"]["PTS_per36"],16)
        self.assertEqual(r["without"]["PTS_per36"],20)
        self.assertEqual(r["with"]["REB_per36"],4)
        self.assertEqual(r["with"]["AST_per36"],3.2)
    def test_never_accept_undated_or_wrong_onoff_query_provenance(self):
        bad=proof("with")
        bad["request_params"].pop("ToDate")
        with self.assertRaisesRegex(ValueError,"request provenance"):
            normalized(with_provenance=bad)
        with self.assertRaisesRegex(ValueError,"request provenance"):
            normalized(without_provenance=proof("with"))

    def test_insufficient_provenance_and_date_leakage(self):
        bad=proof()
        bad["game_dates"]=["2026-10-02"]
        with self.assertRaisesRegex(ValueError,"game dates"):
            normalized(with_provenance=bad)
        bad=proof()
        bad["game_dates"]=["2026-10-02"]*6
        with self.assertRaisesRegex(ValueError,"Duplicate"):
            normalized(with_provenance=bad)
        bad=proof()
        bad["game_dates"]=["2026-10-02","2026-10-03","2026-10-04",
                           "2026-10-05","2026-10-06","2026-11-07"]
        with self.assertRaisesRegex(ValueError,"Future"):
            normalized(with_provenance=bad)
        bad=proof()
        bad["verified_completed_games"]=False
        with self.assertRaisesRegex(ValueError,"provenance"):
            normalized(with_provenance=bad)
    def test_wrong_player_duplicates_and_missing_minutes(self):
        with self.assertRaisesRegex(ValueError,"EntityId"):
            normalized(on={"multi_row_table_data":[{"EntityId":"999","Minutes":180}]})
        d=record();d["multi_row_table_data"].append(dict(d["multi_row_table_data"][0]))
        with self.assertRaisesRegex(ValueError,"EntityId"):
            normalized(on=d)
        d=record();d["multi_row_table_data"][0].pop("Minutes")
        d["multi_row_table_data"][0].pop("SecondsPlayed")
        with self.assertRaisesRegex(ValueError,"minutes"):
            normalized(on=d)
    def test_bad_timestamp_and_inconsistent_units(self):
        with self.assertRaisesRegex(ValueError,"postdate"):
            normalized(observed_through_at="2026-11-08T01:00:00Z")
        d=record();d["multi_row_table_data"][0]["Minutes"]=150
        with self.assertRaisesRegex(ValueError,"Inconsistent"):
            normalized(on=d)

if __name__=="__main__":unittest.main()
