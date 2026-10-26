# Kaggle Dataset Discovery Report

**Review date:** 2026-10-26  
**Local file inspection status:** Refer to the machine-generated inventory at the research root. The Kaggle page listing is not a substitute for opening and validating downloaded files.

## Source 1

- Dataset: [Spotify Charts Daily Updated](https://www.kaggle.com/datasets/gonzalopezgil/spotify-charts-daily-updated)
- Publisher: Gonzalo López Gil
- Pinned listing version: 146
- Kaggle listing says CC BY-SA 4.0.
- Listing description advertises `charts_songs_daily.csv.gz`, `charts_artists_daily.csv.gz`, `charts_albums_weekly.csv.gz`, `artist_listeners_daily.csv`, and normalized song/artist/album/artwork/link tables.
- The listing page reported a distribution content size of `0 bytes`; actual download size must come from the local file inventory.
- Listing categories, columns, date coverage, market coverage, stream availability, and upstream data rights remain unverified until local files are successfully inspected.

## Source 2

- Dataset: [Spotify Charts](https://www.kaggle.com/datasets/dhruvildave/spotify-charts)
- Publisher: Dhruvil Dave
- Pinned listing version: 85
- Kaggle listing says “Database: Open Database, Contents: © Original Authors” under ODbL 1.0.
- Listing description states global Top 200 and Viral 50 charts beginning 2017, and notes that viral-chart stream values are NULL.
- Listing page reported a 991,225,045-byte archive and a last-modified date of 2022-02-09.
- These statements are listing metadata, not validation of local CSV schemas, US records, stream values, completeness, or current commercial rights.

## Local inventory

The audit produces `reports\dataset_inventory.csv` with the actual discovered path, format, bytes, SHA-256, row count where measurable, source version, headers, mapped columns, category, listed license, and permission status. It also produces `reports\dataset_download_status.json` and a source registry.

The project does not commit research data or fabricated production metrics. If a source is absent or the download fails, inventory rows say `NOT_DOWNLOADED` or record the actual failure; coverage outputs report no validated observations rather than inventing dates or counts.

## Local inspection results (2026-10-26)

- The pinned request for `gonzalopezgil/spotify-charts-daily-updated` v146 returned Kaggle HTTP 404. No local file or schema was available for that source; it was not retried with another version.
- `dhruvildave/spotify-charts` v85 downloaded into the external research root as `charts.csv` (3,483,476,388 bytes; 26,173,514 source rows; SHA-256 `8238a106f723af9b1d3b857b78ec43f7147d82472b491c63853bcbcc3c23cb1b`). Its inspected columns are `title`, `rank`, `date`, `artist`, `url`, `region`, `chart`, `trend`, and `streams`.
- The parser accepted 455,031 rows whose `region` normalized to US and rejected 25,718,483 rows: 25,718,457 non-US/unknown-region rows and 26 rows outside the configured chart rank limits.
- Accepted rows are daily song-chart observations. The source includes Top 200 stream values and Viral 50 rows with missing streams, consistent with the listing description. No stream totals are computed here.
- The observed US candidate records span 2017-01-01 through 2021-12-31 only. They are research-staged observations, not verified complete chart coverage or approved commercial data.
- The 455,031 accepted rows contain 14,649 distinct track IDs. IDs are derived only from exact `open.spotify.com/track/<22-character-ID>` URLs; this source has no separate stable artist IDs, album IDs, or album mappings.
- The schema-v3 per-file audit elapsed time was 600.18 seconds, including file hashing, row processing, staging, and inventory. Sampled peak process RSS during row processing was 139,591,680 bytes (about 133.1 MiB). These are local measurements, not performance guarantees.

The measured row counts and coverage by year are in the external research reports. Rights remain `UNVERIFIED`; this local inspection does not authenticate the upstream data or establish permission for commercial derived analytics.
