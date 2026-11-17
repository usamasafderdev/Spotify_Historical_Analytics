# 0.1.8 INTERNAL-READY data coverage

Measured 2026-11-17. These are owner-supplied source observations, not independently authenticated Spotify exports. External redistribution authorization is not established. Do not deliver this bundle externally until the release owner resolves that authorization.

| Separate metric | Accepted observations | Observed reporting dates / range |
|---|---:|---|
| US daily song streams | 721,171 | 3,606 dates; 2017-01-01 to 2026-11-15 |
| US source-weekly song streams | 12,599 | 63 sampled dates; 2022-01-06 to 2026-10-08 |
| Daily-derived song weeks | 131,729 track/week observations | 516 Sundays; 2017-01-01 to 2026-11-15 |
| US weekly album positions (no streams supplied) | 61,588 | 308 Thursdays; 2020-10-22 to 2026-11-12 |
| US daily artist positions (no direct streams supplied) | 368,000 | 1,840 dates; 2021-10-21 to 2026-11-15 |
| Artist listener snapshots (not song streams) | 3,262,204 | 130 observed dates; 2026-06-08 to 2026-11-16 |

Daily song observations cover 15,152 stable IDs and total **316,705,690,324** chart streams. Source-weekly observations cover 2,711 IDs and total **42,913,401,825** chart streams. Derived-weekly totals equal the daily total, not that total plus source-weekly streams. Missing observations are never filled; the first daily-derived reporting week is partial. Every calendar date in the daily interval is represented, but some dates contain fewer than 200 accepted observations. This does not certify complete or authentic historical chart coverage.

The native daily song file contributed 721,171 accepted US rows and 26 invalid US rows. The overlapping legacy file added **zero** observations after verification: 210,976 exact overlaps were skipped, 152,507 same-ID differences were quarantined, and 701 alternate-ID/date/rank collisions were quarantined rather than added to totals. These alternate IDs are not asserted to be aliases. Stream differences affect 51 same-ID conflicts, position differences 573, and label differences 152,174; categories overlap. All established source values remain unchanged. Earlier integration rejected one empty album name and one missing weekly track/artist label.

Metadata contains 220,884 tracks, 75,200 artists and 26,631 albums; exact relationships include 349,341 track-to-artist and 28,984 album-to-artist links. There are 705,473 URL references and **no track-to-album mappings**. Thus linked-track album stream rankings remain empty; independent weekly album position rankings are available in Chart showings. Artwork references are URLs, not downloaded images.

Compared with the previous v0.1.7 figures (716,997 daily, 65,599 source-weekly, 125,361 derived track/weeks), this release has later daily coverage but substantially fewer source-weekly observations. No old seed was overwritten or extracted. Full weekly history, independent authenticity, exact album membership, and external distribution authorization remain unresolved.

The installed documentation includes `source-manifest.json` (exact paths, sizes, timestamps and source hashes) and `integration-verification.json` (integrity, counts, date gaps, source differences and mapping coverage). The database retains exact conflict ledgers. Original CSV files are not bundled. Developer-side integration details are in `LOCAL_DATA_INTEGRATION.md`; normal users never need to copy a database or run PowerShell.
