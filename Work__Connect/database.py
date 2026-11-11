from pathlib import Path

from werkzeug.security import generate_password_hash, check_password_hash

from db import get_db_connection


def initialize_database():
    """Apply the checked-in PostgreSQL schema to the configured database."""
    schema_path = Path(__file__).resolve().parent / "schema.sql"
    schema = schema_path.read_text(encoding="utf-8")
    with get_db_connection() as connection:
        for statement in schema.split(";"):
            if statement.strip():
                connection.execute(statement)


def compute_match_score(worker, job, lang="en"):
    """
    Intelligent Matching Engine (Step 7):
    Calculates a 0-100 match score based on 6 key dimensions:
    1. Skill match (up to 35 pts) - required skill vs worker skill
    2. Location match (up to 20 pts) - proximity and locality match
    3. Experience match (up to 15 pts) - years of experience
    4. Wage compatibility (up to 15 pts) - worker expected wage vs job daily wage
    5. Availability match (up to 10 pts) - worker readiness
    6. Rating score (up to 5 pts) - worker track record & feedback

    Also provides multilingual explanations in English (en), Telugu (te), and Hindi (hi).
    """
    w = dict(worker) if hasattr(worker, "keys") else worker
    j = dict(job) if hasattr(job, "keys") else job
    lang = lang if lang in ("en", "te", "hi") else "en"

    reasons = []

    # 1. Skill Match (Max: 35 pts)
    w_skill = (w.get("skill") or "").strip().lower()
    j_skill = (j.get("skill_required") or "").strip().lower()
    j_title = (j.get("title") or "").strip().lower()
    j_desc = (j.get("description") or "").strip().lower()

    if w_skill and j_skill:
        if w_skill == j_skill:
            skill_score = 35.0
            skill_desc = "Exact skill match"
            if lang == "te":
                reasons.append(f"✓ మీ వృత్తికి సరిగ్గా సరిపోతుంది ({w.get('skill')})")
            elif lang == "hi":
                reasons.append(f"✓ आपके हुनर से बिल्कुल मेल खाता है ({w.get('skill')})")
            else:
                reasons.append(f"✓ Exact skill match ({w.get('skill')})")
        elif w_skill in j_skill or j_skill in w_skill:
            skill_score = 25.0
            skill_desc = "Strong skill overlap"
            if lang == "te":
                reasons.append("✓ సంబంధిత వృత్తి నైపుణ్యం ఉంది")
            elif lang == "hi":
                reasons.append("✓ कार्य से संबंधित मजबूत हुनर")
            else:
                reasons.append("✓ Strong trade skill relevance")
        elif w_skill in j_title or w_skill in j_desc:
            skill_score = 18.0
            skill_desc = "Skill mentioned in job description"
            if lang == "te":
                reasons.append("✓ పని వివరాలలో మీ నైపుణ్యం అవసరం ఉంది")
            elif lang == "hi":
                reasons.append("✓ काम के विवरण में आपके हुनर की मांग")
            else:
                reasons.append("✓ Skill aligns with job requirements")
        else:
            skill_score = 0.0
            skill_desc = "Skill mismatch"
    else:
        skill_score = 10.0
        skill_desc = "General skill"

    # 2. Location Match (Max: 20 pts)
    w_loc = (w.get("location") or "").strip().lower()
    j_loc = (j.get("location") or "").strip().lower()

    if w_loc and j_loc:
        if w_loc == j_loc:
            loc_score = 20.0
            loc_desc = "Exact location match"
            if lang == "te":
                reasons.append(f"✓ మీ సొంత ఊరు లేదా ప్రాంతంలోనే పని ({w.get('location')})")
            elif lang == "hi":
                reasons.append(f"✓ आपके अपने स्थान पर ही काम उपलब्ध ({w.get('location')})")
            else:
                reasons.append(f"✓ Same locality ({w.get('location')})")
        elif w_loc in j_loc or j_loc in w_loc:
            loc_score = 12.0
            loc_desc = "Same region / neighboring area"
            if lang == "te":
                reasons.append("✓ దగ్గర ప్రాంతంలో అందుబాటులో ఉన్న పని")
            elif lang == "hi":
                reasons.append("✓ नजदीकी क्षेत्र में काम उपलब्ध")
            else:
                reasons.append("✓ Neighboring region")
        else:
            loc_score = 0.0
            loc_desc = "Different location"
    else:
        loc_score = 5.0
        loc_desc = "Location flexible"

    # 3. Experience Match (Max: 15 pts)
    try:
        exp = int(w.get("experience") or 0)
    except (TypeError, ValueError):
        exp = 0

    if exp >= 5:
        exp_score = 15.0
        exp_desc = f"Expert ({exp} yrs exp)"
        if lang == "te":
            reasons.append(f"✓ {exp} ఏళ్ల నిపుణత అనుభవం")
        elif lang == "hi":
            reasons.append(f"✓ {exp} वर्षों का विशेषज्ञ अनुभव")
        else:
            reasons.append(f"✓ Expert track record ({exp} yrs)")
    elif exp >= 3:
        exp_score = 13.0
        exp_desc = f"Experienced ({exp} yrs exp)"
        if lang == "te":
            reasons.append(f"✓ {exp} ఏళ్ల చక్కని అనుభవం")
        elif lang == "hi":
            reasons.append(f"✓ {exp} वर्षों का अच्छा अनुभव")
        else:
            reasons.append(f"✓ Experienced worker ({exp} yrs)")
    elif exp >= 1:
        exp_score = 10.0
        exp_desc = f"Competent ({exp} yrs exp)"
        if lang == "te":
            reasons.append(f"✓ {exp} సంవత్సరం పని అనుభవం")
        elif lang == "hi":
            reasons.append(f"✓ {exp} वर्ष का व्यावहारिक अनुभव")
        else:
            reasons.append(f"✓ Competent ({exp} yr exp)")
    else:
        exp_score = 6.0
        exp_desc = "Entry-level / Fresher"

    # 4. Wage Compatibility (Max: 15 pts)
    try:
        w_wage = int(w.get("wage") or 0)
        j_wage = int(j.get("daily_wage") or 0)
    except (TypeError, ValueError):
        w_wage = 0
        j_wage = 0

    if j_wage > 0 and w_wage > 0:
        if w_wage <= j_wage:
            wage_score = 15.0
            wage_desc = f"Within budget (₹{w_wage} ≤ ₹{j_wage})"
            if lang == "te":
                reasons.append(f"✓ ఆశించిన కూలీ (₹{w_wage}) కన్నా ఎక్కువ లేదా సమానం (₹{j_wage})")
            elif lang == "hi":
                reasons.append(f"✓ अपेक्षित मजदूरी (₹{w_wage}) से बराबर या बेहतर (₹{j_wage})")
            else:
                reasons.append(f"✓ Offered wage meets or exceeds expected (₹{w_wage} ≤ ₹{j_wage})")
        elif w_wage <= j_wage * 1.2:
            wage_score = 8.0
            wage_desc = f"Close to budget (within 20%)"
        else:
            wage_score = 2.0
            wage_desc = f"Expected wage exceeds offer (₹{w_wage} > ₹{j_wage})"
    else:
        wage_score = 10.0
        wage_desc = "Flexible wage"

    # 5. Availability (Max: 10 pts)
    avail = str(w.get("availability") or "Immediate").strip().lower()
    if "immediate" in avail or "available" in avail:
        avail_score = 10.0
        avail_desc = "Immediately available"
        if lang == "te":
            reasons.append("✓ వెంటనే చేరడానికి సిద్ధంగా ఉన్నారు")
        elif lang == "hi":
            reasons.append("✓ तुरंत काम शुरू करने के लिए उपलब्ध")
        else:
            reasons.append("✓ Ready to join immediately")
    elif "week" in avail or "within" in avail:
        avail_score = 7.0
        avail_desc = "Available within 1 week"
    elif "part" in avail:
        avail_score = 6.0
        avail_desc = "Part-time availability"
    else:
        avail_score = 5.0
        avail_desc = "Standard availability"

    # 6. Rating (Max: 5 pts)
    try:
        w_rating = w.get("rating")
        if w_rating is not None:
            rating = min(5.0, max(1.0, float(w_rating)))
            rating_score = round((rating / 5.0) * 5.0, 1)
            rating_desc = f"{rating:.1f}/5.0 rating"
        else:
            rating_score = 0.0
            rating_desc = "Not rated yet"
            rating = None
    except (TypeError, ValueError):
        rating_score = 0.0
        rating_desc = "Not rated yet"
        rating = None

    # Total Score Calculation
    total_score = round(skill_score + loc_score + exp_score + wage_score + avail_score + rating_score, 1)
    percentage = int(min(100, max(0, round(total_score))))

    if percentage >= 85:
        level = "Excellent Match"
        badge_class = "match-excellent"
    elif percentage >= 70:
        level = "Good Match"
        badge_class = "match-good"
    elif percentage >= 50:
        level = "Moderate Match"
        badge_class = "match-moderate"
    else:
        level = "Low Match"
        badge_class = "match-low"

    return {
        "score": total_score,
        "percentage": percentage,
        "level": level,
        "badge_class": badge_class,
        "reasons": reasons,
        "explanation": " • ".join(reasons) if reasons else "Profile reviewed for compatibility.",
        "breakdown": {
            "skills": {"score": skill_score, "max": 35, "desc": skill_desc},
            "location": {"score": loc_score, "max": 20, "desc": loc_desc},
            "experience": {"score": exp_score, "max": 15, "desc": exp_desc, "years": exp},
            "wage": {"score": wage_score, "max": 15, "desc": wage_desc, "worker_wage": w_wage, "job_wage": j_wage},
            "availability": {"score": avail_score, "max": 10, "desc": avail_desc},
            "rating": {"score": rating_score, "max": 5, "desc": rating_desc, "rating": rating}
        }
    }


