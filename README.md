# AI Study Planner

AI Study Planner is a Django application that helps students organize courses,
extract syllabus topics, prepare for exams, and adapt study schedules as
progress changes.

## Problem and Solution

Students may have course content, exam dates, and study tasks spread across
different documents. Creating a realistic schedule takes time, and missed
sessions can make an existing schedule unsuitable.

The application combines deterministic scheduling with AI-assisted topic
extraction and study-plan recommendations.

Python enforces ownership, workload limits, exam deadlines, and data integrity.
The AI recommends an action and a server-verified scheduling option.
Python generates the final factual explanation.
Students must approve a replacement before any plan changes are applied.

## Features

- Account registration, login, and logout.
- Course and exam management.
- PDF and UTF-8 TXT syllabus uploads.
- Authenticated syllabus downloads and extracted-text previews.
- AI-assisted topic extraction with structured output validation.
- Editable study-time estimates per topic.
- Daily study preferences.
- Study and revision scheduling across courses.
- Pending, Completed, and Missed session statuses.
- Manual replanning and plan archiving.
- AI recommendations with explicit student approval.
- Signed, expiring approval proposals.
- Calculated scheduling facts and validated limit-change claims.
- One explanation-repair retry with a factual fallback.
- Code-generated final scheduling explanations.
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

Dependency versions are pinned in `requirements.txt`.

## Project Structure

| Location | Responsibility |
| --- | --- |
| `accounts/` | Accounts, authentication, and registration |
| `evaluation/` | Synthetic cases, scoring, runners, and saved reports |
| `planner/ai/` | OpenAI integration, tools, validation, and explanation generation |
| `planner/ai/prompts/` | Markdown instructions for both AI features |
| `planner/api/` | JSON endpoints and shared API decorator |
| `planner/forms/` | Input validation |
| `planner/migrations/` | Database schema history |
| `planner/models/` | Domain models and database constraints |
| `planner/services/` | Scheduling and application business logic |
| `planner/static/` | Stylesheets |
| `planner/templates/` | Server-rendered pages |
| `planner/tests/` | Automated tests |
| `planner/utils/` | Measurement and topic-scoring helpers |
| `study_planner/` | Django configuration |
| `manage.py` | Django management entry point |

## Requirements

- Python 3.10 or newer.
- PostgreSQL.
- An OpenAI API key with access to the configured model for real AI requests.

## Local Setup

Run these PowerShell commands from the project root.

### 1. Create and activate the environment

For a new environment:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If `.venv` already exists, activate it without recreating it:

```powershell
.\.venv\Scripts\Activate.ps1
```

### 2. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

### 3. Configure PostgreSQL

Create a database and an appropriate PostgreSQL account.

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

Edit `.env` with your local database details, private Django secret key,
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

The example configuration uses `gpt-4.1-mini-2025-04-14`.
The OpenAI account must have access to the configured model.

### 5. Apply migrations

```powershell
python manage.py migrate
```

### 6. Optionally create an administrator

```powershell
python manage.py createsuperuser
```

### 7. Start the server

```powershell
python manage.py runserver
```

Open http://127.0.0.1:8000/.

Django admin is available to authorized staff accounts at
http://127.0.0.1:8000/admin/.

### Visual Studio

The repository includes Visual Studio project and solution files.

Select the project's `.venv` interpreter. The startup file is `manage.py`,
with `runserver` configured as the script argument.

## Scheduling Rules

- Daily study time is shared across selected courses.
- Each selected course requires one exam and one syllabus with extracted topics.
- Earlier exams are prioritized.
- Each topic receives its estimated study time plus 15 minutes of revision.
- Sessions must be scheduled before their exam dates.
- Work may be split across days.
- Only one study plan per user may be Active.
- Archived plans have read-only session statuses.
- Session snapshots preserve historical names and deadlines when source
  records are changed or deleted.

Manual replanning uses the plan's existing daily limit.
It preserves completed sessions and reschedules Pending and Missed work.

## Shared OpenAI Configuration

