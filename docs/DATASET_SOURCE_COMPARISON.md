# Dataset Source Comparison

| Attribute | `gonzalopezgil/spotify-charts-daily-updated` | `dhruvildave/spotify-charts` |
|---|---|---|
| Kaggle listing | [Source page](https://www.kaggle.com/datasets/gonzalopezgil/spotify-charts-daily-updated) | [Source page](https://www.kaggle.com/datasets/dhruvildave/spotify-charts) |
| Pinned listing version checked | 146 | 85 |
| Listing update | 2026-10-25 | 2022-02-09 |
| Listing categories | Daily songs/artists, weekly albums, entity metadata, listeners, artwork and links (listing claims; local schema not assumed) | Global Top 200 and Viral 50; listing states history since 2017 |
| Listing license | CC BY-SA 4.0 | ODbL 1.0 database / original-author contents |
| Listed archive size | Page reported 0 bytes; actual size unknown until file inspection | Page reported 991,225,045 bytes |
| USA-only | Not established by the listing | Not established; description says global |
| Stream availability | Must be checked field-by-field in source files | Listing says Viral 50 streams are NULL; local rows still require validation |
| 2017–2026 coverage | Not confirmed | The version listing is from 2022; 2023–2026 cannot be assumed |
| Production permission | UNVERIFIED | UNVERIFIED |

## Local inspection results

- Source 1 v146 returned HTTP 404 from KaggleHub; no version was substituted and no local file was inspected.
- Source 2 v85 yielded one `charts.csv` file, 3,483,476,388 bytes and 26,173,514 rows. The inspected `region` field allowed the parser to stage 455,031 US rows; 25,718,457 other/unknown regions and 26 out-of-range ranks were rejected.
- The accepted rows were daily Top 200 and Viral 50 songs for 2017–2021. Top 200 had stream values; Viral 50 stream values were missing. Stable track IDs were not explicit columns; only syntactically verified Spotify track URLs are used for IDs.
- The accepted US rows contain 14,649 distinct track IDs extracted from the source URLs. There are no separate stable artist IDs or album mappings in this file.
- No chart observations were staged for 2022–2026 from this pinned source. This is not evidence that no such data exists elsewhere.

The separate `reports\dataset_inventory.csv`, `coverage_by_year.csv`, `source_overlap.csv`, and `data_conflicts.csv` files are the local evidence for actual downloads. No precedence is assigned. Identical observations are identified, conflicts are preserved, and no duplicate stream values are summed.

The two input references identify two unique dataset IDs. The downloader de-duplicates by dataset ID and makes at most one pinned-version call per unique ID in each invocation.
