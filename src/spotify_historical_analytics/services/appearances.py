from __future__ import annotations

from ..db import DatabaseManager


SORT_ORDERS = {
    "streams": "streams DESC, chart_date DESC, entity_id ASC",
    "position": "position IS NULL, position ASC, streams DESC, chart_date DESC, entity_id ASC",
    "newest": "chart_date DESC, streams DESC, entity_id ASC",
    "oldest": "chart_date ASC, streams DESC, entity_id ASC",
}


def chart_showings(
    db: DatabaseManager, category: str, start_date: str | None = None,
    end_date: str | None = None, chart_type: str = "daily", search: str = "",
    limit: int = 50, hide_repeats: bool = False, sort: str = "streams",
    include_demo: bool = False,
) -> list[dict]:
    db.validate_date_range(start_date, end_date)
    if sort not in SORT_ORDERS or limit < 1:
        raise ValueError("Choose a supported sort and a positive list limit.")
    definitions = {
        "songs": ("c.track_id", "c.track_name", "c.artist_names", "", "c.track_id IS NOT NULL AND instr(c.track_id, '|') = 0"),
        "artists": (
            "entity.artist_id", "entity.artist_name", "entity.artist_id",
            "JOIN (SELECT DISTINCT track_id, artist_id FROM track_artists WHERE mapping_status='id_match') mapping ON mapping.track_id=c.track_id JOIN artists entity ON entity.artist_id=mapping.artist_id",
            "1=1",
        ),
        "albums": (
            "entity.album_id", "entity.album_name", "COALESCE(entity.album_artist, '')",
            "JOIN track_albums mapping ON mapping.track_id=c.track_id AND mapping.mapping_status='id_match' JOIN albums entity ON entity.album_id=mapping.album_id",
            "1=1",
        ),
    }
    if category not in definitions:
        raise ValueError("Unsupported chart-showings category.")
    identity, label, secondary, joins, identity_filter = definitions[category]
    order = SORT_ORDERS[sort]
    query = f"""
        WITH eligible AS (
            SELECT {identity} AS entity_id, MIN({label}) AS entity_name,
                c.chart_date, SUM(c.streams) AS streams, MIN(c.position) AS position
            FROM analytics_records c {joins}
            WHERE c.country='US' AND c.chart_type=?
                AND (? OR c.source <> 'DEMO / SYNTHETIC')
                AND (? IS NULL OR c.chart_date >= ?) AND (? IS NULL OR c.chart_date <= ?)
                AND {identity_filter}
                AND (? = '' OR {label} LIKE ? OR {secondary} LIKE ? OR {identity} LIKE ?)
            GROUP BY {identity}, c.chart_date
        ), counted AS (
            SELECT *, COUNT(*) OVER (PARTITION BY entity_id) AS chart_appearances,
                ROW_NUMBER() OVER (PARTITION BY entity_id ORDER BY {order}) AS representative
            FROM eligible
        )
        SELECT entity_id, entity_name, chart_date, streams, position, chart_appearances
        FROM counted WHERE (? = 0 OR representative = 1)
        ORDER BY {order} LIMIT ?
    """
    pattern = f"%{search}%"
    parameters = [chart_type, include_demo, start_date, start_date, end_date, end_date,
                  search, pattern, pattern, pattern, hide_repeats, limit]
    return [dict(row) for row in db.connection.execute(query, parameters)]
