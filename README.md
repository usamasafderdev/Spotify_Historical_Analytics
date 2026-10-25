# Spotify Historical Analytics

A local Windows desktop application for analyzing user-supplied US music chart CSV/XLSX observations. Metrics are derived only from imported rows; they are not official platform totals and do not imply complete historical coverage.

## Setup

Requires Python 3.12 or newer.

```powershell
python -m pip install -e .
```

## Launch

```powershell
python -m spotify_historical_analytics
```

## Dashboard

- Overview KPIs and interactive PyQtGraph charts for real imported daily or weekly observations.
- Shared chart-type and inclusive date filters, with last 7/30/90 days and last-year presets.
- Top Songs rankings with search, sorting, top 50/100/200 selection, and a double-click detail view.
- Credited-artist aggregates, source inventory, annual observation counts, missing-date inspection, and local database backup.
- CSV and XLSX import with validation and duplicate reporting.
- Synthetic demo rows are labeled and excluded from real-data KPIs, rankings, and charts.

## Tests

```powershell
python -m pytest -q
```

The tests include an offscreen Qt widget/navigation smoke test. It does not replace visual verification in a normal Windows desktop session.

See [docs/PHASE_2_IMPLEMENTATION.md](docs/PHASE_2_IMPLEMENTATION.md) for behavior and limitations.
