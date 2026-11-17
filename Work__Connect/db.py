"""PostgreSQL connection management for WorkConnect."""

import os
from contextlib import contextmanager
from datetime import datetime

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row

load_dotenv()


def database_url():
    """Return the configured connection string or raise a configuration error."""
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL is not configured. Set it in the local .env file or "
            "Vercel project environment variables."
        )
    return url


def clean_dict_row(cursor):
    """Custom row factory that converts datetime objects to string format for template safety."""
    dict_factory = dict_row(cursor)
    def make_row(values):
        row = dict_factory(values)
        if row:
            for k, v in row.items():
                if isinstance(v, datetime):
                    row[k] = v.strftime('%Y-%m-%d %H:%M:%S')
        return row
    return make_row


# Module-level connection pool for serverless warm instances.
# Created once per function instance and reused across requests to avoid
# opening/closing a PostgreSQL connection on every invocation.
_connection_pool = None


def _get_connection_pool():
    """Lazily create and cache a connection pool per serverless instance."""
    global _connection_pool
    if _connection_pool is None:
        try:
            from psycopg_pool import ConnectionPool
            _connection_pool = ConnectionPool(
                database_url(),
                min_size=0,
                max_size=3,
                open=False,
                kwargs={"prepare_threshold": None, "connect_timeout": 10},
            )
            _connection_pool.open()
        except ImportError:
            # psycopg_pool not installed; fall back to per-call connections
            _connection_pool = False
    return _connection_pool


@contextmanager
def get_db_connection():
    """Yield a PostgreSQL connection with clean datetime formatting, committing on success and closing."""
    pool = _get_connection_pool()
    if pool is False:
        # Fallback: open and close a connection per call (original behavior)
        connection = psycopg.connect(
            database_url(),
            connect_timeout=10,
            prepare_threshold=None,
            row_factory=clean_dict_row,
        )
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
        return

    connection = pool.connection()
    try:
        connection.row_factory = clean_dict_row
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
