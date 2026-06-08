"""Convert a SQLite schema into detector column descriptors."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any


def sample_sqlite_schema(
    db_path: str | Path,
    sample_size: int = 3,
) -> list[dict[str, Any]]:
    path = Path(db_path)
    descriptors: list[dict[str, Any]] = []

    with sqlite3.connect(path) as connection:
        table_names = _table_names(connection)
        for table_name in table_names:
            for column in connection.execute(f'PRAGMA table_info("{table_name}")'):
                _cid, column_name, data_type, not_null, _default, _pk = column
                samples = _sample_values(connection, table_name, column_name, sample_size)
                descriptors.append(
                    {
                        "table_name": table_name.upper(),
                        "column_name": column_name,
                        "data_type": data_type or "UNKNOWN",
                        "sample_values": samples,
                        "nullable": not bool(not_null),
                    }
                )

    return descriptors


def _table_names(connection: sqlite3.Connection) -> list[str]:
    rows = connection.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name NOT LIKE 'sqlite_%'
        ORDER BY name
        """
    )
    return [row[0] for row in rows]


def _sample_values(
    connection: sqlite3.Connection,
    table_name: str,
    column_name: str,
    sample_size: int,
) -> list[str]:
    rows = connection.execute(
        f'''
        SELECT "{column_name}"
        FROM "{table_name}"
        WHERE "{column_name}" IS NOT NULL
        LIMIT ?
        ''',
        (sample_size,),
    )
    return [str(row[0]) for row in rows]

