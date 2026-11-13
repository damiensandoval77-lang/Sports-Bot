import unittest
import datetime as dt
import json
from pathlib import Path

from iphone_bot.verified_gamebook_inactives import load_gamebook_inactives


class OfficialGamebookTests(unittest.TestCase):
    def test_nov11_final_evidence_resolves_missing_players_without_regrading(self):
        from iphone_bot.grade_frozen_ai_forecasts import eligible_predictions, settle_predictions, key
        root = Path(__file__).resolve().parents[2] / 'docs'
        actuals = json.loads((root / 'verified_final_player_cache.json').read_text())['rows']
        archive = json.loads((root / 'ai_no_line_pregame_archive.json').read_text())['predictions']
        old = json.loads((root / 'ai_forecast_actual_ledger.json').read_text())['records']
        evidence = load_gamebook_inactives(actuals)
        recovered = [r for r in evidence if r['date'] == '2026-11-11']
        self.assertEqual(len(recovered), 24)
        self.assertTrue(all(r['dnp_final_verified'] and r.get('PTS') is None for r in recovered))
        result = settle_predictions(eligible_predictions(archive, dt.datetime(2026, 11, 12, 12, tzinfo=dt.timezone.utc)),
                                    actuals, old, confirmed_inactives=evidence)
        after = {key(r): r for r in result['records']}
        for row in old:
            self.assertEqual(after[key(row)], row)
        # Exclusions retain their source in final_source; check exact archived identities.
        names = {(r['player'], r['team']) for r in recovered}
        resolved = [r for r in result['records'] if r.get('status') == 'EXCLUDED_VERIFIED_DNP'
                    and (r['player'], r['team']) in names and r['start'].startswith('2026-11-12')]
        self.assertEqual(len(resolved), 96)

    def test_nov12_reviewed_final_gamebooks_preserve_null_actuals(self):
        root = Path(__file__).resolve().parents[2] / 'docs'
        actuals = json.loads((root / 'verified_final_player_cache.json').read_text())['rows']
        evidence = [r for r in load_gamebook_inactives(actuals) if r['date'] == '2026-11-12']
        self.assertEqual({(r['player'], r['team']) for r in evidence}, {
            ('Scottie Barnes', 'TOR'), ('Trayce Jackson-Davis', 'TOR'),
            ('Adem Bona', 'PHI'), ('LeBron James', 'PHI'), ('Ebuka Okorie', 'DET')})
        self.assertTrue(all(r['dnp_final_verified'] and r.get('PTS') is None for r in evidence))
        self.assertTrue(all(r['source'] == 'NBA_OFFICIAL_INACTIVE_CROSSCHECKED' for r in evidence))

    def test_requires_exact_final_and_rejects_played_player(self):
        rows = [
            dict(player=f"Player {team} {i}", team=team, opponent=opponent,
                 date="2026-11-10", source_game_id="0022600211",
                 source="NBA_CDN_FINAL", final_confirmed=True)
            for team, opponent in (("MIL", "NYK"), ("NYK", "MIL"))
            for i in range(3)
        ]
        self.assertEqual(load_gamebook_inactives(rows[:3]), [])
        evidence = load_gamebook_inactives(rows)
        self.assertEqual({r["player"] for r in evidence}, {"Josh Hart", "Tyler Herro"})
        self.assertTrue(all(r["dnp_final_verified"] and r.get("PTS") is None for r in evidence))
        contradicted = rows + [{**rows[-1], "player": "Josh Hart", "source": "ESPN_FINAL"}]
        self.assertEqual([r["player"] for r in load_gamebook_inactives(contradicted)], ["Tyler Herro"])
