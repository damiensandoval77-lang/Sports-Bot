# Tennis probe diagnostics

This collector remains a single authorized, durably claimed request. Diagnostics
changes do not authorize another request, modify its marker or schedule polling.

- `request_started_at` marks request initiation. `response_received_at` and
  successful `checked_at` mark receipt after reading the bounded response.
  Normalized quote `captured_at` and board `generated_at` use receipt time.
  An observation during an in-flight request is therefore not falsely future-dated.
- `metadata_present` reports only presence of the documented `mode`,
  `source_status`, and `next_cursor` fields. Missing pagination metadata never
  proves complete coverage. Source metadata is not inferred when absent.
- `normalization.rejection_counts` uses fixed reason labels with aggregate counts,
  never player names, IDs, raw values or exception text. Each rejected row counts
  once, at its first failed guard; these are not exhaustive per-row diagnoses.
  Accepted plus rejected counts equal the returned rows for normalization.
- The existing completed probe cannot be retrospectively diagnosed: its raw
  response was not retained. New counters apply only to a separately authorized
  future attempt. Estimates remain withheld, and quote validation is not relaxed.
