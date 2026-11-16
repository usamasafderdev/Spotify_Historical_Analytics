# Local development integration

Integrated on 2026-11-16 into one isolated database:
`local-data/v018-integration/database/analytics.db`.
The existing per-user database, downloads, and previous releases are unchanged.
Launch this data with `scripts/run_integrated.ps1`; normal installed application data is separate.

| Completed source | Category | Imported source rows |
|---|---|---:|
| `artists.csv` | Artist metadata | 74,291 |
| `albums.csv` | Album metadata | 26,631 |
| `songs.csv` | Track metadata | 218,095 |
| `artwork.csv` | Artwork URL snapshots; images not downloaded | 312,520 |
| `links.csv` | Spotify references and retained external-link metadata | 147,917 |
| `spotify_top200_positions_2022.csv.gz` | US source-weekly observations with streams | 2,600 |
| `spotify_top200_positions_2023.csv.gz` | US source-weekly observations with streams | 2,600 |
| `spotify_top200_positions_2024.csv.gz` | US source-weekly observations with streams | 2,600 |
| `spotify_top200_positions_2025.csv.gz` | US source-weekly observations with streams | 2,600 |
| `spotify_top200_positions_2026.csv.gz` | US source-weekly observations with streams | 2,199 |

`artist_listeners_daily.csv` is inventoried but excluded: listener figures are not US chart streams. Other personal files and partial downloads are not opened. These are owner-supplied files; the original publisher/version is not established by their filenames. Exact paths, byte sizes, timestamps, checksums, import counts, exclusions, and conflicts are recorded in `local-data/v018-integration/source-manifest.json` and SQLite `integration_files`.

The database has **12,599 US weekly observations**, **2,711 charting tracks**, and **63 reporting dates**, from **2022-01-06 to 2026-10-08**. These are sampled/partial weeks, not continuous historical coverage. The source-weekly stream sum is **42,913,401,825**. Daily and daily-derived weekly streams remain absent rather than being fabricated.

Stable-ID relationships total **346,107 track-to-artist links** and **28,984 album-to-artist links**. There are **705,473 retained URL references**. Source credits remain intact; artist names are not split to infer identities. Additional source metadata, including labels, release dates, listener figures, external-link details, and track URI lists, is retained in `entity_metadata` without converting it into chart observations or merging distinct track IDs.

No supplied file establishes track-to-album membership. Therefore **track-to-album links and album chart rankings remain empty**, although album metadata is preserved. Album names are never used to guess membership. Detail dialogs show bounded, selectable Spotify/artwork URL references without fetching or claiming verified artwork.

There were **0 duplicate observations and 0 conflicts** in the first integration. Two rows were rejected: `albums.csv` row 3904 has an empty album name; the 2026 weekly file row 68823 lacks a required track/artist label. Non-US chart rows are excluded. Repeated observations and metadata relationships are protected by stable keys; conflicting existing records are preserved and reported.

The v0.1.7 ZIP was listed without extraction: it contains an installer, not a standalone SQLite seed. No standalone recovered seed was found in the bounded known locations checked, so no seed migration or executable extraction was attempted.

The persistent database occupies **766,246,912 bytes (730.75 MiB)**. Transactions run per source file, with 2,000-row batches, bounded temporary tables, writer-excluding source handles on Windows, free-space checks, and WAL checkpoints between files. Temporary growth is checked against 3 GiB; no full-database backup copies are made. Source files newer than 60 seconds or held by a writer are skipped. An unchanged completed file is skipped using its recorded size/timestamp and previously calculated SHA-256, without rescanning it.

To add later completed files, run from the repository after setting up the source environment:

```powershell
$env:PYTHONPATH = 'src'
python -m spotify_historical_analytics.local_integration --downloads 'D:\Downloads' --data-dir 'local-data\v018-integration'
```

The workflow recognizes the five metadata schemas and the weekly exports' `cc,week_end,rank,streams,track_id,title,artists,artist_uris` fields. Week end is explicit and must be Thursday; start is six days earlier. Missing streams, invalid IDs/positions, and ambiguous dates do not become observations. A destination containing an existing user database is refused. Other supported daily/weekly formats can use the existing application importers against this isolated database.

Verification: 16 focused integration checks passed; the integrated database returned `quick_check=ok`, no duplicate observation identities, and correct application queries for weekly totals, artist joins, history dates, repeat counts, and Hide Repeats. Unchanged-source skipping was also confirmed on the integrated database. No installer, executable, screenshots, or ZIP were produced; packaging and complete historical coverage remain pending.