def recalculate_job_positions(job_id, connection=None):
    """
    Recalculate remaining positions for a job based on Confirmed applications.
    Updates the jobs table:
    - positions_remaining = max(0, workers_needed - count_confirmed)
    - status = 'Filled' if positions_remaining == 0 else 'Open'
    """
    if connection is None:
        with get_db_connection() as owned_connection:
            return recalculate_job_positions(job_id, owned_connection)

    cursor = connection.cursor()
    job_row = cursor.execute(
        "SELECT workers_needed FROM jobs WHERE id = %s", (job_id,)
    ).fetchone()

    if not job_row:
        return None

    needed = job_row["workers_needed"]
    confirmed_count = cursor.execute(
        """
        SELECT COUNT(*) AS count FROM applications
        WHERE job_id = %s AND status IN ('Confirmed', 'Accepted')
        """,
        (job_id,)
    ).fetchone()["count"]

    remaining = max(0, needed - confirmed_count)
    new_status = 'Filled' if remaining == 0 else 'Open'

    cursor.execute(
        """
        UPDATE jobs
        SET positions_remaining = %s, status = %s
        WHERE id = %s
        """,
        (remaining, new_status, job_id)
    )

    return {
        "job_id": job_id,
        "workers_needed": needed,
        "confirmed_count": confirmed_count,
        "positions_remaining": remaining,
        "status": new_status
    }


