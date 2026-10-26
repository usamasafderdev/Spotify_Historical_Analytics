# Historical Data Acquisition Status

**Status date:** 2026-10-26  
**Required client range:** USA Spotify chart observations from 2017 through 2026. This requirement is not evidence that such data is available or licensed.

## Availability verified for this project

| Item | Verified status |
|---|---|
| Authorized production years | **None.** No dataset is approved for commercial processing or packaged in the client application. |
| Observed research-only candidate years | **2017–2021** in Dhruvil Dave v85. The audit staged 455,031 rows selected from the file's US `region` values; these observations do not establish source authenticity or complete historical coverage. |
| Synthetic QA years | 2017–2024 in the isolated demo fixture. These generated rows are not Spotify data and must never be described as real history. |
| Unverified / absent in the downloaded candidate | 2017–2021 contain calendar-step gaps; no rows were staged for 2022–2026 from the downloaded v85 file. Availability from other sources, completeness, provenance, and permitted commercial use remain unverified. |
| Research downloads | `dhruvildave/spotify-charts` v85 downloaded to the external research root. The one requested attempt for `gonzalopezgil/spotify-charts-daily-updated` v146 returned HTTP 404; no replacement version was tried. |
| Source downloaded for client production use | **No.** Research data is not automatically copied into the client production database. See the external `D:\Study Material\University\Spotify-Dataset-Research\reports\` audit outputs. |
| Imported production rows validated | **No.** No production source has been approved or imported. Deterministic test fixtures are synthetic and establish code behavior only. |
| Redistribution permission | **None confirmed.** No data provider, license, contract, or redistribution right has been approved. |
| Spotify affiliation | The application is independent and is not affiliated with, endorsed by, or an official Spotify product. |

This project deliberately does not assert complete USA chart coverage for 2017–2026. A populated local database must be audited separately; observed rows and dates do not establish that the source is complete.

## Potential sources — not approved or acquired

- **Spotify Charts** (`https://charts.spotify.com/`): official charts reference. Availability, export rights, historical retention, permitted reuse, derived analytics, and commercial distribution must be confirmed with Spotify before acquisition or use.
- **User-owned or provider-licensed archive**: a candidate only when the client has written rights covering acquisition, local processing, derived analytics, and the planned commercial distribution.
- **Third-party public repositories or dataset marketplaces** (including candidates noted in [DATA_FEASIBILITY.md](./DATA_FEASIBILITY.md)): availability online or a repository/data-platform listing does not establish Spotify authorization, a suitable license, data accuracy, completeness, or redistribution permission. Review each source's specific terms and upstream provenance before use.

Kaggle dataset versions 146 and 85 were reviewed as potential research sources in Phase 6. Version 146 returned HTTP 404; version 85 was downloaded for research-only analysis. Their details are recorded in the generated research reports. No source is approved for commercial use or imported into production.

## Legal and platform constraints

The official [Spotify Developer Policy](https://developer.spotify.com/policy) retrieved for this review states that developers must not analyze Spotify Content or the Spotify Service for purposes including new or derived listenership metrics, benchmarking, functionality, usage statistics, or user metrics. The published policy page identifies an effective date of **15 May 2025**. The [Spotify Developer Terms](https://developer.spotify.com/terms) also include commercial-use restrictions for Spotify developer applications. Applicability to a particular locally supplied dataset, non-platform data source, client workflow, and product distribution requires current legal review; this document is not legal advice.

In particular:

- Do not use Spotify platform/API data or Spotify Content for these derived analytics unless the applicable terms and written permission expressly allow the intended use.
- A user providing a file, owning a copy, or entering a source/license note in the application does **not** automatically grant rights to process, derive metrics from, sublicense, or redistribute its contents.
- Verify dataset provenance, source license, database rights, contractual limits, privacy obligations, and commercial redistribution rights independently.
- Do not scrape Spotify pages or use restricted endpoints as a workaround. No scraper or automated Spotify data download is implemented.
- Do not market the application using Spotify marks or language implying official affiliation.

Policies and contracts can change. Recheck the official policy and obtain counsel/platform confirmation immediately before acquisition, client deployment, or commercial delivery.

## Metadata gaps to resolve

Until an authorized archive is reviewed, it is unknown whether it supplies:

- Stable Spotify track IDs on every chart observation.
- Stable artist IDs and explicit collaborator-to-track relationships.
- Stable album IDs, track-to-album edition relationships, and album artist attribution.
- Consistent market, chart type, stream metric, and daily/weekly period semantics.
- Source provenance, coverage calendar, correction/deletion history, and a license permitting derived analysis.

Never infer artist/album identity from similar names. Unmapped album observations remain excluded from album rankings. Missing dates remain missing; no observations are not interpreted as verified zero streams.

## Before commercial use

Obtain and document: the exact source and version; authorization to acquire and retain it; permitted processing and derived analytics; commercial-use rights; redistribution/export rights for both raw and derived data; any attribution or deletion requirements; market and metric definitions; verified coverage years; validation methods; and written review of the Spotify policy implications. Then import a controlled sample, reconcile it against the provider's documented semantics, and report actual observed coverage without claiming completeness unless independently evidenced.
