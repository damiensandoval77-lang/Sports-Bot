"""Explicit allowlist of independently observed quote sources; never relabel receipts."""
THIRD_PARTY = "independent_prizepicksapi_com"
NATIVE = "native_prizepicks_public"
SOURCES = frozenset((THIRD_PARTY, NATIVE))
STATUSES = frozenset(("LIVE_THIRD_PARTY_PRIZEPICKS_LINES", "LIVE_NATIVE_PRIZEPICKS_LINES"))
def board_source(board):
    return NATIVE if board.get("status") == "LIVE_NATIVE_PRIZEPICKS_LINES" else THIRD_PARTY
