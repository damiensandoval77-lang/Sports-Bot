# Sports-Bot next source integration decision — 2026-11-08

## Goal

Prospectively forecast actual player assists from *potential assists* and actual rebounds from *rebound chances*, each with prior independently dated game IDs and pretip snapshots. These are NOT equivalent to historical box-score AST/REB or play-by-play shot attempts. The code and protected CSV importer are already implemented and validated; unprovided source data cannot be fabricated.

## Provider checks

| Source | What the docs verify | Missing for our automatic game-level data collection |
|---|---|---|
| SportQuanta | NBA player tracking documents `passing.potential_assists` and `rebounding.rebound_chances`; token and paid stats entitlement; per-season/per-game *average* summaries. https://docs.sportquanta.com/api-reference/endpoints/basketball/nba/list-nba-player-tracking/ | No active token/entitlement in repo, and no independently confirmed one-game-per-row logs with played game ID/date. Do not expand aggregate counts into fake observations. |
| Synergy/Sportradar | Synergy tracks player movement and offers UI filters by date range, last N games and individual games. https://support.synergysports.com/support/solutions/articles/77000565951-player-tracking-data ; Synergy basketball API offers possession-level event feeds, https://developer.sportradar.com/sportradar-updates/changelog/synergy-basketball-api-release | Appropriate subscription, specific AST potential assists and REB chances per player-game fields, API/export permission for prop model not confirmed. |
| DunkAPI | Historical props, play-by-play and box scores; https://dunkapi.com/ | No documented optical potential assists/rebound chances; do not relabel box-score or PBP estimates as tracking observations. |
| NBA.com tracking | Field definitions and statistics are publicly visible. | NBA.com restrictions prohibit using NBA Statistics in connection with gambling absent license. Public endpoints do not provide authorization. |

**Decision:** Do not incur a paid subscription or claim integration automatically. If a user has a tracking-provider account, validate game-level field availability and explicit permitted use before writing a data-source adapter. The provider-agnostic normalizer `iphone_bot/import_tracking_export.py` accepts an authorized CSV with `player_id,team,game_id,game_date,observed_at,minutes,potential_assists,assists,rebound_chances,rebounds`. The importer stores only in ignored `data/nba/private`. Running a GitHub Actions workflow cannot access that private local file without secure feed deployment.

## Immediate verified operational blocker

As of the last published live-odds run on November 7 UTC:
- `docs/odds_fetch_status.json` shows 12 events available, **0** requested for props, **11** credits remaining, and **0** outcome rows.
- `docs/odds_slate_health.json` says the 12-credit reserve blocked six upcoming NBA games in its previous slate snapshot.
- `docs/data.json` contains **0** picks; `docs/ai_comparisons.json` contains **0** comparisons. This is a stale snapshot, not a claim there are zero NBA games or opportunities right now.
- Repairing current line coverage is separate from optical tracking access; no claim that additional tracking alone restores the live board.

## Explicit next requirements

1. A provider with independently verified per-player-per-game potential assists and rebound chances, not a per-game average season summary.
2. Legitimate access credentials/contract permitting use in betting analytics. Do not commit tokens.
3. A small real game-level sample verified for player/game IDs, historical cutoff, minutes, and historical conversion, imported only privately.
4. Frozen pregame paired grading over independent later game dates before live promotion.

**Status:** Source identification and existing integration readiness checked. No game-level tracking provider connected. No extra API calls or credit purchases made.
