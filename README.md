# AI Study Planner

AI Study Planner is a Django web application that helps students turn course syllabi and exam dates into an organized, adjustable study schedule. It keeps course materials, study topics, preferences, plans, and session progress together so students can see what to study and respond when they fall behind.

## Problem Statement

Students often have course information spread across syllabi, exam calendars, and personal notes. Converting those materials into a realistic day-by-day study plan takes time, and a plan can quickly become outdated when study sessions are missed. This is especially challenging for students managing several courses and deadlines at once.

## Proposed Solution

The application provides an authenticated workspace for managing courses and exams, uploading PDF syllabi, extracting study topics, estimating time per topic, and generating a study plan around the student's preferences and exam dates. Students can track sessions as pending, completed, or missed, then review or replan unfinished work while preserving completed sessions.

The project combines deterministic scheduling and server-side validation with two focused AI features. OpenAI is used to extract supported topics from syllabus text and to select a constrained study-plan review action. The application validates structured AI output and checks scheduling feasibility in its own services before saving changes.

## Features

- Account registration, login, and logout.
- Course and exam management.
- PDF syllabus upload, text extraction, and download.
- AI-assisted topic extraction with validated structured output.
- Per-topic study-time estimates and study preferences.
- Study-plan generation, review, replanning, and archiving.
- Study-session status tracking and agent review history.
- JSON API endpoints for courses, study plans, and session status.

## Technologies Used

- Python
- Django 5.2
- PostgreSQL with psycopg
- OpenAI API (Responses API; configured model defaults to `gpt-4.1-mini-2025-04-14`)
- `python-dotenv` for local environment configuration
- `pypdf` for extracting text from PDF syllabi
- `psutil` for process memory measurements in the evaluation utility
- HTML templates and CSS for the web interface

## Project Structure

```text
AIStudyPlanner/
├── accounts/                 # Custom user model, registration, login, and account views
├── evaluation/               # Topic extraction cases, evaluation runner, and saved JSON results
├── planner/
│   ├── ai/                   # Topic extraction and plan-review AI integrations
│   ├── api/                  # JSON API endpoints
│   ├── forms/                # Input forms and validation
│   ├── migrations/           # Database schema migrations
│   ├── models/               # Domain models, split by entity
│   ├── services/             # Scheduling, persistence, syllabus, and business rules
│   ├── static/                # Stylesheets
│   ├── templates/             # Server-rendered pages
│   ├── utils/                 # Performance and topic-evaluation helpers
│   └── views/                  # Web request handlers, organized by feature
├── study_planner/            # Django settings and project URL/ASGI/WSGI configuration
├── .env.example              # Safe template for required local settings
├── .gitignore                # Excludes secrets, local files, and generated artifacts
├── manage.py                 # Django management entry point
└── requirements.txt          # Python dependencies
```

## Requirements

- Python 3.10 or newer.
- PostgreSQL running locally or reachable from your machine.
- An OpenAI API key and access to the model configured in `OPENAI_MODEL` for topic extraction and AI plan review.

## How to Run the Project

The commands below use PowerShell on Windows. From a terminal, move into the `AIStudyPlanner` project directory first.

1. Create and activate a virtual environment:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

   On macOS or Linux, use `python3 -m venv .venv` and `source .venv/bin/activate`.

2. Install the dependencies:

   ```powershell
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

3. Create a PostgreSQL database and user, or use an existing PostgreSQL account. For example, from `psql` as a PostgreSQL administrator:

   ```sql
   CREATE USER studyplanner_user WITH PASSWORD 'choose-a-local-password';
   CREATE DATABASE ai_study_planner OWNER studyplanner_user;
   ```

   If you already have a database user, set its values in the next step instead of creating this example user.

4. Create a local `.env` file by copying `.env.example`, then edit the values:

   ```powershell
   Copy-Item .env.example .env
   ```

   Set `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, and `DB_PORT` to match your PostgreSQL setup. Add your OpenAI API key. Do not commit `.env` or put real credentials in the repository.

