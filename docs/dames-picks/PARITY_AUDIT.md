# Dame's Picks Version E — integration parity and reliability audit

Status: **partial, not full parity**. This file is a gap register, not a declaration of production readiness.

## Preservation
The legacy NBA dashboard (`docs/index.html`), NFL dashboard (`docs/nfl/index.html`), source data collectors, modeling workflows, archived quotes, forecasts, and settlement scripts are untouched by the Version E frontend. The player detail page links to each legacy dashboard while migration continues.

## Proven integration
| Domain | Source | Version E status |
| --- | --- | --- |
| NBA standard pretip lines, frozen projections and modeled direction | `lagged_matchup_all_market_ledger.json` | Integrated, no post-tip repricing |
| NBA recorded season, last five, last ten form | `current_form.json` | Integrated, where available |
| NBA official injury status, dated | `injury_context.json` | Integrated exact player/team/game-date label only; frozen models unchanged |
| NFL depth-chart, recent snap share, line-specific season Over/Under | NFL latest CSV fields | Integrated, where source values exist |
| NBA verified individual model grades | Same frozen market ledger | Integrated; pending is not a loss |
| NFL standard pretip props and projections | `nfl/data/latest_2026.json` CSV manifest | Integrated; does not display goblin/demon as standard |
| NFL season averages and recent per-game history | NFL latest CSV rows | Integrated when recorded |
| NFL individual final grade | `nfl/data/pp_graded_2026.csv` | Exact saved-quote join supported; currently no graded rows published |
| NBA observed player stats | `live_player_tracking.json` | Integrated when snapshot is fresh, game in progress, and player/game/team match unambiguously |
| NFL observed player stats | `nfl/data/live_2026.json` | Integrated when fresh and exact model target exists |
| NFL league-wide grading totals | `nfl/data/grading_health_2026.json` | Integrated; zero settled rows explicitly disclosed |
| NBA missing standard-market coverage | `tonight_capture_gradeability.json` | Visible diagnostic |
| NBA AI-only forecast grading backlog | `ai_forecast_today_grade_status.json` | Visible diagnostic; distinct from line-backed grades |
| Saved favorites | Local browser storage | Retained on same browser only; **not** cloud-synced |
| Full legacy research features | Original NBA/NFL pages | Accessible through original research links; **not yet embedded in Version E** |

## Still not feature-parity complete
- Full NBA individual last-six-game chart and opponent positional-defense rank are not published in a verified Version E feed; do not invent these values.
- Injury transitions and automatic injury-aware reprojections, on/off teammate splits, minutes v2/v3, pace projection, advanced shooting statistics, and deeper depth-chart model evidence still live on the original research surfaces; static injury labels and core NFL depth fields are now integrated.
- Full NFL grading is blocked upstream: the grading health file reports zero settled standard picks even though pregame lines exist; dashboard cannot invent final grades.
- NFL full-slate standard-quote coverage and NBA missing-prediction markets require upstream repairs, not only UI work.
- NBA/NFL live observations are periodic and may be stale. Version E suppresses stale snapshots rather than calling them live.
- A single cross-sport database, permanent server-side user bookmarks, push alerts, native app packaging, and full original feature parity are not implemented.
- Frontend checks and CI cannot establish all future provider availability or end-to-end automatic nightly grading.

## Release criteria before claiming full parity
1. All meaningful legacy NBA/NFL features have a verified Version E equivalent with exact sources, or explicitly remain as accessible legacy modules.
2. Every captured eligible pregame prop has stable identity (sport, game, player, stat, line, capture timestamp) and a clear graded/pending/void status.
3. Completed games cause source-verified final settlement without manual action; no unaccounted pending rows and no silent line gaps.
4. Every nightly pipeline publishes source timestamp, completeness/coverage and failure reason; the UI clearly marks stale/partial states.
5. iPhone-width Chromium smoke checks both league boards, player details, and actual source-backed data; model and live tests pass independently.
6. No unverified percentages, fantasy grade labels, opponent ranks or fabricated historical bars.

The current release can pass tests and still fail one of these criteria; do not label it 100% reliable or ready for a native-app migration.
