# Local tennis quote provenance boundary

This module has no network client, publication path or schedule. It does not activate forecasts or grading. A hash binds receipt content, not the truth of supplied data or an independently trusted timestamp.

`capture_quote` accepts fresh normalized pregame snapshots with explicit available standard-side evidence, preserves unknown other sides, and records the actual recording time. `write_receipt` uses exclusive-create, content-addressed local files; an existing unequal file is not overwritten.

`supplied_result_outcome` supports only symmetric Total Games. It requires exact same-provider fixture and both participant IDs, completed conventional score, explicit non-retired/non-walkover status and chronological source receipt. Its caller verification assertion is not independent evidence: output always says `unverified_supplied_result`, `offline_research_only`, `live_ready=false`, and never produces model wins or hit rates.

Current normalized tennis quotes contain player ID and opponent name but no exact opponent ID. They may be captured, but cannot settle through this boundary. Names must not be guessed or substituted for a verified identity crosswalk. Total Games Won score orientation, Aces and Fantasy Score actuals are unsupported. No production result adapter currently exists.
