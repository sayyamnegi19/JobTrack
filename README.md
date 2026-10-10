# JobTrack

JobTrack is a job application tracking platform built with Django. It helps you
track job applications and interviews, and score your resume against any job
description with an AI-powered ATS analysis.

## Features

- Track job applications and their status
- Track interviews and view upcoming ones
- Dashboard with job-search statistics
- **Resume ATS** — score your resume, with or without a specific job:
  - Upload a PDF/DOCX/TXT resume or paste its text
  - Provide a job link, pick a tracked application, or paste a job description
  - Structured AI feedback: overall score, five category scores, matched and
    missing keywords, strengths, and prioritized improvements
  - Embedding-based semantic similarity between resume and job description
  - Full analysis history with score tracking
  - Owner-only resume downloads — uploaded files are never publicly served

## Tech Stack

- Python (3.12+), Django
- PostgreSQL
- Bootstrap 5
- Google Gemini API (free tier) — structured scoring + embeddings

## Getting Started

### Prerequisites

- Python 3.12+
- PostgreSQL running locally
- A free Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey)

### Setup

```bash
python -m venv venv
venv/bin/pip install -r requirements.txt   # Windows: venv\Scripts\pip
```

Create a `.env` file in the project root:

```
DB_NAME=jobtrack_db
DB_USER=postgres
DB_PASSWORD=yourpassword
DB_HOST=localhost
DB_PORT=5432
GEMINI_API_KEY=your-key-here
```

Optional overrides (defaults shown):

```
GEMINI_MODEL=gemini-3.8-flash
GEMINI_EMBEDDING_MODEL=gemini-embedding-2
```

Then create the tables and run the server:

```bash
venv/bin/python manage.py migrate
venv/bin/python manage.py runserver
```

Open http://127.0.0.1:8000, register an account, and use **Resume ATS** in the
navbar.

## How the Resume ATS scoring works

1. **Resume text** is extracted locally (`pypdf` for PDF, `python-docx` for
   DOCX, plain text for TXT) or taken from the paste box.
2. **Job context** is resolved with a simple precedence: a pasted description
   always wins; a link is fetched and its main content extracted
   (`trafilatura`) only when no description was pasted; with neither, a
   general ATS analysis runs.
3. **One structured Gemini call** scores five categories (keyword match,
   formatting, skills/sections, experience impact, readability) and returns
   matched/missing keywords, strengths and prioritized improvements as
   validated JSON.
4. **A free embedding call** adds a semantic similarity signal between resume
   and job description. This is supplementary and non-fatal — if it fails,
   the analysis still completes.

### Cost and quota controls

- Input caps (resume 15k chars, job description 10k), max output ~2k tokens,
  low thinking level, one scoring call per analysis.
- Per-user daily limit of 20 analyses (`ATS_DAILY_LIMIT` in settings).
- Free-tier note: Google may use free-tier API content to improve its
  products. Use a paid Gemini tier if that is not acceptable for your data.

### Security notes

- Job links are fetched through an SSRF guard: only `http`/`https`, only
  globally routable IPs (loopback, private, link-local and cloud-metadata
  addresses are blocked), every redirect hop re-validated, with timeouts and
  a response size cap.
- Uploaded resumes live under `media/` (gitignored) and are only downloadable
  through an authenticated, owner-checked view. Deleting a resume also
  deletes its file from disk.

## Tests

```bash
venv/bin/python manage.py test resumes
```

All external calls (Gemini API, job page fetching) are mocked, so the suite
runs offline and finishes in a couple of seconds.

## Project Structure

| App | Purpose |
|---|---|
| `accounts` | Custom email-based user model, register/login/logout |
| `applications` | Job application tracking |
| `interviews` | Interview scheduling and tracking |
| `dashboard` | Aggregated job-search statistics |
| `resumes` | Resume ATS: parsing, job fetching, AI scoring, history |