def get_all_workers():
    """Return all workers as a list of dicts."""
    with get_db_connection() as connection:
        rows = connection.execute("SELECT * FROM workers ORDER BY id").fetchall()
        return [dict(r) for r in rows]


def get_worker_by_email(email):
    """Return a worker by email (or None)."""
    with get_db_connection() as connection:
        row = connection.execute(
            "SELECT * FROM workers WHERE email = %s", (email.strip().lower(),)
        ).fetchone()
        return dict(row) if row else None


def get_worker_by_id(worker_id):
    """Return a worker by ID (or None)."""
    with get_db_connection() as connection:
        row = connection.execute(
            "SELECT * FROM workers WHERE id = %s", (worker_id,)
        ).fetchone()
        return dict(row) if row else None


def get_all_employers():
    """Return all employers as a list of dicts."""
    with get_db_connection() as connection:
        rows = connection.execute("SELECT * FROM employers ORDER BY id").fetchall()
        return [dict(r) for r in rows]


def get_employer_by_email(email):
    """Return an employer by email (or None)."""
    with get_db_connection() as connection:
        row = connection.execute(
            "SELECT * FROM employers WHERE email = %s", (email.strip().lower(),)
        ).fetchone()
        return dict(row) if row else None


def get_employer_by_id(employer_id):
    """Return an employer by ID (or None)."""
    with get_db_connection() as connection:
        row = connection.execute(
            "SELECT * FROM employers WHERE id = %s", (employer_id,)
        ).fetchone()
        return dict(row) if row else None


def get_job_by_id(job_id):
    """Return a single job by ID with employer details (or None)."""
    with get_db_connection() as connection:
        row = connection.execute(
            """
            SELECT jobs.*, employers.name AS employer_name, employers.phone AS employer_phone, employers.email AS employer_email
            FROM jobs
            JOIN employers ON jobs.employer_id = employers.id
            WHERE jobs.id = %s
            """,
            (job_id,),
        ).fetchone()
        return dict(row) if row else None


def get_all_jobs(status_filter="Open", search_query=None, skill_filter=None,
                 location_filter=None, max_wage=None, worker_email=None, sort_by=None):
    """
    Return jobs matching filters, with intelligent matching if worker_email is provided.
    Supports search by keyword, skill, location, wage, and intelligent match sorting.
    """
    with get_db_connection() as connection:
        
        query = """
            SELECT
                jobs.*,
                employers.name AS employer_name,
                employers.phone AS employer_phone,
                (SELECT COUNT(*) FROM applications WHERE job_id = jobs.id AND status IN ('Confirmed', 'Accepted')) AS confirmed_count
            FROM jobs
            JOIN employers ON jobs.employer_id = employers.id
            WHERE 1=1
        """
        params = []

        if status_filter:
            query += " AND jobs.status = %s"
            params.append(status_filter)

        if skill_filter and skill_filter.strip():
            query += " AND LOWER(jobs.skill_required) LIKE %s"
            params.append(f"%{skill_filter.strip().lower()}%")

        if location_filter and location_filter.strip():
            query += " AND LOWER(jobs.location) LIKE %s"
            params.append(f"%{location_filter.strip().lower()}%")

        if max_wage:
            try:
                max_wage_val = int(max_wage)
                query += " AND jobs.daily_wage <= %s"
                params.append(max_wage_val)
            except ValueError:
                pass

        if search_query and search_query.strip():
            search_term = f"%{search_query.strip().lower()}%"
            query += " AND (LOWER(jobs.title) LIKE %s OR LOWER(jobs.description) LIKE %s OR LOWER(jobs.skill_required) LIKE %s OR LOWER(jobs.location) LIKE %s)"
            params.extend([search_term, search_term, search_term, search_term])

        query += " ORDER BY jobs.id DESC"
        raw_jobs = [dict(r) for r in connection.execute(query, params).fetchall()]

    # If worker is specified, compute match score for every job
    worker = None
    if worker_email:
        worker = get_worker_by_email(worker_email)

    for j in raw_jobs:
        if "positions_remaining" not in j or j["positions_remaining"] is None:
            j["positions_remaining"] = max(0, j["workers_needed"] - j["confirmed_count"])

        if worker:
            match = compute_match_score(worker, j)
            j["match_score"] = match["score"]
            j["match_percentage"] = match["percentage"]
            j["match_level"] = match["level"]
            j["match_badge_class"] = match["badge_class"]
            j["match_breakdown"] = match["breakdown"]
        else:
            j["match_score"] = None
            j["match_percentage"] = None
            j["match_level"] = None
            j["match_badge_class"] = None
            j["match_breakdown"] = None

    # Sorting
    if sort_by == "match" and worker:
        raw_jobs.sort(key=lambda x: (x["match_score"] or 0), reverse=True)
    elif sort_by == "wage_desc":
        raw_jobs.sort(key=lambda x: x["daily_wage"], reverse=True)
    elif sort_by == "wage_asc":
        raw_jobs.sort(key=lambda x: x["daily_wage"])
    elif sort_by == "positions":
        raw_jobs.sort(key=lambda x: x["positions_remaining"], reverse=True)

    return raw_jobs


