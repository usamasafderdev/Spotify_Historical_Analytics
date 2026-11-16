# Local development integration

Integrated on 2026-11-16 and updated with album-chart and listener observations in one isolated database:
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
| `charts_albums_weekly.csv` | US weekly album positions; stored separately, no stream counts supplied | 61,588 |
| `artist_listeners_daily.csv` | Artist listener snapshots; stored separately from chart streams | 3,262,204 |

Both new files are owner-supplied; their original publisher/version is not independently established. The album file has 3,040,175 rows across 51 markets, including 61,588 US rows on 308 Thursday reporting dates from 2020-10-22 to 2026-11-12. Its US positions range from 1 to 200 and its 22-character Spotify album IDs are usable. This is structurally consistent with weekly US album chart positions, but the supplied export's authenticity is not independently verified. The file has no `streams` column, so the positions are not converted to stream totals. Of 2,099 distinct US album IDs, 1,896 match existing album metadata. No track-to-album relationships are inferred.

The listener file has 3,262,204 valid rows for 28,135 Spotify artist IDs and 130 observed dates from 2026-06-08 to 2026-11-16; it is not a continuous daily series. All rows are stored as listener metrics, never as chart streams. Of the distinct artist IDs, 26,529 match existing artist metadata; other valid IDs remain identifiable by their supplied IDs. Other personal files and partial downloads are not opened. Exact paths, byte sizes, timestamps, checksums, import counts, coverage, exclusions, and conflicts are recorded in `local-data/v018-integration/source-manifest.json` and SQLite `integration_files`.

Album positions and listener metrics have separate tables and query methods; neither changes song chart observations. The database still has **12,599 US song-weekly observations**, **2,711 charting tracks**, and **63 reporting dates**, from **2022-01-06 to 2026-10-08**. These are sampled/partial weeks, not continuous historical coverage. The song source-weekly stream sum remains **42,913,401,825**. Daily and daily-derived weekly streams remain absent rather than being fabricated.

Stable-ID relationships total **346,107 track-to-artist links** and **28,984 album-to-artist links**. There are **705,473 retained URL references**. Source credits remain intact; artist names are not split to infer identities. Additional source metadata, including labels, release dates, external-link details, and track URI lists, is retained in `entity_metadata` without merging distinct track IDs.

No supplied file establishes track-to-album membership. **Track-to-album links remain empty**; weekly album positions are independently queryable by album ID, date, and rank and are not the stream-based album rankings derived from linked charting tracks. Album names are never used to guess membership. Detail dialogs show bounded, selectable Spotify/artwork URL references without fetching or claiming verified artwork.

The two new sources added **0 duplicate observations, 0 conflicts, and 0 invalid rows**; **2,978,587 non-US album-chart rows** were excluded. The initial integration's two invalid rows remain documented: `albums.csv` row 3904 has an empty album name; the 2026 weekly file row 68823 lacks a required track/artist label. Repeated observations and metadata relationships are protected by stable keys; conflicting existing records are preserved and reported.

The v0.1.7 ZIP was listed without extraction: it contains an installer, not a standalone SQLite seed. No standalone recovered seed was found in the bounded known locations checked, so no seed migration or executable extraction was attempted.

The persistent database now occupies **1,738,084,352 bytes (about 1.62 GiB)**, up from 766,246,912 bytes. Transactions run per source file, with 2,000-row batches, bounded temporary tables, writer-excluding source handles on Windows, free-space checks, and WAL checkpoints between files. Temporary growth is checked against 3 GiB; no full-database backup copies are made. Source files newer than 60 seconds or held by a writer are skipped. An unchanged completed file is skipped using its recorded size/timestamp and previously calculated SHA-256, without rescanning it.

To add later completed files, run from the repository after setting up the source environment:

```powershell
$env:PYTHONPATH = 'src'
python -m spotify_historical_analytics.local_integration --downloads 'D:\Downloads' --data-dir 'local-data\v018-integration'
```

The workflow recognizes the five metadata schemas, song-weekly exports' `cc,week_end,rank,streams,track_id,title,artists,artist_uris` fields, album-weekly position rows, and artist listener snapshots. Song-week end is explicit and must be Thursday; its start is six days earlier. Album positions and listener snapshots use their own tables and queries. Invalid IDs, positions, counts, or dates do not become observations. A destination containing an existing user database is refused. Other supported daily/weekly formats can use the existing application importers against this isolated database.

Verification: 18 focused integration checks passed; the integrated database returned `quick_check=ok`, with 0 duplicate album-chart identities and unchanged song-weekly counts/date coverage. Unchanged-source skipping was confirmed for both new sources. No installer, executable, screenshots, or ZIP were produced; packaging and complete historical coverage remain pending.
