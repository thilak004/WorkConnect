# WorkConnect

WorkConnect connects local workers with employers. Workers can create profiles, browse and apply for jobs, save listings, receive notifications, and manage interviews. Employers can post jobs, review applications, find matched candidates, and schedule interviews. The interface supports English, Telugu, and Hindi, with optional Gemini-powered assistance and a server-side fallback.

## Technology

- Python and Flask
- PostgreSQL on Supabase, accessed with psycopg 3
- HTML/Jinja templates, CSS, and inline browser JavaScript
- Optional Google Gemini API (`google-genai`)
- Vercel Functions for hosting; GitHub for source control

## Project structure

```text
Work__Connect/
├── app.py                         # Flask app and routes; Vercel entry point
├── database.py                    # PostgreSQL schema setup and application queries
├── db.py                          # Shared psycopg connection lifecycle
├── schema.sql                     # PostgreSQL schema matching the existing SQLite DB
├── migrate_sqlite_to_postgres.py  # Read-only, repeat-safe SQLite data import
├── ai_services.py                 # Gemini assistant, voice field extraction, fallback
├── notification_service.py        # Job posting notifications
├── trade_utils.py                 # Trade matching and display metadata
├── translations.py                # English, Telugu, and Hindi strings
├── templates/                     # Flask/Jinja pages
├── static/
│   ├── css/style.css
│   └── images/trades/             # Trade illustrations
├── requirements.txt
├── vercel.json
└── .env.example
```

The existing `workconnect.db` file is the migration source only. It is ignored by Git and is never modified by the migration script.

## Local setup

Use Python 3.11 or newer and a Supabase PostgreSQL database.

```powershell
cd C:\path\to\Work__Connect
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` and set `DATABASE_URL` and a private `SECRET_KEY`. Generate a strong Flask key with:

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

`GEMINI_API_KEY` is optional. When unset, the assistant uses its built-in WorkConnect fallback. Do not commit `.env` or paste a database password/API key into templates or JavaScript.

Password recovery is temporarily disabled until a verified email-reset flow is configured. The recovery page does not collect passwords, and reset submissions are rejected.

Voice registration requires a user-provided email address and password; it does not create accounts with shared default credentials or invented contact details. User and AI chat messages are rendered as text, and redirects are restricted to this site.

## Create and configure Supabase

1. Create a Supabase project and choose a database password and region.
2. In the Supabase project dashboard, open **Connect** and copy a PostgreSQL connection string. Use the direct connection or an appropriate pooler string; URL-encode special characters in the password. Require SSL.
3. Open **SQL Editor**, run the contents of `schema.sql`, and confirm that all eight tables exist: `workers`, `employers`, `jobs`, `applications`, `saved_jobs`, `notifications`, `interviews`, and `reports`.
4. Put the connection string in local `.env` as `DATABASE_URL`. Keep this server-side; never use the Supabase service-role key in the browser.

For command-line setup instead of the SQL Editor, after `.env` has a valid `DATABASE_URL`, run:

```powershell
python -c "from database import initialize_database; initialize_database()"
```

The schema uses identity columns and preserves the existing field names, uniqueness rules, checks, and foreign-key relationships. Run the schema before importing data.

## Import existing SQLite data

The importer reads `workconnect.db` in read-only mode. It migrates the existing table records and IDs in dependency order, preserves `NULL`s, checks that the SQLite and PostgreSQL column sets match, skips rows that conflict with existing primary/unique keys, and resets identity sequences. PostgreSQL work is transactional; a failure rolls it back. The SQLite file is not changed.

With `DATABASE_URL` set and `schema.sql` already applied:

```powershell
python migrate_sqlite_to_postgres.py
```

To select another source file:

```powershell
python migrate_sqlite_to_postgres.py --sqlite C:\path\to\workconnect.db
```

The script reports inserted records per table. Rerunning it is safe; conflicting records are left unchanged. Review the output and compare table counts before switching traffic to the new database.

## Run locally

```powershell
python app.py
```

Open the address printed by Flask. Database access is lazy, so importing the WSGI app does not run schema DDL; configure the database and apply `schema.sql` before using database-backed routes.

## GitHub

Create a GitHub repository, then from the project directory:

```powershell
git init
git add .
git status
git commit -m "Prepare WorkConnect for PostgreSQL and Vercel"
git branch -M main
git remote add origin https://github.com/<account>/<repository>.git
git push -u origin main
```

Before pushing, check that `.env`, `workconnect.db`, virtual environments, and secret files are ignored. Do not force-add ignored files.

## Vercel deployment

1. Push the project to GitHub.
2. In Vercel, import the repository and set the project root to the directory containing `app.py` and `vercel.json`.
3. Add these server-side environment variables in **Project Settings → Environment Variables** for each target environment:
   - `DATABASE_URL` — Supabase PostgreSQL connection string.
   - `SECRET_KEY` — a randomly generated, private Flask signing key.
   - `GEMINI_API_KEY` — optional; required only for Gemini-backed answers.
4. Ensure the Supabase schema and SQLite import are complete before directing users to the deployment.
5. Deploy from Vercel and inspect the build and function logs. `app.py` exposes the Flask application as `app`; `vercel.json` routes requests to it.

Do not add `workconnect.db` to Vercel for production use. User uploads are not stored on the local filesystem; use an external object-storage service if persistent uploads are added later.

## Post-deployment verification

Test these flows against a non-production test database and test accounts:

- App home page, static trade illustrations, and English/Telugu/Hindi switching.
- Worker and employer registration, login, logout, and profile updates.
- Password recovery displays that it is unavailable until email ownership can be verified; do not re-enable direct password changes by email alone.
- Employer job creation; worker browse/search, apply, and save/unsave.
- Employer application review/status updates and candidate matching.
- Notifications, interview scheduling, and report submission.
- AI chat and voice parsing; test both with and without `GEMINI_API_KEY`.

The repository includes integration scripts such as `test_workflow_and_matching.py`, `test_job_posting_notification_system.py`, and `test_all_9_steps.py`. They require a configured PostgreSQL database and existing test fixtures; some create or delete test rows, so run them only against a disposable test project, never against production data. Also test the deployed Vercel URL directly and review its function logs. A deployment is not considered verified until those checks have actually been run.

Run the integration scripts against a disposable configured database with:

```powershell
python test_workflow_and_matching.py
python test_job_posting_notification_system.py
python test_all_9_steps.py
```