def get_applications_by_employer(employer_email, job_id=None, status_filter=None, sort_by="match"):
    """
    Return all applications for jobs posted by a given employer.
    Attaches full intelligent match scores and detailed applicant and job info.
    Sorted by match score descending by default.
    """
    with get_db_connection() as connection:
        employer = connection.execute(
            "SELECT id FROM employers WHERE email = %s", (employer_email.strip().lower(),)
        ).fetchone()

        if employer is None:
            return []

        query = """
            SELECT
                applications.id AS application_id,
                applications.status AS application_status,
                applications.applied_at AS applied_at,
                workers.id AS worker_id,
                workers.name AS worker_name,
                workers.email AS worker_email,
                workers.skill AS worker_skill,
                workers.location AS worker_location,
                workers.experience AS worker_experience,
                workers.wage AS worker_wage,
                workers.availability AS worker_availability,
                workers.rating AS worker_rating,
                jobs.id AS job_id,
                jobs.title AS job_title,
                jobs.skill_required AS job_skill,
                jobs.location AS job_location,
                jobs.daily_wage AS job_daily_wage,
                jobs.workers_needed AS job_workers_needed,
                jobs.positions_remaining AS job_positions_remaining,
                jobs.status AS job_status,
                (SELECT COUNT(*) FROM applications WHERE job_id = jobs.id AND status IN ('Confirmed', 'Accepted')) AS confirmed_count
            FROM applications
            JOIN workers ON applications.worker_id = workers.id
            JOIN jobs ON applications.job_id = jobs.id
            WHERE jobs.employer_id = %s
        """
        params = [employer["id"]]

        if job_id:
            query += " AND jobs.id = %s"
            params.append(job_id)

        if status_filter and status_filter != "All":
            query += " AND applications.status = %s"
            params.append(status_filter)

        query += " ORDER BY applications.applied_at DESC"
        rows = [dict(r) for r in connection.execute(query, params).fetchall()]

    for app in rows:
        worker_dict = {
            "skill": app["worker_skill"],
            "location": app["worker_location"],
            "experience": app["worker_experience"],
            "wage": app["worker_wage"],
            "availability": app.get("worker_availability", "Immediate"),
            "rating": app.get("worker_rating")
        }
        job_dict = {
            "title": app["job_title"],
            "skill_required": app["job_skill"],
            "location": app["job_location"],
            "daily_wage": app["job_daily_wage"],
            "workers_needed": app["job_workers_needed"],
            "description": ""
        }
        match = compute_match_score(worker_dict, job_dict)
        app["match_score"] = match["score"]
        app["match_percentage"] = match["percentage"]
        app["match_level"] = match["level"]
        app["match_badge_class"] = match["badge_class"]
        app["match_breakdown"] = match["breakdown"]

    if sort_by == "match":
        rows.sort(key=lambda x: (x["match_score"], x["applied_at"]), reverse=True)
    elif sort_by == "date":
        rows.sort(key=lambda x: x["applied_at"], reverse=True)

    return rows


def get_applications_by_worker(worker_email, sort_by="date"):
    """
    Return all applications for a given worker with intelligent match scores.
    """
    with get_db_connection() as connection:
        worker = connection.execute(
            "SELECT * FROM workers WHERE email = %s", (worker_email.strip().lower(),)
        ).fetchone()

        if worker is None:
            return []

        worker_dict = dict(worker)

        query = """
            SELECT
                applications.id AS application_id,
                applications.status AS application_status,
                applications.applied_at AS applied_at,
                jobs.id AS job_id,
                jobs.title AS job_title,
                jobs.skill_required AS job_skill,
                jobs.location AS job_location,
                jobs.daily_wage AS daily_wage,
                jobs.workers_needed AS workers_needed,
                jobs.positions_remaining AS positions_remaining,
                jobs.status AS job_status,
                employers.name AS employer_name
            FROM applications
            JOIN jobs ON applications.job_id = jobs.id
            JOIN employers ON jobs.employer_id = employers.id
            WHERE applications.worker_id = %s
            ORDER BY applications.applied_at DESC
        """
        rows = [dict(r) for r in connection.execute(query, (worker["id"],)).fetchall()]

    for app in rows:
        job_dict = {
            "title": app["job_title"],
            "skill_required": app["job_skill"],
            "location": app["job_location"],
            "daily_wage": app["daily_wage"],
            "workers_needed": app["workers_needed"],
            "description": ""
        }
        match = compute_match_score(worker_dict, job_dict)
        app["match_score"] = match["score"]
        app["match_percentage"] = match["percentage"]
        app["match_level"] = match["level"]
        app["match_badge_class"] = match["badge_class"]
        app["match_breakdown"] = match["breakdown"]

    if sort_by == "match":
        rows.sort(key=lambda x: (x["match_score"], x["applied_at"]), reverse=True)

    return rows


