import unittest
from iphone_bot.quote_capture_coverage import verify,coverage
from iphone_bot.paper_pick_pipeline import snapshot
AT="2026-11-07T20:00:00Z"
START="2026-11-08T01:00:00Z"
def row():
    return {"player":"Nikola Jokic","player_id":"203999","team":"DEN",
        "game":"Denver Nuggets @ Indiana Pacers","stat":"PTS",
        "start":START,"projection":30.,"combined_projection":32.,
        "book_quotes":[{"name":"FanDuel","line":30.5,"over":-110,"under":-110}]}

class QuoteCoverageTests(unittest.TestCase):
    def test_real_pretip_offer_capture_verified(self):
        b=row()
        frozen=snapshot([b],AT)
        r=verify([b],frozen,AT)
        self.assertEqual(r["eligibility_by_reason"]["ELIGIBLE_AND_FROZEN"],1)
        self.assertEqual(r["eligible_quote_missing_from_ledger"],0)
    def test_fails_if_valid_offer_was_not_saved(self):
        with self.assertRaisesRegex(AssertionError,"missing"):
            verify([row()],[],AT)
    def test_model_exact_at_line_not_a_paper_side(self):
        b=row();b["combined_projection"]=30.5
        r=coverage([b],[],AT)
        self.assertEqual(r["eligibility_by_reason"]["MODEL_AT_EXACT_LINE_NO_SIDE"],1)
        self.assertEqual(r["eligible_quote_missing_from_ledger"],0)
    def test_late_offer_not_recreated_as_pregame(self):
        b=row()
        r=verify([b],[],"2026-11-08T01:30:00Z")
        self.assertEqual(r["eligibility_by_reason"]["GAME_ALREADY_STARTED"],1)
    def test_invalid_bookmaker_price_explicitly_excluded(self):
        b=row()
        b["book_quotes"][0]["over"]=None
        r=verify([b],[],AT)
        self.assertEqual(r["eligibility_by_reason"]["INVALID_SIDE_ODDS_OR_REQUIRED_IDENTITY"],1)
    def test_multiple_books_require_exact_independent_ledger_records(self):
        b=row()
        b["book_quotes"].append({"name":"DraftKings","line":29.5,"over":-115,"under":-105})
        frozen=snapshot([b],AT)
        self.assertEqual(verify([b],frozen,AT)["eligibility_by_reason"]["ELIGIBLE_AND_FROZEN"],2)
        partial=verify([b],frozen,AT)
        self.assertEqual(partial["eligible_quote_missing_from_ledger"],0)
        with self.assertRaises(AssertionError):verify([b],frozen[:1],AT)
    def test_duplicate_quote_preserved_without_extra_pick(self):
        b=row()
        b["book_quotes"].append(dict(b["book_quotes"][0]))
        frozen=snapshot([b],AT)
        r=verify([b],frozen,AT)
        self.assertEqual(r["eligibility_by_reason"]["DUPLICATE_SAME_QUOTE"],1)
        self.assertEqual(r["eligibility_by_reason"]["ELIGIBLE_AND_FROZEN"],1)

if __name__=="__main__":unittest.main()
