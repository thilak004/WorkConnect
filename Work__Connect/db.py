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


@contextmanager
def get_db_connection():
    """Yield a PostgreSQL connection with clean datetime formatting, committing on success and closing."""
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