def update_application_status(application_id, new_status, employer_id):
    """
    Update application status (Pending, Shortlisted, Confirmed, Rejected).
    Also updates remaining positions on the corresponding job!
    """
    valid_statuses = {"Pending", "Shortlisted", "Confirmed", "Rejected"}
    if new_status == "Accepted":
        new_status = "Confirmed"

    if new_status not in valid_statuses:
        return False, "Invalid status. Allowed: Pending, Shortlisted, Confirmed, Rejected."

    with get_db_connection() as connection:
        cursor = connection.cursor()

        # Verify application belongs to this employer's job
        app_row = cursor.execute(
            """
            SELECT applications.id, applications.job_id, applications.status AS current_status,
                   jobs.workers_needed, jobs.positions_remaining
            FROM applications
            JOIN jobs ON applications.job_id = jobs.id
            WHERE applications.id = %s AND jobs.employer_id = %s
            """,
            (application_id, employer_id)
        ).fetchone()

        if not app_row:
            return False, "Application not found or does not belong to your jobs."

        job_id = app_row["job_id"]

        # Check capacity if confirming
        if new_status == "Confirmed" and app_row["current_status"] != "Confirmed":
            confirmed_count = cursor.execute(
                "SELECT COUNT(*) AS count FROM applications WHERE job_id = %s AND status IN ('Confirmed', 'Accepted')",
                (job_id,)
            ).fetchone()["count"]

            if confirmed_count >= app_row["workers_needed"]:
                return False, f"Cannot confirm: All {app_row['workers_needed']} positions are already filled for this job."

        cursor.execute(
            "UPDATE applications SET status = %s WHERE id = %s",
            (new_status, application_id)
        )
        # Step 8: Trigger in-app notification for worker in the same transaction.
        worker_info = cursor.execute(
            "SELECT worker_id, job_id FROM applications WHERE id = %s",
            (application_id,)
        ).fetchone()
        if worker_info:
            job_row = cursor.execute(
                "SELECT title FROM jobs WHERE id = %s",
                (worker_info["job_id"],)
            ).fetchone()
            job_title = job_row["title"] if job_row else "Job"
            cursor.execute(
                """
                INSERT INTO notifications (user_role, user_id, title, message, link)
                VALUES ('worker', %s, %s, %s, %s)
                """,
                (
                    worker_info["worker_id"],
                    f"Application {new_status}",
                    f"Your application for '{job_title}' has been updated to '{new_status}'.",
                    "/worker/dashboard"
                )
            )

        # Recalculate remaining positions for this job
        job_stats = recalculate_job_positions(job_id, connection)

        msg = f"Application status updated to '{new_status}'."
        if job_stats:
            msg += f" Remaining positions for job #{job_id}: {job_stats['positions_remaining']}/{job_stats['workers_needed']}."

        return True, msg


def is_profession_match(worker_profession, job_profession):
    """
    Check if a worker's registered profession strictly matches the job's required profession.
    Strict profession matching:
    1. Case-insensitive exact match (e.g. 'Driver' == 'driver', 'Electrician' == 'electrician')
    2. Canonical trade mapping (e.g. 'Driver' <-> 'Driving', 'Plumber' <-> 'Plumbing',
       'Farm Worker' <-> 'Farming', 'Mason' <-> 'Masonry')
    Excludes any unrelated professions.
    """
    if not worker_profession or not job_profession:
        return False

    w_str = str(worker_profession).strip().lower()
    j_str = str(job_profession).strip().lower()

    if w_str == j_str:
        return True

    try:
        from trade_utils import TRADE_METADATA
        def resolve_key(val):
            s = str(val).strip().lower()
            for key, meta in TRADE_METADATA.items():
                if key == s:
                    return key
                for kw in meta.get("keywords", []):
                    kw_low = kw.lower()
                    if kw_low == s or kw_low in s or s in kw_low:
                        return key
            return None

        w_key = resolve_key(w_str)
        j_key = resolve_key(j_str)
        if w_key and j_key and w_key == j_key:
            return True
    except Exception:
        pass

    return False


