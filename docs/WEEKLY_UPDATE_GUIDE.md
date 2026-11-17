# Weekly update guide: 0.1.8

1. Obtain a completed weekly chart file you are permitted to use. Do not relabel a daily chart as weekly.
2. In **Data Management / Import**, choose **Import Weekly CSV** and select one or multiple CSV, CSV.GZ or XLSX files.
3. Review the per-file result. Each file is fully validated and commits transactionally. Identical observations are skipped. Conflicting or invalid rows block that file without overwriting established observations; other selected files may succeed.

Custom tables require `date,track_name,artist_names,streams,country,track_id,weekly_start,weekly_end`. Use `US`, whole nonnegative streams, and a valid 22-character alphanumeric Spotify track ID (or a supported track URL/URI column). Supply seven inclusive calendar days and an observation date inside that interval; rank, when present, must be a positive integer. General-import synthetic/fallback identifiers are not accepted by this dedicated weekly workflow.

Original Spotify weekly exports with recognized legacy/current headers and an intact `regional-us-weekly-...` filename can supply the market and reporting period without custom boundary columns. A Thursday-ending filename such as `regional-us-weekly-2024-02-08.csv` identifies February 2-8. Recognized explicit Friday/Thursday boundary forms are described in `SUPPORTED_DATA_SCHEMA.md`. Ambiguous or renamed files must provide explicit fields; the app never guesses a week from a category label.

Choose **Source weekly** after import to analyze these counts. **Weekly (from daily)** remains separate and does not merge source-weekly observations. Restarting, updating or reinstalling the app preserves the existing user database and its imported weekly rows. Create a Settings backup when desired; this workflow does not make automatic full-database backup copies.
