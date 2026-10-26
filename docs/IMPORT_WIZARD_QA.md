> Historical report: the wizard and mandatory manifest described here have been replaced. See [SIMPLE_IMPORT_INTERFACE.md](SIMPLE_IMPORT_INTERFACE.md) for the current workflow.

# Import Wizard QA

## Implemented workflow

The desktop application now exposes a persisted 13-stage CSV/XLSX import wizard:

1. Select a local dataset.
2. Identify the source and chart cadence.
3. Fingerprint and inspect the file in a worker thread.
4. Review detected columns, map fields, and stage the data.
5. Validate the explicit country/market.
6. Validate dates and chart cadence.
7. Validate integer stream values.
8. Review track, artist, and album identifiers.
9. Review exact duplicates and conflicting observations.
10. Review observed annual coverage and missing daily-date candidates.
11. Record an externally reviewed, hash-bound rights manifest.
12. Confirm the intended production import.
13. Run the production transaction and check SQLite integrity.

The staging database is separate from production and is stored under the
per-user application data root. CSV is parsed as a stream; XLSX files use
read-only workbook iteration. Accepted rows are committed in bounded chunks.
Rejections are counted by reason, with at most 100 diagnostic samples kept.
The source path, size, modification time, SHA-256, schema mapping, row
checkpoint, stage, status, and error are persisted. Resumption checks the
source fingerprint and refuses to continue if the selected file changed.

Production insertion uses a worker-owned SQLite connection and a single
transaction. It rechecks the source and evidence hashes, blocks conflicting
observations and incompatible metadata IDs, inserts chart rows and supplied
identity mappings, records the manifest/evidence digests, and runs
`PRAGMA integrity_check` before commit. The same staged session cannot be
finalized twice; importing an identical file in a new session skips matching
observations instead of adding duplicate streams.

## Rights boundary

The manifest must identify the exact source and file digest, include dataset
version, reviewer and review date, point to documentary evidence whose hash
matches, and explicitly approve acquisition, derived analytics, commercial
use, and redistribution/export. Missing or false scopes block import.

This is an evidence-recording control, not independent legal verification.
The application cannot establish the validity of a contract, reviewer
authority, or permission scope. The label recorded in production means that
matching evidence and a review assertion were recorded; it does not mean that
the application certified the rights. A checkbox and a provenance note cannot
approve a source.

The existing direct metadata-import UI is disabled because it does not yet
use this same rights-gated workflow. Metadata associations can be imported
only when explicitly included in an approved chart-data session; a separate
metadata-only staging flow is not implemented.

## Automated verification

`tests/test_import_sessions.py` and `tests/test_import_wizard.py` use only
generated synthetic CSV/evidence fixtures. They cover chunked staging,
validation and bounded rejection samples, duplicate and conflict detection,
file-change refusal, missing/mismatched rights evidence, no production writes
without approval, transactional rollback, repeated imports, multi-artist
identity mappings without duplicate stream totals, safe pause, real Qt wizard
navigation, main-window entry points, and an end-to-end isolated import.

Run the focused suite with:

```powershell
python -m pytest -q tests\test_import_sessions.py tests\test_import_wizard.py
```

## Limitations / not release acceptance

- Source-specific MGD+ and Dhruvil adapters are not automatically selected by
  this generic schema-mapping wizard.
- Legal rights and reviewer authority remain externally determined.
- Metadata-only imports and album metadata without a supplied, exact mapping
  remain unavailable.
- Native interactive Windows visual inspection, DPI review, and installer
  compilation must be documented separately from offscreen tests.
- No MGD+ or Dhruvil research data is copied into staging or production by
  this workflow.