Both AI features use `planner/ai/openai_client.py`.

The shared client reads the key and model through Django settings.
Its timeout is 60 seconds, SDK automatic retries are disabled,
and requests use `store=False`.

SDK errors are translated into `AIServiceError`.
Each feature translates this into its own user-facing error type.

Prompts are loaded as UTF-8 text from:

- `planner/ai/prompts/topic_extraction.md`
- `planner/ai/prompts/plan_review.md`

The plan-review agent has a separate application-level explanation-repair
retry. Disabling SDK retries does not disable this repair attempt.

## AI Topic Extraction

The application extracts text from an owned syllabus and sends it to OpenAI.

The response must follow a strict JSON schema. Python validates titles,
descriptions, field names, topic count, and duplicate titles before saving.

Extracted topics initially receive a 60-minute study estimate.
Students should review the extracted content and adjust estimates before
generating a plan.

## AI Plan Review

### Student input

The student supplies:

- A valid resume date.
- A maximum acceptable daily study limit.
- A preference for a manageable workload or finishing sooner.

The resume date is when rescheduling starts, not an exam deadline.

### Server-calculated options and facts

The server runs the replanning scheduler for candidate daily limits.

Candidates start at the current limit and increase in 15-minute steps.
The exact maximum is also considered.

Only feasible options are retained. Each includes:

- Daily study limit.
- Projected finish date.
- Number of study days.
- Peak scheduled daily workload.

Python also calculates:

- Whether unfinished work remains.
- Whether the current daily limit has a feasible replacement.
- The current-limit replacement's finish date.
- The earliest feasible finish date.
- Days saved by each option compared with the current-limit replacement.

The agent receives progress totals, feasible options, calculated facts,
daily limits, the resume date, and the student's preference.
Syllabus text, topic names, and individual exam deadlines are not included
in the review input.

### AI decision and validation

The agent proposes one of three actions:

- `keep_current_plan`
- `replan_unfinished_work`
- `cannot_fit`

Python rejects unoffered daily limits, keeping a schedule with missed or
overdue work, and reporting infeasibility when feasible options exist.

Keeping the daily limit is different from keeping the existing schedule.
Missed work can require a replacement schedule at the same daily limit.

The tool also requires `limit_change_type`:

| Value | Meaning |
| --- | --- |
| `not_needed` | No daily-limit increase is proposed |
| `preference` | A higher limit is selected while the current limit remains feasible |
| `required` | A higher feasible limit is selected because the current limit has no feasible replacement |

Keeping the plan and reporting `cannot_fit` use `not_needed`
because neither action proposes a daily-limit increase.

Python validates this classification against the selected option and
current-limit feasibility.

### Explanation repair and final rendering

The agent's explanation is checked for its structured claim and specified
contradictory capacity wording.

If the initial decision is valid but its explanation fails these checks,
the application requests one repair. The repair must preserve the validated
action and daily limit.

If the repair fails, the original validated decision is retained.

Invalid initial decisions are rejected rather than repaired by this
explanation-only retry.

For every returned proposal, Python generates the final displayed explanation
from the validated decision and scheduling facts. Model-written prose is not
displayed, even when it passes the explanation checks.

The final explanation reports relevant limits, finish dates, days saved,
and whether an increase is optional or required. It does not claim that
every feasible recommendation optimally matches the preference rubric.

This design is stricter than displaying a model-written reasoning sentence
alongside code-generated facts.

The generated explanation is used by the proposal preview, approval token,
agent history, and evaluation output.

### Approval and application

Requesting a proposal does not change the study plan.

A replacement requires explicit student approval. Its signed token:

- Expires after 10 minutes.
- Is tied to the account and plan.
- Includes a fingerprint of the reviewed plan and sessions.
- Is rejected if the reviewed plan or progress changes.

The AI request finishes before database locks are taken.
The plan is checked again under the lock.

On approval, feasibility is recalculated inside a transaction before creating
the replacement plan.

Completed work is preserved, the original plan is archived, and the
replacement becomes Active. Saved Study settings are unchanged.

