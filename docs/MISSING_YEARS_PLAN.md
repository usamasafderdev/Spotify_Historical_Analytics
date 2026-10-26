# Missing Historical Years Plan

**Client target:** USA chart observations from 2017 through 2026.  
**Current status:** Research candidates only; no source is approved for production or commercial derived analytics.

## What is actually present

### Dhruvil Dave v85 (Kaggle; research only)

| Year | Top 200 rows | Top 200 dates | Viral 50 rows | Viral 50 dates | Viral 50 stream values |
|---:|---:|---:|---:|---:|---:|
| 2017 | 72,384 | 362 | 18,148 | 363 | 0 |
| 2018 | 73,000 | 365 | 18,229 | 365 | 0 |
| 2019 | 73,000 | 365 | 17,938 | 360 | 0 |
| 2020 | 73,200 | 366 | 18,300 | 366 | 0 |
| 2021 | 72,600 | 363 | 18,232 | 365 | 0 |
| 2022–2026 | 0 staged | 0 | 0 staged | 0 | 0 |

Top 200 rows have stream values. Viral 50 rows do not, so the Viral 50 data cannot support streaming-based rankings. Twenty-six rejected out-of-range rows were all Viral 50 rank 51; they remain excluded.

### Zenodo MGD+ (research-only archive)

The verified archive includes US regional Top 200 observations from 2017-01-01 through 2022-03-13: 378,800 source rows over 1,893 observed dates. It contains 72 observed dates in 2022 through March 13, and no Viral chart file. Five calendar-step gaps occur inside its first-to-last date span; 2021-09-01 contains 400 rows (200 repeated identities). The expected source schedule is not independently verified.

| Year | US Top 200 rows | Distinct observed dates | Notes |
|---:|---:|---:|---|
| 2017 | 72,200 | 361 | Four calendar gap candidates |
| 2018 | 73,000 | 365 | — |
| 2019 | 72,800 | 364 | One calendar gap candidate |
| 2020 | 73,200 | 366 | — |
| 2021 | 73,200 | 365 | 200 duplicate rows on 2021-09-01; 73,000 unique date/track/rank keys |
| 2022 | 14,400 | 72 | Observed only through 2022-03-13 |
| 2023–2026 | 0 in this archive | 0 | This archive ends in 2022; this is not evidence no other source exists |

MGD+ and Dhruvil v85 share 363,785 date/track-ID/rank keys for 2017–2021. All shared keys have identical stream values. There are 399 Dhruvil-only and 415 MGD+-only keys in their common date span. The match is a consistency check, not proof that either dataset is complete, authoritative, independent, or licensed.

## Required gaps and limits

- **2022:** MGD+ has observations through March 13 only; April–December are unverified and not covered by that archive.
- **2023–2026:** No observations were validated from the reviewed files.
- **Viral 50:** The reviewed MGD+ archive does not include Viral 50. Dhruvil v85 includes rank data but no stream values.
- **Albums:** No album fields were found in the inspected MGD+ US song/artist metadata schemas. Do not infer album mappings from track titles.
- **Rights:** Both sources are `UNVERIFIED` for upstream Spotify rights, commercial derived analytics, and redistribution. Neither may enter production.

No year is described as complete. Calendar-day gaps, zero-row dates, and source listings do not establish an expected publication schedule.

## Safe acquisition sequence

1. Request a client-owned or provider-licensed archive with written permission for retention, local processing, derived analytics, commercial use, exports, and redistribution. A user-supplied file alone is not permission.
2. Require the source/version, geography semantics, chart definitions, cadence, stream metric, expected publication calendar, corrections policy, provenance, and redistribution terms.
3. Obtain USA Top 200 daily data and Viral 50 data for 2017–2026 with stable track IDs, ranks, and actual stream values where that metric exists. If only a subset is authorized, report that exact subset.
4. Keep new data in external research staging. Verify checksums, schemas, US-only selection, row totals, date/rank counts, duplicates, missing dates, and stream semantics before any production decision.
5. Compare overlaps by stable IDs and chart/date/rank. Preserve conflicts; never sum duplicate records or prefer a source without documented evidence.
6. Import only after written legal/platform review and explicit source/version approval. Do not scrape Spotify or treat restricted developer data as a workaround.

## Output locations

The detailed 2017–2026 year/month/date candidates and source comparisons are in the external research root:

- `reports\phase6b_compact_audit\chart_quality_by_year.csv`
- `reports\phase6b_compact_audit\chart_quality_by_month.csv`
- `reports\phase6b_compact_audit\chart_quality_by_date.csv`
- `reports\phase6b_zenodo_audited\zenodo_mgdplus_us_chart_by_year.csv`
- `reports\phase6b_zenodo_audited\zenodo_mgdplus_us_chart_by_month.csv`
- `reports\phase6b_zenodo_audited\zenodo_mgdplus_us_chart_by_date.csv`
- `reports\phase6b_zenodo_audited\zenodo_mgdplus_audit.json`

All are research artifacts outside the repository, production database, and Windows executable.
