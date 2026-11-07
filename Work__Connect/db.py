"""PostgreSQL connection management for WorkConnect."""

import os
from contextlib import contextmanager

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


@contextmanager
def get_db_connection():
    """Yield a PostgreSQL connection, committing on success and always closing it."""
    connection = psycopg.connect(
        database_url(),
        connect_timeout=10,
        prepare_threshold=None,
        row_factory=dict_row,
    )
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