Approval does not make another OpenAI request.

## Django Admin

These Planner models are registered as read-only:

- Course
- Exam
- Syllabus
- Topic
- StudyPlan
- StudySession
- AgentLog

Authorized administrators can inspect, search, and filter records.
Adding, changing, deleting, and bulk actions are disabled for these registrations.

The syllabus admin omits the storage file field.
Application downloads require authentication and ownership.

Existing User and Group administration retain their own permissions.

## Automated Tests

Run from the project root with the environment activated:

```powershell
python manage.py test --verbosity 2
```

The full suite passed during the October 16 explanation-fix workflow.

Coverage includes:

- Scheduling limits, deadlines, revision workload, and impossible schedules.
- Replanning calculations and replacement-plan persistence.
- Ownership protection in web views and APIs.
- API authentication, methods, and cache handling.
- OpenAI configuration and SDK error translation.
- Topic extraction validation.
- Feasible review options and input forms.
- Structured limit-change claims.
- Explanation repair and decision preservation.
- Fallback behavior after repair failures.
- Code-generated explanation facts.
- Signed approval tokens, expiry, tampering, and changed progress.
- Proposal preview, approval, and CSRF protection.
- Topic-scoring helpers and evaluation runners.
- Final explanation-consistency checks.

OpenAI calls are mocked in automated tests, so these tests use no API credit.

Database tests require PostgreSQL and permission to create a test database.
Django normally creates `test_ai_study_planner` and removes it afterward.

Passing mocked tests verifies tested application behavior.
It does not establish real-model accuracy or absence of all bugs.

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

The API uses Django session authentication.

The shared `api_view_json` decorator handles authentication,
allowed methods, and no-cache headers.

At the view layer, unauthenticated requests return 401.
Unsupported methods return 405 with an `Allow` header.
Django's CSRF middleware can reject unsafe requests before the view runs.

PATCH requests require JSON and CSRF protection.

Example body:

```json
{"status": "completed"}
```

## AI Evaluation

Saved reports are under `evaluation/results/`.

The evaluation runners make real OpenAI requests and use API credit.
They do not modify application study plans.

### Topic extraction

The expanded dataset contains six synthetic syllabus cases, including
administrative text, weekly tables, numbered subtopics, and repeated content.

The October 15 run used three repetitions per case:

| Metric | Result |
| --- | --- |
| Attempts | 18 |
| Successful extractions | 18 |
| Exact micro precision, recall, and F1 | Approximately 0.949 each |
| Fuzzy micro precision, recall, and F1 | Approximately 0.949 each |
| Fuzzy similarity threshold | 0.85 |
| Average duration | Approximately 2.08 seconds |

Report:

`evaluation/results/topic_evaluation_20261015T192749345674Z.json`

Exact matching normalizes case and whitespace.
Fuzzy matching uses character similarity with one-to-one title assignments.
Duplicate predictions count against precision.

Fuzzy matching added no matches at the selected threshold in this run.
It measures wording similarity, not semantic correctness.

Run:

```powershell
python -m evaluation.run_topic_evaluation --repetitions 3
```

### Plan-review scenarios and rubrics

Six synthetic scenarios cover:

- A completed plan.
- Missed work with a manageable-workload preference.
- The same workload with a finish-sooner preference.
- Completed work consuming capacity and requiring a higher limit.
- An insufficient maximum daily limit.
- An exam deadline already reached at the resume date.

The manageable-workload rubric selects the lowest feasible daily limit.
The finish-sooner rubric selects the earliest finish, then the lowest limit
achieving that date.

These are explicit benchmark expectations, not universal measures of the
best recommendation.

### October 16 development results

Each run below used ten repetitions per scenario: 60 attempts.

| Metric | Baseline | Before action-prompt clarification | After clarification |
| --- | ---: | ---: | ---: |
| Successful attempts | 60/60 | 56/60 | 60/60 |
| Correct actions across all attempts | 60/60 | 56/60 | 60/60 |
| Preference matches | 29/30 | 26/30 | 30/30 |
| Consistent final explanations | Not scored | 56/60 | 60/60 |
| Explanation consistency among accepted proposals | Not scored | 100% | 100% |
| Average duration | 1.590 s | 1.466 s | 1.343 s |

