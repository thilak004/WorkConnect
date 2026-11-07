
from db import get_db_connection

with get_db_connection() as connection:
    jobs = connection.execute("""
        SELECT
            jobs.id,
            employers.name AS employer_name,
            jobs.title,
            jobs.skill_required,
            jobs.location,
            jobs.workers_needed,
            jobs.daily_wage,
            jobs.status
        FROM jobs
        JOIN employers ON jobs.employer_id = employers.id
        ORDER BY jobs.id
    """).fetchall()

    print("Total jobs:", len(jobs))

    for job in jobs:
        print(dict(job))
