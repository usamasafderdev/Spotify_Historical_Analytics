# MGD+ vs Dhruvil v85 Comparison

**Review date:** 2026-10-26  
**Scope:** US daily Top 200 rows with stable track IDs and actual per-chart streams. Comparison is technical research, not a source-precedence decision or permission approval.

## Sources and matching rules

- MGD+: supplied archive `D:\Downloads\MGDplus.zip`, SHA-256 `93ad6b8dd7e8443fbfbece0d56bf74120073f69b1315706e305b995301e5392a`.
- Dhruvil v85: the separate compact research DB at `D:\Study Material\University\Spotify-Dataset-Research\staging\research_staging_compact.sqlite`. Its source status is `UNVERIFIED`.
- MGD+ rows were selected only from `market=us`, `Chart=Top 200`; Dhruvil rows were selected only from `country=US`, daily songs, `chart_name=top200`.
- Observation identity is `(market, chart type, chart date, track ID)`. `position` and `streams` are compared as values. A rank change is therefore a conflict on a shared track/date identity, not two unrelated missing observations.
- Duplicate source rows are not summed. Identities and observed rank/stream signatures are held as sets. The 200 additional repeated rows in MGD+ on 2021-09-01 do not inflate distinct-identity counts.

## Coverage and overlap

Dhruvil's stream-bearing Top 200 comparison span is **2017-01-01 through 2021-12-31**, with 364,184 unique identities. MGD+ has 378,600 unique US Top 200 identities overall, including repeated source rows in its 378,800-row chart member.

| Comparison measure | Result |
|---|---:|
| MGD+ unique identities within Dhruvil's date span | 364,200 |
| Shared identities | 363,785 |
| Same rank and stream values on shared identities | 363,785 |
| Conflicting shared identities | 0 |
| Dhruvil-only identities within common dates | 399 |
| MGD+-only identities within common dates | 415 |
| MGD+ identities after Dhruvil's last date | 14,400 |
| Distinct MGD+ identities after Dhruvil span | 14,400 |

The 14,400 post-span MGD+ identities occur on **72 dates in 2022**, from January 1 through March 13 (14,400/200 rows per observed date). There are no MGD+ chart rows after March 13, 2022; no 2023–2026 coverage is present.

### By year

| Year | Dhruvil identities | MGD+ identities | Shared, matching rank and streams | Dhruvil only | MGD+ only |
|---:|---:|---:|---:|---:|---:|
| 2017 | 72,384 | 72,200 | 72,185 | 199 | 15 |
| 2018 | 73,000 | 73,000 | 73,000 | 0 | 0 |
| 2019 | 73,000 | 72,800 | 72,800 | 200 | 0 |
| 2020 | 73,200 | 73,200 | 73,200 | 0 | 0 |
| 2021 | 72,600 | 73,000 | 72,600 | 0 | 400 |
| 2022 | 0 | 14,400 | 0 | 0 | 14,400 |

All shared identity observations match on both rank and stream values. This establishes agreement for these matching rows only; it does not prove either source is complete, correct, independent, or authoritative. Source-only rows are unresolved discrepancies, not automatically missing records in the other source.

## Track and artist metadata overlap

The stream-bearing Dhruvil Top 200 rows have 9,303 distinct track IDs; the MGD+ US Top 200 has 9,589. **9,299 track IDs are shared**; four occur only in Dhruvil and 290 only in MGD+.

MGD+ song metadata has stable song and artist IDs for all 9,589 MGD+ chart track IDs. Of these charting tracks, 3,690 map to multiple artist IDs, so artist attribution requires the application's documented full-credit policy and can overlap. For the 9,299 shared track IDs, MGD+ IDs can potentially supply artist identity information missing from Dhruvil's source records, subject to rights review and exact-ID validation. This does not automatically validate the metadata's provenance or authorize using it.

All 2,061 distinct artist IDs exposed by MGD+ song metadata are present in its US artist metadata files. The MGD+ US metadata does not include album-related fields, so it does not provide verified track-to-album mappings.

## What this comparison does not establish

- The identical 363,785 shared stream values do not establish source independence; the sources may derive from overlapping upstream data.
- The 399 and 415 source-only common-span identities have not been independently resolved.
- MGD+ has five calendar-step gap candidates over its observed date span and a date with duplicate rows. Neither proves the expected publishing calendar.
- No full 2017–2022 coverage claim is supported: MGD+ ends March 13, 2022, and has no observations for 2023–2026.
- MGD+ record-level CC BY 4.0 metadata does not resolve upstream Spotify rights, commercial use, derived analytics, or redistribution. Both sources remain `UNVERIFIED`; do not import or package their records.

The machine-readable comparison is `D:\Study Material\University\Spotify-Dataset-Research\reports\phase6c_mgdplus_final\zenodo_mgdplus_audit.json`. The adapter reads the compact DB read-only and the ZIP in streaming mode.
