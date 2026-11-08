"""Schema-only provider diagnostic must not publish player stats."""
import unittest
from iphone_bot.probe_pbpstats_access import response_schema,MAX_RESPONSE_BYTES

class ProbeSchemaTests(unittest.TestCase):
    def test_reveals_only_keys_and_structure_not_values(self):
        sample={"multi_row_table_data":[{"PlayerId":"SECRET_PLAYER_ID","Minutes":123,
                  "Pts":999}],"single_row_table_data":{"rows":[{"Possessions":12}]},
                  "request":"SECRET_VALUE"}
        out=response_schema(sample)
        self.assertEqual(out["response_shape"],"OBJECT")
        self.assertEqual(out["multi_row_table_data_row_keys"],["Minutes","PlayerId","Pts"])
        self.assertEqual(out["single_row_table_data_nested_row_keys"],["Possessions"])
        self.assertNotIn("SECRET_PLAYER_ID",str(out))
        self.assertNotIn("SECRET_VALUE",str(out))
    def test_handles_rows_as_arrays_and_empty_responses(self):
        out=response_schema({"multi_row_table_data":[["A","B"],[1,2]]})
        self.assertEqual(out["multi_row_table_data_row_width"],2)
        self.assertEqual(response_schema({})["response_shape"],"OBJECT")
        self.assertEqual(response_schema([])["response_shape"],"ARRAY")
        self.assertLessEqual(MAX_RESPONSE_BYTES,8*1024*1024)

if __name__=="__main__":unittest.main()
