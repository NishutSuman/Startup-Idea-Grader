# Founder Idea — AI Evaluator

A founder submits a startup idea; a Shark-Tank-style AI panel grades it out of 100
across five business areas and returns a staged report with a verdict.

**Live demo:** _<paste your Vercel URL here>_

> Note: the brief suggested a 1–2 hour, single-input tool. I deliberately went a bit
> further — a staged, multi-domain evaluator — to show how I reason across marketing,
> product, finance, GTM, and execution. The rubric and prompts (the part that matters)
> are hand-written; AI was used for the app code, as encouraged.

## What it does
- **Detailed pitch** mode: a structured form (problem, customer, model, pricing, geography…).
- **Quick idea** mode: type one line (e.g. *"alumni management system"*). It's too thin to
  grade, so the AI proposes 3–4 assumption options per missing field; you confirm or edit,
  then it grades the steel-manned version and shows *what you told us* vs *what we assumed*.
- Choose provider (**Gemini / OpenAI / Anthropic**) and market mode (**reasoned** estimate or
  **grounded** live web data).
- Output: a 0–100 score, per-area sub-scores with reasoning, market/finance estimates, and a
  panel verdict with the questions a real panel would ask next.

## How I judge a startup (the rubric)
Hand-written in [`backend/rubric.py`](backend/rubric.py). Five stages, sixteen atoms, 100 points:

| Stage | Weight | Why it carries this weight |
|---|---|---|
| Market & Opportunity | 30 | Most startups die building something nobody urgently needs. |
| Product & Moat | 20 | The fix must be much better *and* hard to copy. |
| Business & Finance | 22 | Unit economics decide whether it can ever be a business. |
| Go-to-Market & Growth | 16 | A great product with no distribution still fails. |
| Execution & Team | 12 | The idea is only as good as the ability to build it. |

Each atom is scored 0–10 by a **focused prompt for that stage**; the weighted total is
computed **in code** (LLMs are unreliable at arithmetic). Grades: A ≥ 85 … F < 40, tuned so
an average idea lands near 50 — a deliberately tough, honest grader.

## Architecture (and the decisions behind it)
```
React (Vite)  ──HTTP──▶  FastAPI  ──▶  LLM provider (Gemini / OpenAI / Anthropic)
  two modes, toggles      staged pipeline    + optional web search (grounding)
  staged report           weighted score in code, SQLite history
```
- **Why a backend:** to keep the API key server-side (never in the browser) and to run the
  multi-stage pipeline. That is the real justification for Python — not gold-plating.
- **Provider fallback:** free Gemini models are individually flaky (retired / quota / overload),
  so the Gemini adapter falls back across several models automatically. Hardens the demo.
- **Score in code, not the model.** The model scores atoms; Python does the weighting.
- **Key safety:** keys live in `backend/.env` (gitignored). The public deploy uses a free
  Gemini key or bring-your-own; a paid key stays local.

## Run locally
**Backend**
```bash
cd backend
python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt
cp .env.example .env            # add a GEMINI_API_KEY (free) or others
./.venv/bin/uvicorn main:app --port 8000
```
**Frontend** (new terminal)
```bash
cd frontend
npm install
npm run dev                     # http://localhost:5173
```

## Deploy (free)
- **Frontend → Vercel:** import repo, root `frontend`, framework Vite. Set `VITE_API_URL` to the backend URL.
- **Backend → Render:** new Web Service, root `backend`, start `uvicorn main:app --host 0.0.0.0 --port $PORT`. Set `GEMINI_API_KEY` and `ALLOWED_ORIGIN` (your Vercel URL).

## Files
- `backend/rubric.py` — rubric + stage prompts (the thinking)
- `backend/pipeline.py` — staged evaluation + weighted scoring
- `backend/providers.py` — Gemini / OpenAI / Anthropic adapters (+ fallback)
- `backend/grounding.py` — optional live web data · `backend/db.py` — SQLite history
- `backend/main.py` — FastAPI (rate-limited, CORS)
- `frontend/src/App.jsx` — the UI
