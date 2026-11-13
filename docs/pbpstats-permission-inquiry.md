# PBP Stats provider usage approval request — NOT SENT

**Recipient lead:** The author/maintainer public contact appears in https://pypi.org/project/pbpstats/ as the package author email. Independently verify this address belongs to the PBP Stats API operator before sending. The open-source package's MIT license does NOT establish rights to the provider's statistics or to underlying NBA data.

**Subject:** PBP Stats API permission and data availability for personal NBA player-prop research

Hello,

I'm developing a privately operated NBA player-prop research application. I would like to use PBP Stats' documented JSON API (specifically `get-wowy-stats/nba`, `get-playing-time-distribution/nba`, `get-wowy-combo-playing-time-distribution/nba`, and possibly game logs) to model how teammates' presence changes a player's expected minutes, scoring, rebounds, and assists.

Before turning on recurring collection, could you clarify:

1. Do you permit recurring authenticated or unauthenticated API calls for an application that researches or predicts sportsbook/PrizePicks player props? Is this permitted for personal/internal research, or does a separate paid/commercial license apply?
2. What are the documented request limits, attribution requirements, and any fees or approved authentication methods?
3. May I temporarily cache raw JSON privately, store normalized pregame snapshots, train prediction models on the statistics, and publish only derived projections/accuracy summaries (not redistribute the original rows)?
4. Does authorization extend to the underlying NBA statistics used to produce the PBP Stats data, or must a separate NBA data license be obtained?
5. How can I obtain independently verifiable dated game-level ON/OFF samples (with player and teammate IDs, actual seconds together/apart, game IDs and dates) for the 2026–27 season? Does the playing-time distribution endpoint support a verified historical cutoff and fully represent those stints?
6. Is your API usable in GitHub Actions for a low-volume scheduled pregame update, assuming compliance with any rate limits?

I can provide the precise expected request volume and show the project architecture if useful. I will not activate automated statistical ingestion until permitted use is confirmed.

Thank you.

---

**Approval handling:** Save the provider's reply privately. Set `licensed_use_verified=true` only after checking the actual permitted use and any NBA third-party restrictions. Never commit correspondence, provider-supplied private data, or credentials to the public repo.

**Status:** Contact identified from public package listing; inquiry prepared only. No email has been sent or permission received.
