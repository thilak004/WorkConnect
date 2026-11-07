
from db import get_db_connection

with get_db_connection() as connection:
    rows = connection.execute("""
        SELECT
            a.id,
            w.name,
            j.title,
            a.status,
            a.applied_at
        FROM applications AS a
        JOIN workers AS w ON a.worker_id = w.id
        JOIN jobs AS j ON a.job_id = j.id
    """).fetchall()

    if rows:
        for row in rows:
            print("Application ID:", row["id"])
            print("Worker:", row["name"])
            print("Job:", row["title"])
            print("Status:", row["status"])
            print("Applied at:", row["applied_at"])
            print("-" * 30)
    else:
        print("No applications found.")
