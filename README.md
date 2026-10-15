# AI Study Planner

AI Study Planner is a Django application that helps students organize courses,
extract syllabus topics, prepare for exams, and adapt study schedules as
progress changes.

## Problem Statement

Students often have course content, exam dates, and study tasks spread across
different documents. Creating a realistic schedule takes time, and missed
sessions can make that schedule unsuitable.

## Proposed Solution

The application combines deterministic scheduling with AI-assisted topic
extraction and study-plan recommendations.

Python services enforce workload limits, exam deadlines, ownership, and data
integrity. The AI recommends a feasible scheduling option using the student's
preferences. Students review and approve proposed changes before application.

## Features

- Account registration, login, and logout.
- Course and exam management.
- PDF and UTF-8 TXT syllabus uploads.
- Authenticated syllabus downloads and extracted-text previews.
- AI-assisted topic extraction with structured output validation.
- Editable study-time estimates per topic.
- Daily study preferences.
- Study and revision scheduling across courses.
- Session status tracking: Pending, Completed, and Missed.
- Manual replanning and plan archiving.
- AI proposals with explicit student approval.
- Agent history with outcomes, elapsed time, and process memory readings.
- Session-authenticated JSON APIs.
- Read-only inspection of Planner models through Django admin.
- Automated tests and separate evaluations of both AI features.

## Technologies

- Python
- Django 5.2
- PostgreSQL with psycopg
- OpenAI Responses API
- python-dotenv
- pypdf
- psutil
- Django templates, HTML, CSS, and JavaScript

Exact dependency versions are listed in `requirements.txt`.

## Project Structure

| Location | Responsibility |
| --- | --- |
| `accounts/` | User accounts, authentication, and registration |
| `evaluation/` | Synthetic cases, scoring, evaluation runners, and saved reports |
| `planner/ai/` | Shared OpenAI client, AI integrations, tools, and validation |
| `planner/ai/prompts/` | Markdown instructions for both AI features |
| `planner/api/` | JSON endpoints and shared API decorator |
| `planner/forms/` | Input validation |
| `planner/migrations/` | Database schema history |
| `planner/models/` | Domain models and constraints |
| `planner/services/` | Scheduling and application business logic |
| `planner/static/` | Stylesheets |
| `planner/templates/` | Server-rendered pages |
| `planner/tests/` | Automated tests |
| `planner/utils/` | Measurement and topic-scoring helpers |
| `planner/views/` | Web request handlers |
| `planner/admin.py` | Read-only Planner model registrations |
| `study_planner/` | Django settings and project configuration |
| `manage.py` | Django management entry point |

## Requirements

- Python 3.10 or newer.
- PostgreSQL.
- An OpenAI API key and access to the configured model for real AI requests.

## Local Setup

Run the following PowerShell commands from the project root.

### 1. Create and activate a virtual environment

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If the environment already exists, activate it without recreating it.

### 2. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

### 3. Configure PostgreSQL

Create a database and use an appropriate PostgreSQL account.

For example, from psql as a PostgreSQL administrator:

```sql
CREATE USER studyplanner_user WITH PASSWORD 'choose-a-local-password';
CREATE DATABASE ai_study_planner OWNER studyplanner_user;
```

### 4. Configure environment variables

For a new setup:

```powershell
Copy-Item .env.example .env
```

Do not overwrite an existing configured `.env`.

Edit `.env` with your database connection details, a private Django secret key,
and OpenAI configuration. Never commit real secrets.

| Variable | Purpose |
| --- | --- |
| `DJANGO_SECRET_KEY` | Required Django signing key |
| `DJANGO_DEBUG` | Set `True` for local development |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated allowed host names |
| `DB_NAME` | PostgreSQL database name |
| `DB_USER` | PostgreSQL user |
| `DB_PASSWORD` | PostgreSQL password |
| `DB_HOST` | PostgreSQL host |
| `DB_PORT` | PostgreSQL port |
| `OPENAI_API_KEY` | Required for real AI requests |
| `OPENAI_MODEL` | Model used by both AI integrations |