def get_matched_workers_for_job(job_id, min_score=0):
    """
    Intelligent Worker Recommendation (Phase 06):
    Find and rank registered workers for a specific job.
    Strict profession matching: filters candidates by profession first,
    ensuring only candidates with the matching profession are scored and displayed.
    """
    job = get_job_by_id(job_id)
    if not job:
        return []

    job_profession = job.get("skill_required") or ""
    workers = get_all_workers()
    matched_candidates = []

    for w in workers:
        worker_profession = w.get("skill") or ""

        # Step 1: Strict profession matching before calculating match score
        if not is_profession_match(worker_profession, job_profession):
            continue

        # Step 2: Calculate match score only for candidates of the selected profession
        match = compute_match_score(w, job)
        if match["percentage"] >= min_score:
            cand = dict(w)
            cand["match_score"] = match["score"]
            cand["match_percentage"] = match["percentage"]
            cand["match_level"] = match["level"]
            cand["match_badge_class"] = match["badge_class"]
            cand["match_breakdown"] = match["breakdown"]
            cand["match_reasons"] = match.get("reasons", [])
            cand["match_explanation"] = match.get("explanation", "")
            matched_candidates.append(cand)

    matched_candidates.sort(key=lambda x: x["match_score"], reverse=True)
    return matched_candidates


def insert_application(worker_id, job_id):
    """
    Worker applies for a job.
    Enforces:
    - Worker and Job exist
    - Job is Open and has remaining positions > 0
    - Worker has not already applied
    """
    with get_db_connection() as connection:
        cursor = connection.cursor()

        job = cursor.execute(
            "SELECT id, status, positions_remaining FROM jobs WHERE id = %s", (job_id,)
        ).fetchone()

        if not job:
            return None, "Job not found."

        if job["status"] != "Open" or (
            job["positions_remaining"] is not None and job["positions_remaining"] <= 0
        ):
            return None, "This job is already filled or closed."

        existing = cursor.execute(
            "SELECT id FROM applications WHERE worker_id = %s AND job_id = %s",
            (worker_id, job_id)
        ).fetchone()

        if existing:
            return None, "You have already applied for this job."

        cursor.execute(
            "INSERT INTO applications (worker_id, job_id, status) VALUES (%s, %s, 'Pending') RETURNING id",
            (worker_id, job_id)
        )
        return cursor.fetchone()["id"], "Application submitted successfully!"


# =====================================================================
# STEP 1 & 2: USER AUTHENTICATION, PASSWORD HASHING, & PROFILE HELPERS
# =====================================================================

def create_worker(name, email, password, skill, location, experience=0, wage=0, availability="Immediate", rating=None, phone=""):
    """Create a new worker account with securely hashed password."""
    password_hash = generate_password_hash(password)
    with get_db_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO workers
            (name, email, password_hash, skill, location, experience, wage, availability, rating, phone)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (name.strip(), email.strip().lower(), password_hash, skill.strip(), location.strip(), experience, wage, availability.strip(), rating, phone.strip())
        )
        return cursor.fetchone()["id"]


def create_employer(name, email, password, employer_type, location, is_verified=0, phone=""):
    """Create a new employer account with securely hashed password."""
    password_hash = generate_password_hash(password)
    with get_db_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO employers
            (name, email, password_hash, employer_type, location, is_verified, phone)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (name.strip(), email.strip().lower(), password_hash, employer_type.strip(), location.strip(), is_verified, phone.strip())
        )
        return cursor.fetchone()["id"]


def verify_worker_credentials(email, password):
    """Verify worker credentials using secure password hashing."""
    worker = get_worker_by_email(email)
    if not worker:
        return None
    stored_hash = worker.get("password_hash")
    if stored_hash and check_password_hash(stored_hash, password):
        return worker
    return None


def verify_employer_credentials(email, password):
    """Verify employer credentials using secure password hashing."""
    employer = get_employer_by_email(email)
    if not employer:
        return None
    stored_hash = employer.get("password_hash")
    if stored_hash and check_password_hash(stored_hash, password):
        return employer
    return None


def update_worker_profile(worker_id, name, skill, location, experience, wage, availability, phone=""):
    """Allow workers to correct and update their profile and preferences (Step 7)."""
    with get_db_connection() as connection:
        connection.execute(
            """
            UPDATE workers
            SET name = %s, skill = %s, location = %s, experience = %s, wage = %s, availability = %s, phone = %s
            WHERE id = %s
            """,
            (name.strip(), skill.strip(), location.strip(), experience, wage, availability.strip(), phone.strip(), worker_id)
        )
        return True


def update_employer_profile(employer_id, name, employer_type, location, is_verified=None, phone=""):
    """Update employer profile."""
    with get_db_connection() as connection:
        if is_verified is not None:
            connection.execute(
                """
                UPDATE employers
                SET name = %s, employer_type = %s, location = %s, is_verified = %s, phone = %s
                WHERE id = %s
                """,
                (name.strip(), employer_type.strip(), location.strip(), 1 if is_verified else 0, phone.strip(), employer_id)
            )
        else:
            connection.execute(
                """
                UPDATE employers
                SET name = %s, employer_type = %s, location = %s, phone = %s
                WHERE id = %s
                """,
                (name.strip(), employer_type.strip(), location.strip(), phone.strip(), employer_id)
            )
        return True


def toggle_employer_verification(employer_id, is_verified=None):
    """Toggle or set employer verification status (Step 8)."""
    with get_db_connection() as connection:
        if is_verified is None:
            connection.execute(
                "UPDATE employers SET is_verified = CASE WHEN is_verified = 1 THEN 0 ELSE 1 END WHERE id = %s",
                (employer_id,)
            )
        else:
            connection.execute(
                "UPDATE employers SET is_verified = %s WHERE id = %s",
                (1 if is_verified else 0, employer_id)
            )
        return True


