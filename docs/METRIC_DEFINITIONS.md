# Metric Definitions

## Chart stream totals
These are derived from imported chart observations and are not official Spotify totals unless separately licensed and imported as such.

- `Total available chart streams in selected period`: sum of all valid imported `streams` rows in the selected date range.
- `Distinct charting tracks`: count of unique track identities in the selected range.
- `Distinct credited artists`: count of unique artist identities in the selected range.
- `Chart dates with data`: count of unique chart dates containing at least one valid record.
- `Observed coverage percentage`: observed chart dates divided by expected reporting intervals in the selected range. Daily data uses inclusive calendar days; weekly data uses seven-day intervals from the chart-date range. With no explicit date range, the observed minimum and maximum chart dates define the range.
- Coverage is descriptive only. It does not establish that the imported source is complete, that every reporting date was expected, or that unavailable dates had zero streams.

## Song rankings
- `Total chart streams`: summed chart-eligible streams for a tracked song in the selected date range.
- `Best chart position`: minimum `position` value for that song across valid rows.
- `Chart appearances`: count of unique chart dates where the song appears. For weekly charts, each chart date represents a weekly chart observation; period start/end columns are retained when available.
- `Artist charting-song streams`: aggregate of charting-song streams assigned to a supplied artist ID, or to an unresolved exact credited-artist string when no ID mapping is present.
- Stable-ID artist attribution is full credit per mapped track to each supplied artist ID. Collaborations with multiple mapped IDs can therefore make artist totals overlap; artist totals must not be summed as if they were unique chart streams.
- Credited strings without IDs are retained whole. Commas, ampersands, and other text are not split. A known artist ID is not guessed from a display name.
- `Album charting-track streams`: sum of chart-record stream rows whose stable track ID is mapped to the stable album ID by user-supplied metadata. It is not a comprehensive album total from Spotify.
- Album editions with distinct album IDs remain separate. A charting track may legitimately be mapped to more than one edition, so totals across editions may overlap.
- Album observations without a stable track-to-album mapping are excluded from album rankings.

## Important rules
- Daily and weekly chart observations are never mixed in a single metric stack.
- Weekly records must preserve explicit `weekly_start` and `weekly_end` semantics.
- Duplicates are removed by import-time validation and database uniqueness rules. Imports without a position column use explicit duplicate matching as well.
- Track IDs are the preferred identity; title and credited artist are used as the conservative fallback when an ID is unavailable.
- Unknown artist or album metadata must not be guessed silently.
- A `DEMO / SYNTHETIC` dataset is excluded from the real-data metrics review and must be visually labeled.
- The synthetic preview uses a separate temporary SQLite database. Synthetic values are visible only while explicitly in demo mode and are never merged into production queries, backups, or exports.
- Rankings exports use the same USA/chart/date/search ranking query and selected Top 50/100/200 limit as the on-screen result set. Exports include the metric definition, active date interval, chart type, observed coverage, and overlapping real source names and attribution notes.
- Exported artist values preserve full-credit attribution and may overlap across collaborators. Exported album metrics remain charting-track streams, not official or comprehensive album totals.
- Exported coverage is observed coverage only; it does not verify that a source is complete. Empty ranking exports include metadata and headers but have no ranking data rows.
- Text values beginning with spreadsheet formula characters are escaped as text in CSV and XLSX exports.
