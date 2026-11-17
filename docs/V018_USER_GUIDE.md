# US Music Charts Analytics 0.1.8: user guide

This INTERNAL-READY build contains owner-supplied US historical observations, not a certified complete Spotify history. See the accompanying coverage summary and source manifest. Data authenticity and external distribution authorization are not independently established.

## Navigate and filter

The sidebar contains Overview, Top Songs, Top Artists, Top Albums, Data Sources & Coverage, Data Management / Import, and Settings. Select a chart source, date range and **Apply**. Search ranking pages, select Top 50/100/200, and sort by a table heading. Export the active ranking to CSV or XLSX.

- **Daily:** actual imported US daily song chart streams.
- **Source weekly:** the supplied weekly stream counts, kept separate from daily data.
- **Weekly (from daily):** Monday-Sunday sums of observed daily rows, reported on Sunday. Missing dates stay missing; partial weeks remain partial.

Double-click a song for its history and references. Graphs use actual reporting dates with gaps and a zero lower stream axis; hover gives the observation date and value. Stream totals describe charting observations only, never platform-wide listening.

Artist stream rankings use exact supplied track-to-artist IDs. Collaborators receive full credit, so their totals can overlap. Album stream rankings require exact track-to-album links; absent membership is not inferred from names. This seed has no supplied track-to-album membership.

## Chart showings and separate source metrics

Open **Chart showings** on Songs, Artists, or Albums. In **Source**, choose track-derived streams, **US daily artist positions**, **US weekly album positions**, or **Artist listener snapshots** where offered. Album/artist source positions are actual rankings, not manufactured stream totals. Listener snapshots are a separate metric and need not form a continuous daily series. Position/listener sources use their own fixed cadence and the selected date/search filters, independently of the page's track-stream cadence.

Repeat indicators count all eligible reporting dates per stable entity before Top N. **Hide Repeats** in Chart showings retains one representative per entity according to the selected sort. The list limit applies after deduplication. Turning it off shows additional appearances. This changes display only: aggregated rankings, totals, and stored rows remain unchanged. Unknown-ID credit groups remain available in aggregate rankings rather than asserting stable artist identity.

## Imports, exports and safety

Use **Import Weekly CSV** for one or multiple CSV, CSV.GZ, or XLSX weekly updates; see `WEEKLY_UPDATE_GUIDE.md`. The general **Import Dataset** workflow handles compatible local tables and creates a pre-import backup; weekly updates use transactional conflict protection without automatically copying the whole database. Settings also provides backups and validated restore. Retain backups outside the application folder.

CSV/XLSX exports follow the selected ranking, dates, source and limit. Keep coverage/definition information with a report. Importing or exporting a file does not confer acquisition, commercial-use, analysis or redistribution rights.
