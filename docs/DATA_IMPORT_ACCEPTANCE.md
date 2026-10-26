# Data import acceptance

## Desktop local-file import

The client importer is one **Import Historical Music Data** dialog. It accepts
CSV, XLSX, and supported CSV.GZ tables, detects known MGD+/Dhruvil schemas,
previews valid USA records and coverage, reports validation warnings, and imports
only after the user clicks **Import Dataset**. Unknown schemas can be mapped in
that dialog. No JSON rights manifest, reviewer, evidence upload, or authorization
questionnaire is required.

Acceptance checks:

- Required source columns and the exact selected file are validated before writes.
- Only explicit USA records and the selected daily/weekly cadence are accepted.
- Dates and supplied stream values are validated; missing metrics are not zeroed.
- Stable IDs are preserved. Artist/album associations require explicit IDs/names.
- Weekly rows require supplied boundaries; missing dates are not invented.
- Exact duplicates are skipped; conflicting observations block the transaction.
- A backup precedes production writes. Cancellation/failure rolls back the transaction.
- Production integrity is checked and results report actual imported/skipped/rejected counts.
- Source name, file digest, and unverified-permission provenance remain recorded.
- Importing a file does not create rights approvals or permission to redistribute it.

See [SIMPLE_IMPORT_INTERFACE.md](SIMPLE_IMPORT_INTERFACE.md) for implementation,
rendered evidence, tests, formats, and current release verification.

## Separate research-data safeguards

Research datasets remain separate from the production application and EXE. Their
existing rights state is not changed by removing the client manifest UI. The
controlled `research_pipeline.py` transfer functions retain their own approval
checks and evidence records; local-file imports do not automatically transfer
research staging databases or approve candidate archives.

Source terms and restrictions continue to apply to acquisition, analytics,
commercial use, export, and redistribution. User upload, attribution, and a
successful technical import do not independently verify these permissions.
Existing historical approval/audit records are preserved. The application does
not authenticate external reviewers or determine contractual scope.

Review data quality, intended use, attribution, retention, and distribution
requirements separately before delivering or bundling any third-party dataset.
No unapproved research data is bundled by the application build.
