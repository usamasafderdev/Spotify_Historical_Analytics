# Data Feasibility and Source Review

This project is intentionally designed to work with user-supplied historical CSV/XLSX files and to avoid any unsupported scraping or redistribution of protected Spotify datasets.

## Verified source review

| Source | Purpose | Date range | Region | Fields | License / rights | Status |
|---|---|---:|---|---|---|---|
| Spotify Charts | Official charts reference | Varies by chart, current product period | Global and country-specific | Ranking, track, artist, streams, dates | Spotify terms and charts product policies | Reference only; not used for automated ingestion without explicit permission and compliance checks |
| Spotify support article | Chart definitions | Ongoing | Global | Chart definitions and terminology | Public documentation | Reference only |
| Spotify developer policy | API and platform use rules | Ongoing | Global | Platform/data usage rules | Public legal policy | Reference only |
| Spotify user guidelines | Platform terms | Ongoing | Global | User and platform conduct | Public legal policy | Reference only |
| Kaggle dataset | Historical chart archive | 2017-2021 examples reported | USA and others, dataset-specific | Tracks, artists, dates, streams | Must be reviewed per dataset license and redistribution policy | Blocked by default until rights are confirmed |
| IAjimi/Spotify200 | Historical USA chart archive | Dataset-specific | USA | Track-level chart data | Must be reviewed per repository license | Blocked by default until rights are confirmed |
| younver/spotify-top-200-dataset | Reference dataset | Dataset-specific | Global/market-specific | Chart data | Must be reviewed per repo license | Blocked by default until rights are confirmed |

## Operational conclusions

- Historical Spotify chart data is not assumed to be complete across 2017-2026.
- USA chart data must be validated for market and stream semantics before use.
- The application must not silently fabricate missing observations or claim complete official platform totals.
- This app supports lawful import of user-owned CSV/XLSX data and produces derived metrics only from valid imported rows.
- Any automated ingestion of third-party datasets must be blocked unless a source's terms and redistribution rights are explicitly verified.

## Default project stance

- Real data acquisition is treated as user-assisted and documented.
- Unsupported or unverified sources remain blocked and visible in the app as unavailable.
- A synthetic demo dataset is allowed only for UI testing and is clearly labeled `DEMO / SYNTHETIC`.
