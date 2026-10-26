# Data Permission Status

## Current source statuses

| Dataset | Listing license | Rights status |
|---|---|---|
| `gonzalopezgil/spotify-charts-daily-updated` v146 | CC BY-SA 4.0 on Kaggle | UNVERIFIED |
| `dhruvildave/spotify-charts` v85 | ODbL 1.0 database / original-author contents on Kaggle | UNVERIFIED |
| Zenodo MGD+ record 8086643 | CC BY 4.0 stated on Zenodo record | UNVERIFIED for upstream Spotify content and intended commercial analytics |

A dataset platform's stated license does not by itself prove upstream ownership or resolve rights in Spotify Content, database contents, derived analytics, or an intended commercial product. The status defaults to `UNVERIFIED` for each dataset version. No automatic approval is granted from a Kaggle page, metadata field, source attribution, user upload, or download success.

## Phase 6 local research audit

The pinned request for `gonzalopezgil/spotify-charts-daily-updated` v146 returned HTTP 404. `dhruvildave/spotify-charts` v85 was downloaded and audited in the separate research root; 455,031 US candidate rows were staged from a 26,173,514-row CSV. This is a technical schema/market validation only. It is not an upstream provenance check or license approval. `permissions_approved` remains 0 and `production_imports_performed` remains 0.

The current Kaggle listing was separately checked and reported v146. No version 146 cache was found. The unversioned KaggleHub download was not called because the conservative free-space requirement (47,033,771,609 bytes) exceeded the 31,576,604,672 bytes available at preflight. Zenodo MGD+ was downloaded (364,603,433 bytes) and CRC-checked, but its archive was not extracted or production-imported. Record-level CC BY 4.0 metadata does not establish rights to underlying Spotify content, commercial derived analytics, or redistribution. No data rights status was changed or approved.

## Approval gate

Research records are staged in a separate SQLite database and are not exposed to the desktop app. The programmatic production-import gate requires a JSON approval record for the exact dataset ID and version, reviewer, review date, and a path to an existing evidence file. The operator/release owner must verify the underlying evidence and current terms. The code verifies that a reference exists; it cannot decide that the evidence is legally sufficient.

Possible states are `UNVERIFIED`, `APPROVED`, `RESTRICTED`, and `REJECTED`. Only `APPROVED` permits the controlled production importer, and only compatible song-chart rows with actual stream values can pass its current schema gate. Artist and album metrics remain out of song totals.

## Platform review

Spotify's [Developer Policy](https://developer.spotify.com/policy) says it is effective 15 May 2025 and restricts certain analysis of Spotify Content or the Spotify Service, including derived listenership metrics. Whether this policy governs a specific third-party dataset and the client's offline/commercial use needs current counsel/platform review. No legal conclusion is made here. Do not scrape Spotify, bypass access controls, or bundle unapproved records in the application.

Required written approvals before commercial integration should address acquisition, retention, local processing, derived analytics, commercial use, export, redistribution, attribution, deletion/correction obligations, and upstream provenance. Counsel should review applicable Spotify terms and dataset/database licenses.
