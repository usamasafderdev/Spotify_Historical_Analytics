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
- `Artist charting-song streams`: aggregate of charting-song streams for the artist, using the documented attribution rule.
- `Album charting-track streams`: aggregate of charting-track streams for the album, using the documented mapping rule.

## Important rules
- Daily and weekly chart observations are never mixed in a single metric stack.
- Weekly records must preserve explicit `weekly_start` and `weekly_end` semantics.
- Duplicates are removed by import-time validation and database uniqueness rules. Imports without a position column use explicit duplicate matching as well.
- Track IDs are the preferred identity; title and credited artist are used as the conservative fallback when an ID is unavailable.
- Unknown artist or album metadata must not be guessed silently.
- A `DEMO / SYNTHETIC` dataset is excluded from the real-data metrics review and must be visually labeled.
