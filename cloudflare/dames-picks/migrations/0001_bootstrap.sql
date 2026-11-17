-- Phase 1: independent Cloudflare D1 status/heartbeat. No sports-provider calls yet.
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS source_health (
  source_id TEXT PRIMARY KEY NOT NULL,
  league TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('not_connected','ok','partial','stale','error','unavailable')),
  last_observed_at TEXT,
  last_success_at TEXT,
  last_attempt_at TEXT,
  max_age_minutes INTEGER NOT NULL CHECK (max_age_minutes > 0),
  records INTEGER NOT NULL DEFAULT 0 CHECK (records >= 0),
  note TEXT NOT NULL DEFAULT '',
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS scheduler_runs (
  run_id INTEGER PRIMARY KEY AUTOINCREMENT,
  job TEXT NOT NULL,
  scheduled_at TEXT NOT NULL,
  completed_at TEXT NOT NULL,
  outcome TEXT NOT NULL CHECK(outcome IN ('success','skipped','failure')),
  detail TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS scheduler_runs_job_time ON scheduler_runs(job, scheduled_at DESC);
INSERT OR IGNORE INTO source_health(source_id,league,status,max_age_minutes,note) VALUES
('nba_scores','NBA','not_connected',10,'Worker-owned live collection not connected'),
('nba_player_stats','NBA','not_connected',180,'Worker-owned player statistics not connected'),
('nfl_scores','NFL','not_connected',10,'Worker-owned live collection not connected'),
('nfl_player_stats','NFL','not_connected',180,'Worker-owned player statistics not connected'),
('prizepicks_standard_lines','MULTI','not_connected',10,'New line provider not connected; paid polling disabled'),
('frozen_ai_projections','MULTI','not_connected',1440,'Model compute and immutable forecast export not connected'),
('postgame_grades','MULTI','not_connected',1440,'Final-grade reconciliation not connected');
