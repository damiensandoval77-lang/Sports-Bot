# PBP Stats 2026–27: real, bounded ON/OFF source audit
Captured by GitHub Actions 2026-11-08 UTC. These are real source-consistency diagnostics, not actual pregame prop predictions or evidence of a profitable edge.

## Findings through November 6, 2026

| Player | Teammate | ON games | ON court minutes | OFF games | OFF court minutes | Provider minutes agree? | Eligible for WOWY research? |
| --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| Stephen Curry | Draymond Green | 7 | 175.03 | 4 | 20.55 | ON differs 5.70 min (3.2%), OFF agrees 0.42 min | No. OFF exposure well under 120 minutes and only four games |
| Jalen Brunson | Josh Hart | 7 | 205.13 | 7 | 66.57 | Yes: ON differs 1.34 min; OFF differs 0.40 min | No. OFF exposure under 120 minutes |
| Franz Wagner | Paolo Banchero | — | — | — | — | HTTP error on bounded query | Unverified |
| Trae Young | Anthony Davis | — | — | — | — | HTTP error on bounded query | Unverified |

Data source: PBP Stats public `get-wowy-stats/nba` and `get-playing-time-distribution/nba`, requested with a date cutoff of 2026-11-06. These observations came from one-time bounded diagnostics rather than a bulk download; raw player statistics and full possession records were not committed to GitHub.

### Why we don't automatically change picks yet
- A real, reachable dataset is not necessarily a stable input. Both successfully analyzed pairs lacked the required independent OFF exposure (currently minimum 5 games *and* 120 minutes).
- Game possession intervals include zero-duration entries and overlapping spans. The validator now ignores empty entries and unions overlapping spans without double-counting.
- The sample-qualification routine enforces independent ON and OFF game dates and possession exposure.
- A successful response demonstrates reachability, **not** unrestricted API data rights, and not predictive accuracy.
- Provider HTTP errors for the other two pairs were not categorized by status in the original one-time test. Do not assume they were 429 errors or permission denials.

### Next data-dependent step
Select a player–teammate pair that meets 5 games and 120 minutes in *both* conditions from verified, cutoff-limited game-level records. Evaluate the PTS/REB/AST per-36 differences prospectively, freeze the candidate pretip, and grade the real subsequent outcome against the Combined AI on identical archived lines. Keep the live board unchanged until the comparison has enough independent observations.

Source files: `docs/pbpstats_onoff_coverage_probe.json`, `docs/pbpstats_current_season_probe.json`, `iphone_bot/pbpstats_game_coverage.py`, `iphone_bot/assemble_pbpstats_wowy.py`.
