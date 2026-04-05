# Agentic PR Auditor

Production-ready, zero-database web application for multi-agent code review of GitHub pull requests.

Built for **Scarlet Hacks 2026** (Corporate Innovation track) and aligned with Focused Labs' interest in **Agentic Integration**.

## Core Features

- Accepts a public GitHub Pull Request URL
- Pulls changed file patches using **PyGithub**
- Runs a **LangGraph** state machine with three specialized Gemini agents:
  - **Agent A (Architect):** structural integrity and Drupal-style standards
  - **Agent B (Security):** leaked keys, SQL injection, logic flaws, unsafe patterns
  - **Agent C (Manager):** plain-English summary for non-technical stakeholders
- Displays a "Mission Control" dashboard with:
  - dark terminal-inspired UI
  - PR URL launcher
  - "Glass Box" thought-stream timeline (operational agent logs)
  - visual result cards for architecture grade, security signal, and PM summary

## Tech Stack

### Backend

- FastAPI
- PyGithub
- LangGraph
- google-generativeai (Gemini 1.5 Flash)
- python-dotenv

### Frontend

- Next.js (App Router)
- TypeScript
- Tailwind CSS

## Architecture

1. Client submits GitHub PR URL to `/analyze`.
2. FastAPI parses URL and fetches PR metadata + patch snippets with PyGithub.
3. LangGraph executes sequentially: Architect -> Security -> Manager.
4. Gemini Flash powers all agent evaluations.
5. API returns structured findings + timeline logs.
6. Frontend renders mission dashboard and staggered thought-stream log playback.

## Project Structure

```text
backend/
  agents.py       # LangGraph workflow + Gemini prompts
  main.py         # FastAPI server + /analyze endpoint
  requirements.txt
frontend/
  app/
    page.tsx      # Mission Control dashboard
  components/
    AuditResults.tsx
README.md
```

## Setup

## 1) Backend

```bash
cd backend
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```


## Deployment (Planned)
- Frontend: Vercel
- Backend API: Render (or Railway/Fly)

Set env vars:

- `GOOGLE_API_KEY` or `GEMINI_API_KEY` (one required)
- `GITHUB_TOKEN` (optional but recommended to avoid GitHub rate limits)
- `GEMINI_MODEL` (optional, defaults to `gemini-flash-latest`; set `gemini-1.5-flash` if your account exposes it)

Run API:

```bash
uvicorn main:app --reload --port 8000
```

## 2) Frontend

Run:

```bash
cd frontend
npm install
npm run dev
```

Optional env in `frontend/.env.local`:

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

Open `http://localhost:3000`.

## API Contract

### `POST /analyze`

Request:

```json
{
  "pr_url": "https://github.com/owner/repo/pull/123"
}
```

Response includes:

- `metadata`: PR and changed-files summary
- `architect`: grade + structural recommendations
- `security`: red/green status + flagged issues
- `manager`: plain-English impact/risk/release summary
- `logs`: timestamped thought-stream events


## Troubleshooting

- If you see "missing API key", ensure backend startup loads backend/.env and set either GOOGLE_API_KEY or GEMINI_API_KEY.
- If you see Gemini 429 quota errors, the app now returns a structured fallback result so UI cards still render; switch to a key/project with available quota for full AI analysis.
