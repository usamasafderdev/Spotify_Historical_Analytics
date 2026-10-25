# Artist and Album Metadata Import

Metadata import uses only user-supplied CSV/XLSX data. The application does not scrape Spotify pages, call restricted endpoints, or infer IDs from names.

## Required identities

Every imported mapping needs a Spotify track ID. Provide at least one of:

- Album ID and Album Title, to create a track-to-album mapping.
- Artist ID, to create a track-to-artist mapping.

To import both types of mappings, provide both sets of columns. You can repeat a track row once per credited artist ID. Do not concatenate artist IDs into one cell.

IDs must be 22 ASCII alphanumeric characters. Spotify track/album/artist URLs and `spotify:track:...` style track URIs are accepted where IDs are read; mappings are stored by the normalized ID. Display-name similarity is never used as a substitute for a stable ID.

## Supported columns

Column names are suggested automatically and can be changed in the import preview.

| Meaning | Suggested column names | Required |
|---|---|---|
| Spotify track ID | `track_id`, `spotify_track_id`, `spotify_id` | Yes |
| Spotify album ID | `album_id`, `spotify_album_id` | For album mappings |
| Album title | `album_name`, `album_title`, `album` | For album mappings |
| Album artist display name | `album_artist`, `album_artists` | Optional |
| Track title | `track_name`, `track_title`, `title` | Optional |
| Spotify artist ID | `artist_id`, `spotify_artist_id` | For artist mappings |
| Artist display name | `artist_name`, `artist` | Optional |
| Release date | `release_date`, `album_release_date` | Optional; normalized to `YYYY-MM-DD` |
| Source identifier | `source_identifier`, `source_id`, `dataset_id` | Optional |

Use a separate Artist ID for each credited artist. `Album Artist` describes album metadata; it does not by itself create a track-to-artist identity mapping.

## Import workflow

1. Open **Settings → Import artist / album metadata**.
2. Select a CSV or XLSX file. The application previews up to 12 rows and suggests column mappings.
3. Confirm or adjust field mappings, enter a source name and license/attribution note, and start import.
4. The import runs on a worker thread with its own SQLite connection. Valid rows, rejected rows, duplicate mappings, and newly created relationship counts are reported.
5. Changes commit in one transaction. An unexpected database error rolls back the metadata batch and all relationships it attempted to add.

Metadata imports can occur before or after chart imports. A mapping imported in advance becomes applicable when matching track IDs exist in chart observations.

## Identity, ambiguity, and editions

- An exact supplied track ID + album ID pair maps a track to an album. Similar titles do not create mappings.
- Different album IDs remain different editions even if their titles match. A track can be mapped to more than one album ID (for example, an album edition and a single/compilation); ranking totals may then overlap across those album rows.
- Re-importing the same pair is idempotent and does not duplicate chart observations or album totals.
- Existing stable IDs with conflicting non-empty names or dates are rejected for review rather than silently overwritten.
- Rows with invalid/missing IDs, incomplete album pairs, or no usable artist/album mapping are rejected and reported.
- Metadata without an Artist ID does not change artist identity. Existing credited artist strings remain intact and are shown as unresolved whole strings; punctuation is never used to guess collaborators.
- An artist ID without a supplied display name is retained and shown as an unlabeled ID.

## Rights and provenance

The source name and license/attribution note are stored with each metadata import batch and applied to imported artist/album records. User-supplied notes do not constitute legal verification. Confirm authorization and redistribution terms independently before commercial use.

## Placeholder example

```csv
track_id,album_id,album_name,album_artist,track_name,artist_id,artist_name,release_date,source_identifier
<22-char track ID>,<22-char album ID>,<album title>,<album artist>,<track title>,<22-char artist ID>,<artist name>,2020-01-02,<source/dataset reference>
```

Placeholder IDs above are instructions only, not chart records or real catalog metadata.