Baseline report:

`evaluation/results/plan_review_evaluation_20261016T195134480567Z.json`

Report before action-prompt clarification:

`evaluation/results/plan_review_evaluation_20261016T202014831810Z.json`

Latest report:

`evaluation/results/plan_review_evaluation_20261016T202401271876Z.json`

The intermediate run rejected four `keep_current_plan` recommendations
in the missed-work manageable-workload scenario.
The existing validator correctly rejected these actions.

The prompt was clarified to distinguish keeping a daily limit from
keeping the existing schedule. These failures did not recur in the
next 60-attempt run.

The latest run recorded 60 accepted proposals, 60 correct actions,
30 of 30 preference matches, and 60 consistent final explanations.

### Explanation-consistency metric

The evaluator checks the final application's explanation against:

- Current and selected daily limits.
- Feasible replacement finish dates.
- Days saved.
- Required versus optional limit increases.
- Completed-plan and infeasible-replacement statements.
- Missing or unexpected numeric values and dates.

It reuses the structured-claim and wording checks and independently
compares explanation content with scheduling options.

It reports:

- `explanation_consistent` for each attempt.
- `consistent_explanations` in the summary.
- `explanation_consistency_all_attempts`, including failed attempts.
- `explanation_consistency_accepted_proposals`, excluding failed attempts.

This measures specific consistency properties of code-generated output.
It is not a measurement of raw AI explanation accuracy or general
natural-language truthfulness.

### Running the plan-review evaluation

```powershell
python -m evaluation.run_plan_review_evaluation --repetitions 10
```

Ten repetitions is also the runner's default.

With six cases, this produces 60 attempts.
Each attempt normally makes one request and may make one additional
explanation-repair request.

Reports use `report_version: 2` for the new explanation metrics.
Older reports are retained and are not rewritten.

The runner's exit status indicates request failures.
Inspect the quality metrics separately.

### Interpretation and limitations

- Both evaluations use small synthetic datasets.
- Repeated scenarios were reused during prompt refinement.
- The latest run is a development evaluation, not an independent
  held-out benchmark.
- Passing 60 attempts does not guarantee future action accuracy.
- Invalid initial choices can still produce a rejected review.
- Raw model explanations, repair counts, and rejected raw outputs
  are not captured in these reports.
- Accepted-proposal rate is not raw model safety accuracy.
- Topic scores do not measure description quality, ordering,
  or PDF extraction quality.
- Explanation checks cover specific template properties and are not
  a general natural-language verification system.
- Results do not establish performance across real student populations
  or varied real-world syllabi.
- Network, API, database, and other untested failures remain possible.

Latency includes proposal generation, explanation repair when needed,
validation, and final explanation generation.
Scheduling-option generation and evaluation scoring are outside the
reported proposal latency.

Memory readings describe the entire local Python process.
They are before-and-after samples, not peak usage or remote model memory.
MB figures use decimal units.

Earlier reports and `Performance_Evaluation.docx` describe historical
evaluation work. Until that document is updated, use this README and
the referenced JSON reports for the October 16 results.

## Security and Uploads

- Keep `.env` and credentials private.
- Uploaded PDF and TXT files are limited to 5 MB.
- PDF extraction is limited to 50 pages.
- Extracted text is limited to 100,000 characters.
- Scanned PDFs require a text-based alternative; OCR is not implemented.
- Downloads require authentication and ownership checks.
- Uploaded files use randomly generated storage names.
- AI responses are validated before use.
- Replacement proposals require approval before application.
- Word temporary lock files matching `~$*` are ignored by Git.
- `.gitignore` does not remove files that are already tracked.
- Production requires `DEBUG=False`, appropriate allowed hosts,
  HTTPS, and a suitable deployment configuration.

## License

No license file is currently included.