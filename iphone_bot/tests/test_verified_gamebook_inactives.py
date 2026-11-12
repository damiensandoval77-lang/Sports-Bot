import unittest

from iphone_bot.verified_gamebook_inactives import load_gamebook_inactives


class OfficialGamebookTests(unittest.TestCase):
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
