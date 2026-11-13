"""Fail-closed mobile rendering expectation, independent of near-tip alerts."""
def board_rendered(cards, expected_upcoming_picks):
    return cards > 0 or expected_upcoming_picks == 0
