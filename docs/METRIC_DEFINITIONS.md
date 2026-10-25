# Metric Definitions

## Chart stream totals
These are derived from imported chart observations and are not official Spotify totals unless separately licensed and imported as such.

- `Total available chart streams in selected period`: sum of all valid imported `streams` rows in the selected date range.
- `Distinct charting tracks`: count of unique track identities in the selected range.
- `Distinct credited artists`: count of unique artist identities in the selected range.
- `Chart dates with data`: count of unique chart dates containing at least one valid record.
- `Date coverage percentage`: `(dates_with_data / total_days_in_range) * 100`, using the inclusive selected range and excluding unknown or invalid dates.

## Song rankings
- `Total chart streams`: summed chart-eligible streams for a tracked song in the selected date range.
- `Best chart position`: minimum `position` value for that song across valid rows.
- `Chart appearances`: count of unique chart observations or chart dates where the song appears.
- `Artist charting-song streams`: aggregate of charting-song streams for the artist, using the documented attribution rule.
- `Album charting-track streams`: aggregate of charting-track streams for the album, using the documented mapping rule.

## Important rules
- Daily and weekly chart observations are never mixed in a single metric stack.
- Weekly records must preserve explicit `weekly_start` and `weekly_end` semantics.
- Duplicates are removed by import-time uniqueness constraints and validation.
- Unknown artist or album metadata must not be guessed silently.
- A `DEMO / SYNTHETIC` dataset is excluded from the real-data metrics review and must be visually labeled.