# =====================================================================
# STEP 8: SAVED JOBS, NOTIFICATIONS, INTERVIEWS, AND REPORTS HELPERS
# =====================================================================

def save_job_for_worker(worker_id, job_id):
    """Bookmark a job for a worker."""
    with get_db_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO saved_jobs (worker_id, job_id) VALUES (%s, %s)
            ON CONFLICT (worker_id, job_id) DO NOTHING
            RETURNING id
            """,
            (worker_id, job_id)
        )
        if cursor.fetchone() is None:
            return False, "Job is already saved in your bookmarks."
        return True, "Job saved to your bookmarks."


def unsave_job_for_worker(worker_id, job_id):
    """Remove a bookmarked job."""
    with get_db_connection() as connection:
        connection.execute(
            "DELETE FROM saved_jobs WHERE worker_id = %s AND job_id = %s",
            (worker_id, job_id)
        )
        return True, "Job removed from saved list."


def is_job_saved_by_worker(worker_id, job_id):
    """Check if a job is saved by worker."""
    if not worker_id:
        return False
    with get_db_connection() as connection:
        row = connection.execute(
            "SELECT id FROM saved_jobs WHERE worker_id = %s AND job_id = %s",
            (worker_id, job_id)
        ).fetchone()
        return bool(row)


def get_saved_jobs_by_worker(worker_id):
    """Retrieve all saved jobs with employer info."""
    with get_db_connection() as connection:
        rows = connection.execute(
            """
            SELECT jobs.*, employers.name AS employer_name, employers.is_verified AS employer_is_verified, saved_jobs.saved_at
            FROM saved_jobs
            JOIN jobs ON saved_jobs.job_id = jobs.id
            JOIN employers ON jobs.employer_id = employers.id
            WHERE saved_jobs.worker_id = %s
            ORDER BY saved_jobs.id DESC
            """,
            (worker_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def create_notification(user_role, user_id, title, message, link=None,
                        notification_type="JOB_POSTED", job_id=None,
                        company_name=None, job_title=None, location=None):
    """Create in-app notification with support for rich metadata."""
    with get_db_connection() as connection:
        connection.execute(
            """
            INSERT INTO notifications (user_role, user_id, title, message, link,
                                       notification_type, job_id, company_name, job_title, location)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (user_role, user_id, title, message, link,
             notification_type, job_id, company_name, job_title, location)
        )
        return True


