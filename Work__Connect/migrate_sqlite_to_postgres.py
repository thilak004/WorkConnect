"""Copy WorkConnect's SQLite data into an already-created PostgreSQL schema."""

import argparse
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

import psycopg
from psycopg import sql

from db import get_db_connection


TABLES_IN_DEPENDENCY_ORDER = (
    "employers",
    "workers",
    "jobs",
    "applications",
    "saved_jobs",
    "interviews",
    "notifications",
    "reports",
)
BATCH_SIZE = 500
TIMESTAMP_COLUMNS = {"created_at", "applied_at", "saved_at"}


def _sqlite_identifier(name):
    if not name.replace("_", "").isalnum() or not name[0].isalpha():
        raise ValueError(f"Unexpected SQLite identifier: {name!r}")
    return '"' + name.replace('"', '""') + '"'


def _postgres_value(column, value):
    if value is None or column not in TIMESTAMP_COLUMNS:
        return value
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _get_source_tables(connection):
    return {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' "
            "AND name NOT LIKE 'sqlite_%'"
        )
    }


def migrate(sqlite_path):
    """Migrate all recognized records while preserving IDs and source data."""
    source_path = Path(sqlite_path).resolve()
    if not source_path.is_file():
        raise FileNotFoundError(f"SQLite database not found: {source_path}")

    source_uri = f"file:{source_path.as_posix()}?mode=ro"
    source = sqlite3.connect(source_uri, uri=True)
    source.row_factory = sqlite3.Row
    current_table = None
    try:
        source_tables = _get_source_tables(source)
        missing_tables = set(TABLES_IN_DEPENDENCY_ORDER) - source_tables
        unexpected_tables = source_tables - set(TABLES_IN_DEPENDENCY_ORDER)
        if missing_tables or unexpected_tables:
            raise ValueError(
                "SQLite table inventory does not match the reviewed WorkConnect "
                f"schema. Missing: {sorted(missing_tables)}; "
                f"unexpected: {sorted(unexpected_tables)}"
            )

        source_columns = {}
        for table in TABLES_IN_DEPENDENCY_ORDER:
            source_columns[table] = [
                row["name"]
                for row in source.execute(
                    f"PRAGMA table_info({_sqlite_identifier(table)})"
                )
            ]

        migrated_rows = {}
        with get_db_connection() as destination:
            destination_columns = {}
            for table in TABLES_IN_DEPENDENCY_ORDER:
                rows = destination.execute(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = current_schema() AND table_name = %s
                    """,
                    (table,),
                ).fetchall()
                destination_columns[table] = {row["column_name"] for row in rows}

            for table in TABLES_IN_DEPENDENCY_ORDER:
                source_set = set(source_columns[table])
                target_set = destination_columns[table]
                if not target_set:
                    raise RuntimeError(
                        f"Destination table {table!r} is missing; apply schema.sql first."
                    )
                if source_set != target_set:
                    raise RuntimeError(
                        f"Column mismatch for {table!r}; SQLite has "
                        f"{sorted(source_set)}, PostgreSQL has {sorted(target_set)}."
                    )

            for table in TABLES_IN_DEPENDENCY_ORDER:
                current_table = table
                columns = source_columns[table]
                quoted_columns = sql.SQL(", ").join(
                    sql.Identifier(column) for column in columns
                )
                placeholders = sql.SQL(", ").join(
                    sql.Placeholder() for _ in columns
                )
                insert = sql.SQL(
                    "INSERT INTO {} ({}) VALUES ({}) ON CONFLICT DO NOTHING"
                ).format(
                    sql.Identifier(table),
                    quoted_columns,
                    placeholders,
                )

                before = destination.execute(
                    sql.SQL("SELECT COUNT(*) AS count FROM {}").format(
                        sql.Identifier(table)
                    )
                ).fetchone()["count"]
                source_cursor = source.execute(
                    f"SELECT * FROM {_sqlite_identifier(table)}"
                )
                while True:
                    batch = source_cursor.fetchmany(BATCH_SIZE)
                    if not batch:
                        break
                    with destination.cursor() as cursor:
                        cursor.executemany(
                            insert,
                            [
                                tuple(
                                    _postgres_value(column, row[column])
                                    for column in columns
                                )
                                for row in batch
                            ],
                        )

                destination.execute(
                    sql.SQL(
                        """
                        SELECT setval(
                            pg_get_serial_sequence(%s, 'id'),
                            COALESCE(MAX(id), 1),
                            MAX(id) IS NOT NULL
                        )
                        FROM {}
                        """
                    ).format(sql.Identifier(table)),
                    (table,),
                )
                after = destination.execute(
                    sql.SQL("SELECT COUNT(*) AS count FROM {}").format(
                        sql.Identifier(table)
                    )
                ).fetchone()["count"]
                migrated_rows[table] = {
                    "source": source.execute(
                        f"SELECT COUNT(*) FROM {_sqlite_identifier(table)}"
                    ).fetchone()[0],
                    "inserted": after - before,
                }
    except Exception as error:
        if isinstance(error, (FileNotFoundError, ValueError, RuntimeError)):
            raise
        raise RuntimeError(
            f"SQLite-to-PostgreSQL migration failed while processing "
            f"{current_table or 'schema validation'}. PostgreSQL changes were "
            f"rolled back and the source file was opened read-only: {error}"
        ) from error
    finally:
        source.close()

    print(f"Migration completed from read-only source: {source_path}")
    for table, counts in migrated_rows.items():
        print(
            f"  {table}: {counts['inserted']} inserted "
            f"({counts['source']} source rows; existing conflicts skipped)"
        )
    return migrated_rows


def main():
    parser = argparse.ArgumentParser(
        description="Copy WorkConnect records from SQLite to PostgreSQL."
    )
    parser.add_argument(
        "--sqlite",
        default=str(Path(__file__).resolve().parent / "workconnect.db"),
        help="Path to the existing SQLite database (read-only).",
    )
    args = parser.parse_args()

    try:
        migrate(args.sqlite)
    except (
        FileNotFoundError,
        RuntimeError,
        ValueError,
        sqlite3.Error,
        psycopg.Error,
    ) as error:
        print(f"Migration failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