5. Apply database migrations:

   ```powershell
   python manage.py migrate
   ```

6. (Optional) Create an administrator account for Django's admin interface:

   ```powershell
   python manage.py createsuperuser
   ```

7. Start the development server:

   ```powershell
   python manage.py runserver
   ```

8. Open the web application at [http://127.0.0.1:8000/](http://127.0.0.1:8000/). The Django admin is at [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/).

The AI topic extraction and plan-review actions require a valid OpenAI API key, network access, and model availability. Other application setup also requires PostgreSQL to be running and reachable with the configured database values.

## Environment Variables

The application reads `.env` from the project root. `.env.example` contains placeholders only.

| Variable | Required | Purpose |
| --- | --- | --- |
| `DJANGO_SECRET_KEY` | Yes | Django signing and security key. Use a private, randomly generated value. |
| `DJANGO_DEBUG` | No | Enables Django debug mode when set to `True`; the example enables it for local development. |
| `DJANGO_ALLOWED_HOSTS` | For deployment | Comma-separated host names Django may serve. The example lists local development hosts. |
| `DB_NAME` | Yes | PostgreSQL database name. |
| `DB_USER` | Yes | PostgreSQL user name. |
| `DB_PASSWORD` | Yes | Password for the PostgreSQL user. |
| `DB_HOST` | Yes | PostgreSQL server host, commonly `localhost` for local development. |
| `DB_PORT` | Yes | PostgreSQL server port, commonly `5432`. |
| `OPENAI_API_KEY` | For AI features | API key used for syllabus topic extraction and study-plan review. |
| `OPENAI_MODEL` | For AI features | Model name used for both AI features; the example sets `gpt-4.1-mini-2025-04-14`. |

For a deployed environment, set a production secret, turn debug mode off, and configure the real allowed host names. Never publish private credentials.

## Web Pages and API

The main web interface is served from `/`. Common pages include `/courses/`, `/study-plans/`, `/study-settings/`, and `/agent-history/`. Account pages are under `/accounts/`.

The JSON API is mounted under `/api/`:

| Endpoint | Purpose |
| --- | --- |
| `GET /api/courses/` | List the signed-in user's courses. |
| `GET /api/study-plans/` | List the signed-in user's study plans. |
| `GET /api/study-plans/<plan_id>/` | Retrieve an owned study plan and its sessions. |
| `PATCH /api/study-sessions/<session_id>/status/` | Update a session status by sending JSON such as `{"status":"completed"}`. |

The API uses Django's session authentication and requires a signed-in user. The session-status endpoint accepts `application/json` and is subject to Django CSRF protection when used with session cookies.

## AI Evaluation Snapshot

The repository includes topic-extraction evaluation cases and saved JSON results in `evaluation/results/`. The included run used 3 repetitions across 3 synthetic cases (9 attempts total) with the model recorded in the result file:

- Successful extractions: 9 of 9.
- Micro precision: 0.926.
- Micro recall: 0.926.
- Micro F1: 0.926.
- Mean extraction duration: about 1.47 seconds.
- Mean process memory after an attempt: about 71.98 MB; this is a process RSS sample, not peak memory.

The title metric normalizes case and whitespace; equivalent wording may need manual semantic review. These results reflect the included small synthetic evaluation set, not a broad real-world benchmark. Latency covers extraction and validation, and memory measurements sample the local Python process before and after each attempt.

To run the evaluation again, configure `OPENAI_API_KEY` and `OPENAI_MODEL` in `.env`, activate the environment, and run:

```powershell
python -m evaluation.run_topic_evaluation --repetitions 3
```

Each repetition makes one API request per evaluation case and may incur API usage. A new JSON report is saved under `evaluation/results/`.

## Security and Uploaded Files

- Keep `.env` private; it is excluded by `.gitignore`.
- The example environment file contains placeholders, not working credentials.
- Syllabus PDF uploads are limited to 5 MB by the application setting.
- Uploaded media files are stored locally in `media/`, which is excluded from version control.

## License

No license file is currently included. Add a license before redistributing the project if you intend to grant reuse rights.
