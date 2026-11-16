from __future__ import annotations

from ..db import DatabaseManager


def entity_references(db: DatabaseManager, kind: str, identifier: str) -> list[dict]:
    if not db.connection.execute("SELECT 1 FROM sqlite_master WHERE name='entity_references'").fetchone():
        return []
    return [dict(row) for row in db.connection.execute(
        "SELECT reference_type,url FROM entity_references WHERE entity_type=? AND entity_id=? ORDER BY reference_type,url LIMIT 3",
        (kind, identifier),
    )]
