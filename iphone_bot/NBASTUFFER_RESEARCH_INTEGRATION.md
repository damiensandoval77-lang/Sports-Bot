# NBAstuffer research-data evaluation (not a live feed)

Source references:
- https://www.nbastuffer.com/2026-2027-nba-player-stats/
- https://www.nbastuffer.com/2026-2027-nba-team-stats/
- https://www.nbastuffer.com/terms-of-use/

**Status: offline research adapter only.** NBAstuffer's published terms restrict
commercial use and alteration/transformation of its work. Do **not** set up an
automated collector, extract its tables for production, or redistribute its data
without confirming suitable usage rights. Public visibility is not a license.

`external_stats_snapshot.load_snapshot(csv_path, manifest_path, kind)` reads
only explicitly supplied, authorized CSV files and corresponding JSON manifest.
It makes **no network requests**. A manifest example:

```json
{
  "source_name": "licensed research dataset",
  "source_url": "https://example.com/licensed-data",
  "season": "2026-2027",
  "as_of": "2026-11-09",
  "rights_confirmed": true,
  "research_only": true
}
```

The caller is responsible for verifying rights; do not set rights_confirmed
unless that verification has been done. Raw exported statistics and personal
identifiers should not be committed to the repository. The adapter rejects
stale, future-dated, malformed, non-finite and duplicate rows; it reports
provenance, date and research-only status, and fails closed. Do not silently
replace missing values with zero.

## Next modeling gates

1. Source approval and audit: access rights, permitted refresh rate, schema,
   team naming and stable player IDs across trades. Use verified player IDs
   rather than joining on player names alone.
2. Historical player GAME logs and opponent/game chronology remain the source
   for variance and defense-vs-position. Season aggregates cannot reconstruct
   player-game outcomes or identify actual on-court defenders.
3. Join only pre-tip snapshots, recording snapshot timestamp, game ID and
   origin of each feature. Reject look-ahead leakage.
4. Compare a baseline model with a shadow challenger incorporating validated
   pace, minutes, usage and efficiency. The matchup-aware projection already
   includes opponent effects; don't multiply by the defensive factor again.
5. Evaluate walk-forward holdouts for MAE, bias, empirical calibration, log
   loss/Brier score where applicable, by-market coverage and missingness.
   Preserve the existing 20,000-draw research simulator and label simulation
   percentages **uncalibrated** until validated.
6. Promote only if reliability, coverage and calibration meet explicit gates;
   otherwise preserve the current production behavior and report the reason.

Existing `position_defense.py` is a separate historical coarse-role (G/F/C)
feature pipeline. It is not verified defender matchup tracking.

Run tests:
`python -m unittest discover -s iphone_bot/tests -p 'test_external_stats_snapshot.py' -v`
