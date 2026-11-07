
from db import get_db_connection

with get_db_connection() as connection:
    for table in ("workers", "employers"):
        rows = connection.execute(
            f"SELECT * FROM {table} ORDER BY id"
        ).fetchall()

        print(f"\n--- {table.upper()} ---")
        print(f"Total records: {len(rows)}")

        for row in rows:
            row = dict(row)
            row["password_hash"] = "[redacted]" if row.get("password_hash") else None
            print(row)