def get_notifications(user_role, user_id, unread_only=False):
    """Get notifications for a user in reverse chronological order with formatted metadata."""
    from datetime import datetime, timezone

    def _relative_time(ts_str):
        if not ts_str:
            return "Recently"
        formats = ["%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d"]
        dt = ts_str if isinstance(ts_str, datetime) else None
        for fmt in formats:
            if dt:
                break
            try:
                dt = datetime.strptime(str(ts_str).strip(), fmt)
                break
            except (ValueError, TypeError):
                continue
        if not dt:
            try:
                dt = datetime.fromisoformat(str(ts_str).strip().replace("Z", "+00:00"))
            except (ValueError, TypeError):
                return str(ts_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        diff = int((datetime.now(timezone.utc) - dt.astimezone(timezone.utc)).total_seconds())
        if diff < 45:
            return "Just now"
        if diff < 3600:
            return f"{max(1, diff // 60)}m ago"
        if diff < 86400:
            return f"{diff // 3600}h ago"
        if diff < 604800:
            return f"{diff // 86400}d ago"
        return dt.strftime("%b %d, %Y")

    with get_db_connection() as connection:
        query = "SELECT * FROM notifications WHERE user_role = %s AND user_id = %s"
        params = [user_role, user_id]
        if unread_only:
            query += " AND is_read = 0"
        query += " ORDER BY id DESC LIMIT 50"
        rows = connection.execute(query, params).fetchall()
        
        result = []
        for r in rows:
            item = dict(r)
            item["time_display"] = _relative_time(item.get("created_at"))
            # Fallback metadata if not set
            if not item.get("job_title") and item.get("title"):
                item["job_title"] = item.get("title")
            if not item.get("company_name"):
                item["company_name"] = "WorkConnect"
            if not item.get("location"):
                item["location"] = "Local"
            if not item.get("link"):
                if item.get("job_id"):
                    item["link"] = f"/jobs/{item['job_id']}"
                else:
                    item["link"] = "/worker/dashboard" if user_role == "worker" else "/employer/dashboard"
            result.append(item)
        return result


def get_unread_notifications_count(user_role, user_id):
    """Count unread notifications."""
    if not user_id:
        return 0
    with get_db_connection() as connection:
        row = connection.execute(
            "SELECT COUNT(*) AS count FROM notifications WHERE user_role = %s AND user_id = %s AND is_read = 0",
            (user_role, user_id)
        ).fetchone()
        return row["count"] if row else 0


def mark_notification_as_read(notification_id, user_role, user_id):
    """Mark a specific notification as read."""
    with get_db_connection() as connection:
        connection.execute(
            "UPDATE notifications SET is_read = 1 WHERE id = %s AND user_role = %s AND user_id = %s",
            (notification_id, user_role, user_id)
        )
        return True


def mark_all_notifications_as_read(user_role, user_id):
    """Mark all user notifications as read."""
    with get_db_connection() as connection:
        connection.execute(
            "UPDATE notifications SET is_read = 1 WHERE user_role = %s AND user_id = %s",
            (user_role, user_id)
        )
        return True


def schedule_interview(job_id, application_id, employer_id, worker_id, interview_date, interview_time, location_or_link, notes=""):
    """Schedule an interview between employer and worker (Step 8)."""
    with get_db_connection() as connection:
        if application_id == 0:
            candidate = connection.execute(
                """
                SELECT workers.skill, jobs.skill_required
                FROM workers
                CROSS JOIN jobs
                WHERE workers.id = %s
                  AND jobs.id = %s
                  AND jobs.employer_id = %s
                """,
                (worker_id, job_id, employer_id)
            ).fetchone()
            if (
                not candidate
                or not is_profession_match(candidate["skill"], candidate["skill_required"])
            ):
                raise ValueError(
                    "The selected worker and job are not available for this employer."
                )

            application = connection.execute(
                """
                INSERT INTO applications (worker_id, job_id, status)
                SELECT %s, %s, 'Pending'
                WHERE EXISTS (
                    SELECT 1 FROM jobs WHERE id = %s AND employer_id = %s
                )
                AND EXISTS (SELECT 1 FROM workers WHERE id = %s)
                ON CONFLICT (worker_id, job_id) DO NOTHING
                RETURNING id
                """,
                (worker_id, job_id, job_id, employer_id, worker_id)
            ).fetchone()
            if application is None:
                application = connection.execute(
                    """
                    SELECT applications.id
                    FROM applications
                    JOIN jobs ON applications.job_id = jobs.id
                    WHERE applications.worker_id = %s
                      AND applications.job_id = %s
                      AND jobs.employer_id = %s
                    """,
                    (worker_id, job_id, employer_id)
                ).fetchone()
            if not application:
                raise ValueError(
                    "The selected worker and job are not available for this employer."
                )
            application_id = application["id"]

        application = connection.execute(
            """
            SELECT applications.worker_id, jobs.employer_id
            FROM applications
            JOIN jobs ON applications.job_id = jobs.id
            WHERE applications.id = %s AND jobs.id = %s
            """,
            (application_id, job_id)
        ).fetchone()
        if (
            not application
            or application["worker_id"] != worker_id
            or application["employer_id"] != employer_id
        ):
            raise ValueError(
                "The selected application does not belong to this worker and job."
            )

        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO interviews
            (job_id, application_id, employer_id, worker_id, interview_date, interview_time, location_or_link, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (job_id, application_id, employer_id, worker_id, interview_date, interview_time, location_or_link, notes)
        )
        interview_id = cursor.fetchone()["id"]

        # Trigger notification for the worker
        job = get_job_by_id(job_id)
        job_title = job["title"] if job else "Job"
        notif_msg = f"Meeting scheduled for '{job_title}' on {interview_date} at {interview_time}."
        cursor.execute(
            "INSERT INTO notifications (user_role, user_id, title, message, link) VALUES ('worker', %s, %s, %s, %s)",
            (worker_id, "Meeting Scheduled", notif_msg, "/worker/dashboard")
        )
        return interview_id


def get_interviews_for_worker(worker_id):
    """Retrieve interviews for a worker."""
    with get_db_connection() as connection:
        rows = connection.execute(
            """
            SELECT interviews.*, jobs.title AS job_title, employers.name AS employer_name, employers.location AS employer_location
            FROM interviews
            JOIN jobs ON interviews.job_id = jobs.id
            JOIN employers ON interviews.employer_id = employers.id
            WHERE interviews.worker_id = %s
            ORDER BY interviews.interview_date ASC, interviews.interview_time ASC
            """,
            (worker_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def get_interviews_for_employer(employer_id, job_id=None):
    """Retrieve interviews scheduled by an employer."""
    with get_db_connection() as connection:
        query = """
            SELECT interviews.*, jobs.title AS job_title, workers.name AS worker_name, workers.email AS worker_email, workers.skill AS worker_skill
            FROM interviews
            JOIN jobs ON interviews.job_id = jobs.id
            JOIN workers ON interviews.worker_id = workers.id
            WHERE interviews.employer_id = %s
        """
        params = [employer_id]
        if job_id:
            query += " AND interviews.job_id = %s"
            params.append(job_id)
        query += " ORDER BY interviews.interview_date ASC, interviews.interview_time ASC"
        rows = connection.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def submit_report(reporter_role, reporter_id, target_type, target_id, reason, details=""):
    """Submit a report for suspicious job, worker, or employer (Step 8)."""
    with get_db_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO reports (reporter_role, reporter_id, target_type, target_id, reason, details)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (reporter_role, reporter_id, target_type, target_id, reason, details)
        )
        return cursor.fetchone()["id"]


def get_all_reports():
    """Retrieve all reports for moderation."""
    with get_db_connection() as connection:
        rows = connection.execute("SELECT * FROM reports ORDER BY id DESC").fetchall()
        return [dict(r) for r in rows]