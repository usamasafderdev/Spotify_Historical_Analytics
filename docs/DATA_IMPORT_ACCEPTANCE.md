# Data Import Acceptance

## Required source evidence

Before a source/version can use the research-staging production import function, retain a documentary evidence file for that exact dataset version and record:

1. The source, version, acquisition route, and source-file digest.
2. Permission for acquisition and local retention.
3. Permission for derived analytics.
4. Commercial-use permission for the intended product.
5. Redistribution and export permission for raw and derived content, as applicable.
6. Attribution, deletion, geographic, retention, or other restrictions.
7. Named reviewer and review date.

Approval JSON must provide all four scope values as `true`: `acquisition`, `derived_analytics`, `commercial_use`, and `redistribution`. A false or missing scope blocks approval. Evidence must resolve to an existing file. Its SHA-256 and the attested scopes are retained in research-staging rights notes.

This software records evidence and review assertions; it cannot independently validate a contract, determine legal scope, authenticate reviewer authority, or override platform terms. A checked box, user statement, dataset listing, public availability, source attribution, or file ownership is not by itself proof of rights. Obtain qualified legal review and provider/platform authorization where required.

## Staging and approval sequence

The supported research pipeline separates file inventory and chunked validation from production import:

1. Detect and fingerprint the file.
2. Verify file format and required source columns.
3. Validate region; only recognized US values are accepted for US coverage.
4. Preserve chart category and explicit cadence; do not infer weekly periods.
5. Validate ISO chart dates.
6. Validate stable track IDs and preserve source URL/reference.
7. Validate integer stream values; Viral 50 remains separate and streamless.
8. Record duplicates and conflicts without summing source observations.
9. Review source rights against documentary evidence.
10. Record dataset/version rights scope and reviewer.
11. Perform explicit transactional production import only after the gate.
12. Verify SQLite integrity and transaction outcome.
13. Refresh dashboard queries after a successful import.

The source adapters in `spotify_historical_analytics.source_adapters` are read-only normalization interfaces. They do not run this import sequence and do not write to production.

## Production protections

- Unapproved research-source imports raise `PermissionError`.
- Unsupported categories, Viral charts, and weekly rows without explicit week boundaries are rejected from the production chart table.
- The production insert is transactional and idempotent against the database uniqueness constraint.
- Current MGD+ and Dhruvil datasets are not authorized and must not be imported.
- Manual user-file imports remain marked as user supplied and rights-unverified. The provenance text is not a legal approval.

## Acceptance checklist for a future authorized archive

- [ ] Exact source/version and source-file SHA-256 recorded.
- [ ] Documentary permission reviewed for each intended use scope.
- [ ] Source schema matches a supported adapter or a reviewed mapping.
- [ ] US market, chart category, date, ID, rank, and stream fields validated.
- [ ] Duplicate and conflict report reviewed; no duplicate rows summed.
- [ ] Artist mappings use stable IDs and preserve all explicit credits.
- [ ] Album editions use stable `track_id`, `album_id`, name, album artist, release date, and source reference.
- [ ] Import occurs in a test database first and passes integrity/query checks.
- [ ] Production import is explicitly approved and backed up.
- [ ] Export, attribution, deletion, and redistribution behavior reviewed.
- [ ] Coverage gaps are disclosed; observed coverage is not represented as completeness.
