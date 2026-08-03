# HireSense — Enhance Your Resume

Python (FastAPI) backend + vanilla HTML/CSS/JS frontend, powered by **Gemini 3.5 Flash-Lite**.

## Tech Stack
- **Backend:** FastAPI (Python), Pydantic for schema validation
- **AI:** Google Gemini 3.5 Flash-Lite, called via direct REST API (not the SDK — see note below), using native structured JSON output (`responseSchema`)
- **Frontend:** Vanilla HTML/CSS/JS (no build step) — "scanner/terminal" themed UI
- **Architecture:** 2 distinct LLM passes — `/api/analyze` (keyword alignment) and
  `/api/rewrite` (bullet rewriting) — matching the recommended prompting strategy.

## Setup

1. Get a Gemini API key: https://aistudio.google.com/apikey
2. Copy `.env.example` to `.env` and paste your key in:

GEMINI_API_KEY=your_key_here

3. Run:
```bash
   chmod +x run.sh
   ./run.sh
```
   This creates a venv, installs `requirements.txt`, and starts the server at
   `http://localhost:8000`.

   Or manually:
```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   uvicorn backend.main:app --reload --port 8000
```

4. Open `http://localhost:8000` in your browser.

## How it works

1. **Dual input** — paste the job description and your resume (Markdown) into the two panels.
2. **Pass 1 (`/api/analyze`)** — Gemini extracts skills/tools/qualifications from the JD,
   compares against the resume, and returns a match score + matched / missing / weakly-emphasized
   keyword breakdown as structured JSON.
3. **Pass 2 (`/api/rewrite`)** — Gemini finds weak bullet points (passive voice, vague verbs,
   no metrics) and rewrites them with strong action verbs, streamed live to the page as it
   generates. Where there's no real metric to draw from, it inserts `[Insert metric: ...]`
   instead of inventing a number — flagged clearly in the UI as "FILL-IN NEEDED".
4. **Output** — signal-strength match score, 3-column keyword gap summary, and a before/after
   view per rewritten bullet with one-click copy.

## Extra features

- **ATS X-Ray mode** — toggles an overlay on the resume panel showing exactly what a
  keyword-matching bot "sees": matched keywords glow green, weakly-emphasized ones glow amber,
  and everything else dims to near-invisible. High-priority missing keywords are called out
  below since they can't be highlighted in text that doesn't contain them.
- **Apply Rewrites & Rescan** — splices the AI's rewritten bullets directly into your resume
  text, then re-runs the full analysis and shows an animated score delta (e.g. `+18%`) so you
  can see the improvement land in real time.
- **Live PDF preview** — generates a styled, downloadable PDF of your resume right in the page,
  and auto-refreshes it whenever you apply rewrites and rescan.

## Project structure

resume-ai-python/
├── README.md
├── requirements.txt
├── .env.example
├── run.sh
├── backend/
│ ├── main.py # FastAPI app entrypoint, serves frontend + mounts routes
│ ├── gemini_client.py # Gemini REST client (forces structured JSON output)
│ ├── pdf_export.py # Markdown resume -> styled PDF renderer
│ ├── prompts.py # Pass 1 & Pass 2 prompt templates
│ ├── schemas.py # Pydantic models + hand-written Gemini JSON schemas
│ └── routes/
│ ├── analyze.py # POST /api/analyze (Pass 1)
│ ├── rewrite.py # POST /api/rewrite, /api/rewrite/stream (Pass 2)
│ └── export.py # POST /api/export-pdf
└── frontend/
├── index.html
├── style.css
└── app.js


## Note on Gemini auth

This project calls Gemini's REST API directly with `requests` and passes the
API key via the `x-goog-api-key` header. Google is rolling out a new key
format: newer "Authorization" keys (start with `AQ.Ab...`) require this header
and are rejected with `401 ACCESS_TOKEN_TYPE_UNSUPPORTED` if passed as the
older `?key=...` query param — which only works with legacy "Standard" keys
(`AIzaSy...`). Since AI Studio now issues Auth keys by default, the header
method is the one that works going forward. See:
https://ai.google.dev/gemini-api/docs/generate-content/api-key

## Note on Gemini's response_schema

Gemini's `responseSchema` only supports a narrow subset of JSON Schema:
`type`, `properties`, `items`, `required`, `enum`, `description`. It does
**not** support `default`, `minimum`, `maximum`, or `additionalProperties` —
these cause `"unknown field for schema"` errors. Because of this, the schemas
sent to Gemini (`GEMINI_KEYWORD_ANALYSIS_SCHEMA`, `GEMINI_BULLET_REWRITE_SCHEMA`
in `schemas.py`) are hand-written minimal dicts, kept separate from the
Pydantic models used for validating the parsed response on our own side.

## Requirements checklist mapped to this repo

- [x] **1. Dual text area input** — `frontend/index.html` (`#jd-input`, `#resume-input`)
- [x] **2. Skill & keyword alignment** — `backend/routes/analyze.py` + `backend/prompts.py` (Pass 1)
- [x] **3. AI-powered bullet rewriting** — `backend/routes/rewrite.py` + `backend/prompts.py` (Pass 2)
- [x] **4. Side-by-side output & gap summary** — `frontend/app.js` (`renderAnalysis`, `renderRewrites`)
- [x] Structured JSON output via schema — `backend/gemini_client.py` (`responseSchema`)
- [x] 2 distinct LLM passes — separate `/api/analyze` and `/api/rewrite` routes
- [x] Anti-hallucination placeholder tags — enforced in `PASS2_SYSTEM_PROMPT`