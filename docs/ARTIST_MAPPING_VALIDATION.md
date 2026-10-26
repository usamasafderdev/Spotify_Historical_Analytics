# Artist Mapping Validation

## Method

- Stable track and artist IDs are the preferred identity keys.
- MGD+ song metadata uses the verified `song_id` and `artist_id` columns. The adapter parses an explicit list of artist IDs and preserves each distinct credited ID; it does not split artist display strings.
- A track can have multiple credited artists. Each supplied artist receives full credit for that track's chart streams. Collaborator totals overlap and are not additive.
- A missing artist ID remains unresolved. Names are not used to guess an ID.
- Derived artist totals must be traceable to the source chart observations and exact track-to-artist mapping records.
- Aggregations must avoid expanding one chart observation into multiple counted chart observations. Many-to-many artist joins represent attribution, not unique market streams.

## Automated fixture coverage

The synthetic adapter tests cover:

- Exact MGD+ `song_id` / `artist_id` mapping.
- Multiple credited artist IDs on one track.
- Chunk boundaries while reading metadata.
- Dhruvil IDs extracted only from a verified Spotify track URL.
- No mappings inferred from a display-name string.
- Viral 50 rows do not contribute streams.

Fixtures are generated locally and contain no source archive records.

## Known research metadata facts

Prior MGD+ archive validation found 9,589 chart track IDs mapped to artist metadata, 2,061 distinct artist IDs, and 3,690 tracks with multiple artist credits. These are research-only audit findings, not production metadata and not rights approval. No MGD+ album mappings were found.

## Production reporting

The Data Sources & Coverage table reports unique chart track IDs and counts of those IDs with exact, `id_match` artist or album metadata. A zero mapping count means no such verified metadata mapping is present in the production database; it is not evidence that the corresponding artists or albums do not exist.