The example model is `gpt-4.1-mini-2025-04-14`. Access to the configured model
must be available to the OpenAI account.

### 5. Apply migrations

```powershell
python manage.py migrate
```

### 6. Optionally create an administrator

```powershell
python manage.py createsuperuser
```

### 7. Start the development server

```powershell
python manage.py runserver
```

Open [the application](http://127.0.0.1:8000/).

The [Django admin](http://127.0.0.1:8000/admin/) requires an authorized
staff account.

### Visual Studio

The repository retains its Visual Studio project and solution files.

The startup file is `manage.py`, with `runserver` configured as the script
argument. Select the project's `.venv` interpreter when using Visual Studio.

The empty original startup file and unused test placeholder were removed.
Microsoft Office temporary lock files are excluded through `.gitignore`.

## Scheduling Rules

- Daily study time is shared across selected courses.
- Each selected course requires one exam and one syllabus with extracted topics.
- Earlier exams are prioritized.
- Each topic receives its estimated study time plus 15 minutes of revision.
- Sessions must be scheduled before their exam dates.
- Work may be split across days.
- Only one study plan per user may be Active.
- Archived plans have read-only session statuses.
- Saved session snapshots preserve historical names and deadlines when source
  records are changed or deleted.

Manual replanning uses the plan's existing daily limit. It preserves completed
sessions and reschedules Pending and Missed work.

## Shared OpenAI Configuration

Both AI features use `planner/ai/openai_client.py`.

The shared client reads the API key and model through Django settings.
The timeout is configured as 60 seconds, automatic retries are disabled, and
requests use `store=False`.

SDK errors are translated into `AIServiceError`. Each feature translates that
exception into its existing user-facing error type and validates its own
response structure.

Prompts are loaded as UTF-8 text from:

- `planner/ai/prompts/topic_extraction.md`
- `planner/ai/prompts/plan_review.md`

The standalone evaluation runners initialize Django and use the same settings.

## AI Topic Extraction

The application extracts text from an owned syllabus and sends that text to
OpenAI.

The response must follow a strict JSON schema. Python then validates titles,
descriptions, field names, topic count, and duplicate titles before saving.

Extracted topics initially receive a 60-minute study estimate. Students should
review extracted content and adjust estimates before generating a plan.

## AI Plan Review and Approval

The review agent recommends a scheduling tradeoff rather than following a
single predetermined tool-selection rule.

### Student input

The student provides:

- A valid resume date.
- A maximum acceptable daily study limit.
- A preference for a lighter workload or finishing sooner.

### Server-calculated options

The server uses the replanning scheduler to calculate feasible options within
the student's permitted range.

Candidate limits start at the current limit and increase in 15-minute steps.
The exact maximum is also considered.

Each option includes its daily limit, projected finish date, number of study
days, and peak scheduled daily workload.

### AI recommendation

The agent receives progress totals, feasible scheduling options, the resume
date, daily limits, and the student's preference. Syllabus text, topic names,
and individual exam deadlines are not included in the review input.

It can recommend:

- Keeping the current plan when no missed or overdue work requires repair.
- Replanning with one of the feasible daily limits.
- Reporting that unfinished work cannot fit when no feasible option exists.

The model can choose among different feasible limits. Python validates its
proposal but does not force one particular feasible limit.

### Approval and application

Requesting a proposal does not change the study plan.

A replanning proposal requires explicit student approval. Its signed token:

- Expires after 10 minutes.
- Is tied to the account and plan.
- Includes a fingerprint of the reviewed plan and sessions.
- Is rejected if the reviewed plan or progress changes.

On approval, the server recalculates feasibility inside a transaction before
creating the replacement plan.

Completed work is preserved, the original plan is archived, and the replacement
becomes Active. Saved Study settings are unchanged.

Approval does not make another OpenAI request.

### Explanation limitations

The scheduling checks validate the proposed plan, not every sentence in the
AI's explanation.

Manual evaluation found that an explanation could incorrectly claim the
current daily limit could not meet deadlines even when that limit appeared
among the feasible options. The recommended higher limit could still be valid
and correctly reflect the student's preference for finishing sooner.

The prompt was refined and the evaluation repeated. Correct actions and
preference matches were maintained, but an incorrect capacity claim still
appeared in the repeated run.

Another explanation described the resume date as though it were a completion
deadline. The resume date is when rescheduling starts.

Students should review explanations critically. Correct decision scores do
not establish factual explanation accuracy, and prompt instructions do not
guarantee factual output.

## Django Admin

The following Planner models are registered as read-only:

- Course
- Exam
- Syllabus
- Topic
- StudyPlan
- StudySession
- AgentLog

Authorized administrators can inspect records, search, and use the configured
filters. Adding, changing, deleting, and bulk actions are disabled for these
registrations.

The syllabus admin omits the storage file field. Authenticated application
downloads remain the route for retrieving syllabus files.

Existing User and Group administration retain their own permissions.

## Automated Tests

Run from the project root with the virtual environment activated:

```powershell
python manage.py test --verbosity 2
```

The current suite contains **123 tests**, confirmed passing during development.

Coverage includes:

- Scheduling limits, deadlines, revision workload, and impossible schedules.
- Replanning calculations and replacement-plan persistence.
- User ownership protection in web views and APIs.
- Shared API authentication, method checks, and cache handling.
- Shared OpenAI configuration and SDK error translation.
- Topic extraction validation.
- AI review forms and feasible scheduling options.
- Proposal validation and mocked AI responses.
- Signed approval tokens, expiry, tampering, and changed progress.
- Proposal preview, approval, error handling, and CSRF rejection.
- Exact and fuzzy title scoring.
- Agent-evaluation scoring and mocked evaluation runners.

OpenAI calls are mocked in the automated tests, so they use no API credit.

Database tests require PostgreSQL and permission to create a test database.
Django normally creates `test_ai_study_planner` and removes it afterward.
The application database is not used for test records.

Mocked tests verify application behaviour and validation. They do not measure
the real model's recommendation quality.

## Web Pages and JSON API

Main pages include:

- `/courses/`
- `/study-plans/`
- `/study-settings/`
- `/agent-history/`

Account pages are under `/accounts/`.

| Endpoint | Purpose |
| --- | --- |
| `GET /api/courses/` | List the signed-in user's courses |
| `GET /api/study-plans/` | List the signed-in user's plans |
| `GET /api/study-plans/<plan_id>/` | Retrieve an owned plan and its sessions |
| `PATCH /api/study-sessions/<session_id>/status/` | Update an owned active-plan session |

The API uses Django session authentication. The shared `api_view_json`
decorator handles authentication, allowed methods, and no-cache headers.

At the view layer, unauthenticated requests return 401 and unsupported methods
return 405 with an `Allow` header. Django's CSRF middleware can reject unsafe
requests before the view runs.

PATCH requests require JSON and remain subject to CSRF protection.

Example request body:

```json
{"status": "completed"}
```

## AI Evaluation

Evaluation reports are stored in `evaluation/results/`. Both runners make real
OpenAI requests and use API credit. They do not modify application study plans.

### Expanded topic extraction evaluation

The expanded set contains six synthetic syllabus cases, including longer
examples with administrative text, a weekly table, numbered subtopics, and
repeated content.

The October 15, 2026 run used three repetitions per case:

| Metric | Result |
| --- | --- |
| Attempts | 18 |
| Successful extractions | 18 |
| Failed extractions | 0 |
| Exact micro precision, recall, and F1 | Approximately 0.949 each |
| Fuzzy micro precision, recall, and F1 | Approximately 0.949 each |
| Fuzzy similarity threshold | 0.85 |
| Average extraction duration | Approximately 2.08 seconds |
| Average process memory afterward | Approximately 98.61 MB |

Report: `evaluation/results/topic_evaluation_20261015T192749345674Z.json`

Exact matching normalizes case and whitespace. Fuzzy matching uses Python's
character-similarity scoring with one-to-one title assignments. Duplicate
predictions count against precision.

Fuzzy matching found no additional matches at the selected threshold in this
run. It measures wording similarity, not semantic correctness.

Run the evaluation with:

```powershell
python -m evaluation.run_topic_evaluation --repetitions 3
```

With six cases and three repetitions, this makes 18 OpenAI requests.

### Plan-review evaluation

Six synthetic scenarios cover:

- A completed plan.
- Missed work with a lighter-workload preference.
- The same workload with a finish-sooner preference.
- Completed work consuming capacity and requiring a higher daily limit.
- An insufficient maximum daily limit.
- An exam deadline already reached at the resume date.

Feasible options are calculated using the application's scheduler.

The preference rubric selects the lowest feasible daily limit for
lighter-workload cases. For finish-sooner cases, it selects the earliest finish,
then the lowest daily limit achieving that date.

These are explicit benchmark expectations, not universal measures of the
best recommendation.

The repeated October 15, 2026 run after prompt refinement recorded:

| Metric | Result |
| --- | --- |
| Attempts | 18 |
| Successful attempts | 18 |
| Accepted proposals | 18 of 18 |
| Correct actions | 18 of 18 |
| Preference matches | 9 of 9 applicable attempts |
| Average proposal duration | Approximately 1.61 seconds |
| Average process memory afterward | Approximately 99.19 MB |

Report: `evaluation/results/plan_review_evaluation_20261015T193408073484Z.json`

The earlier run is also retained:

`evaluation/results/plan_review_evaluation_20261015T192925553820Z.json`

Application validation rejects invalid proposals before returning them to the
runner. Therefore, accepted-proposal rate is not a measurement of the raw
model's safety. Raw rejected model outputs are not captured.

Failures remain in the relevant metric denominators. Explanations are saved
for manual review, but their factual accuracy is not automatically scored.

Run the evaluation with:

```powershell
python -m evaluation.run_plan_review_evaluation --repetitions 3
```

With six cases and three repetitions, this makes 18 OpenAI requests.

### Interpretation and limitations

- Both evaluations use small synthetic datasets.
- The longer syllabi remain controlled examples with explicit main headings.
- Topic scores do not measure description quality, topic ordering, or PDF
  extraction quality.
- Fuzzy title similarity is not semantic evaluation.
- Agent scores reflect the defined scenario rubrics and validated proposals.
- Manual review identified factual errors in some agent explanations despite
  correct actions and preference matches.
- The same agent scenarios were reused after prompt refinement. The repeated
  run is a development evaluation, not an independent held-out benchmark.
- Results do not establish performance across real student populations or
  varied real-world syllabi.
- Further evaluation should include unseen cases and a documented rubric for
  explanation accuracy.

Latency measurements cover the AI feature call and its application validation.
Scheduling-option generation and evaluation scoring are outside the reported
agent latency.

Memory readings describe the entire local Python process. They are
before-and-after samples, not peak usage or remote model memory. MB figures
use decimal units.

Earlier reports and `Performance_Evaluation.docx` describe the original,
smaller topic evaluation. They are historical results and do not replace the
expanded reports above.

## Security and Uploads

- Keep `.env` and credentials private.
- Uploaded PDF and TXT files are limited to 5 MB.
- PDF extraction is limited to 50 pages.
- Extracted text is limited to 100,000 characters.
- Scanned PDFs require a text-based alternative; OCR is not implemented.
- Downloads require authentication and ownership checks.
- Uploaded files use randomly generated storage names.
- AI responses are validated before use.
- Review proposals require confirmation before application.
- Production requires `DEBUG=False`, correct allowed hosts, HTTPS, and an
  appropriate deployment configuration.

## License

No license file is currently included.