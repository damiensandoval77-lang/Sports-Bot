# Two reviewed target holds

These are standard-line statistical outcomes, not a claim about platform-specific settlement. No frozen line, projection, player identity, other market, or alternate-tier outcome is changed.

- `2026_10_SEA_LV`, Tory Horton (`00-0040648`): the complete official gamebook page 2 attributes all 17 Seattle pass attempts to five receivers (10 + 3 + 1 + 2 + 1 targets). Horton has 10 offensive snaps in the reviewed ledger, but zero targets. There are no unallocated attempts from which an omitted receiver could have a target.
- `2026_10_SF_DAL`, Demarcus Robinson (`00-0032775`): page 2 attributes all 28 San Francisco pass attempts to six receivers (9 + 7 + 4 + 3 + 3 + 2 targets). Robinson has 21 offensive snaps but zero targets.

The source URLs and PDF hashes are retained in the corresponding reviewed gamebook JSON files. No PDF is redistributed.

Independent cross-check: nflverse `play_by_play_2026.csv.gz` from its official GitHub release, SHA256 `696bf931fc5097ae1cab274cb08421fdb448a431b5e5f75cdfa12c6e9f480015`. Filter exact game and possession team, pass_attempt=1, excluding no-play, sacks and two-point attempts. This yields 17 and 28 pass attempts, respectively, each with a named receiver ID. Neither player's ID appears. The derived play IDs and receiver IDs are stored in the hash-pinned player proof, not downloaded at runtime.

This is not a generic rule that an omitted box-score row means zero targets. Only these individually reviewed complete-allocation proofs remove the TGT exclusion. All other target holds remain intact. The full transcript hash, final event validation, team/category totals and frozen identity checks still apply.
