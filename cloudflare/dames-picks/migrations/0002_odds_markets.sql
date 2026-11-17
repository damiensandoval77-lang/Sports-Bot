-- Stage 2: credit-budgeted market data; no source polling is activated by this migration.
-- Odds markets are never observed player performance statistics or frozen AI forecasts.
CREATE TABLE IF NOT EXISTS odds_api_budget (
 month_utc TEXT PRIMARY KEY NOT NULL,
 day_utc TEXT NOT NULL,
 used_credits INTEGER NOT NULL DEFAULT 0 CHECK (used_credits >= 0),
 reserved_credits INTEGER NOT NULL DEFAULT 0 CHECK (reserved_credits >= 0),
 daily_used INTEGER NOT NULL DEFAULT 0 CHECK (daily_used >= 0),
 daily_reserved INTEGER NOT NULL DEFAULT 0 CHECK (daily_reserved >= 0),
 provider_remaining INTEGER,
 updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS odds_api_quotes (
 quote_key TEXT PRIMARY KEY NOT NULL,
 league TEXT NOT NULL CHECK(league IN ('NBA','NFL')),
 event_id TEXT NOT NULL,
 event_start TEXT NOT NULL,
 home_team TEXT NOT NULL,
 away_team TEXT NOT NULL,
 bookmaker TEXT NOT NULL,
 market_key TEXT NOT NULL,
 player TEXT NOT NULL,
 player_key TEXT NOT NULL,
 player_id TEXT,
 player_team TEXT,
 identity_verified INTEGER NOT NULL DEFAULT 0 CHECK(identity_verified IN (0,1)),
 standard_line REAL NOT NULL CHECK(standard_line >= 0),
 over_price INTEGER,
 under_price INTEGER,
 price_type TEXT NOT NULL CHECK(price_type IN ('indicative_dfs','sportsbook_american')),
 market_observed_at TEXT NOT NULL,
 captured_at TEXT NOT NULL,
 source TEXT NOT NULL DEFAULT 'the_odds_api',
 is_alternate INTEGER NOT NULL DEFAULT 0 CHECK(is_alternate=0),
 CHECK(identity_verified=0 OR (player_id IS NOT NULL AND player_team IS NOT NULL))
);
CREATE INDEX IF NOT EXISTS odds_quote_live
 ON odds_api_quotes(league,event_start,market_observed_at DESC,bookmaker);
CREATE INDEX IF NOT EXISTS odds_quote_player_history
 ON odds_api_quotes(league,player_key,market_key,event_start,market_observed_at DESC);
CREATE TABLE IF NOT EXISTS odds_api_attempts (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 month_utc TEXT NOT NULL,
 league TEXT NOT NULL CHECK(league IN ('NBA','NFL')),
 event_id TEXT NOT NULL,
 requested_markets TEXT NOT NULL,
 bookmaker_group TEXT NOT NULL,
 requested_at TEXT NOT NULL,
 resolved_at TEXT NOT NULL,
 maximum_reserved INTEGER NOT NULL,
 charged_credits INTEGER NOT NULL,
 outcome TEXT NOT NULL CHECK(outcome IN ('ok','empty','error','partial','unknown_cost')),
 quotes_stored INTEGER NOT NULL DEFAULT 0,
 provider_remaining INTEGER,
 note TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS odds_attempts_event_time
 ON odds_api_attempts(league,event_id,requested_at DESC);
