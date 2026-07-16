# Build Plan — Founder Idea AI Evaluator (Mesa assignment)

## 0. What they grade (keep this on top)
1. How you think about startups → **the rubric + stage prompts** (the star)
2. Your prompting skill → **one focused prompt per stage**
3. You can run a coding environment → **a clean full-stack app, deployed**

We deliberately exceed the "1–2 hour / one box" brief to show range. README will say so in one line, so it reads as intentional, not as missing the brief.

## 1. Scope (confirmed with Nishut)
- Multi-stage, atomised rubric across business domains (Shark-Tank panel).
- Two input modes: structured pitch form + quick idea (with AI assumption chips).
- Market grounding: user chooses **Reasoned estimate** or **Grounded (live web data)**.
- Providers: **Anthropic (default, Claude Haiku), OpenAI, Gemini**.
- Stack: **React (Vite) + FastAPI (Python) + SQLite (history)**.
- Key safety: office Anthropic key in backend `.env`, **never** on a public host. Public demo = bring-your-own-key.

## 2. Architecture
```
React (Vite) frontend  ──HTTPS──▶  FastAPI backend  ──▶  LLM provider (Anthropic/OpenAI/Gemini)
   two input modes                  staged pipeline        + optional web search (grounding)
   provider + grounding toggle      key from env OR request
   renders staged report            rate-limited
                                     └─▶ SQLite (evaluation history)
```
**Why a backend:** to keep the API key server-side (never in the browser) and to run the multi-stage pipeline + web search. This is the architectural justification for Python — not gold-plating.
**Why score in code:** the model returns per-atom scores; the weighted total is computed in Python so arithmetic is deterministic and auditable.

## 3. Repo structure
```
founder-idea-evaluator/
├── frontend/            # React + Vite
│   ├── src/App.jsx      # modes, form, provider/grounding toggles, report view
│   ├── src/api.js       # calls backend /evaluate, /expand, /history
│   └── src/components/  # InputForm, QuickInput, StageReport, ScoreCard
├── backend/
│   ├── main.py          # FastAPI app, CORS, rate limit, routes
│   ├── pipeline.py      # the staged evaluation orchestration
│   ├── rubric.py        # THE RUBRIC (stages, atoms, weights) + stage prompts
│   ├── providers.py     # Anthropic / OpenAI / Gemini adapters (one interface)
│   ├── grounding.py     # web-search for live market data (optional mode)
│   ├── db.py            # SQLite history
│   ├── requirements.txt
│   └── .env.example     # names only, no secrets
├── .gitignore           # .env, node_modules, *.db, dist
├── README.md            # usage + architecture + rubric rationale + "why beyond brief"
└── BUILD_PLAN.md        # this file
```

## 4. The rubric (5 stages, 16 atoms, total 100)
Lives in `backend/rubric.py`. Weights are Nishut's to tune before the interview.

| Stage (domain) | Atoms (points) | Stage |
|---|---|---|
| **1. Market & Opportunity** | Problem severity (10) · Market size TAM/SAM/SOM (8) · Why-now (5) · Competition (7) | **30** |
| **2. Product & Moat** | Differentiation (8) · Defensibility (7) · Feasibility (5) | **20** |
| **3. Business & Finance** | Business model (6) · Unit economics CAC/LTV/margin (9) · Capital efficiency (7) | **22** |
| **4. Go-to-Market & Growth** | Distribution/marketing (6) · Partnerships (4) · Retention (6) | **16** |
| **5. Execution & Team** | Founder-market fit (6) · Operations/scalability (4) · Red flags (2) | **12** |

Each atom scored 0–10 → multiplied by its weight → summed to 0–100 in code. Grade bands A≥85 … F<40 (tough-but-fair; average idea ≈ 50).

## 5. The pipeline (stage-by-stage, each its own prompt)
`backend/pipeline.py` runs:
- **Stage 0 — Intake/normalise.**
  - Mode A (form): assemble a canonical brief from the fields.
  - Mode B (quick idea): `/expand` first — AI proposes **3–4 assumption options per missing field** (customer, model, geography, pricing…). User picks a chip or edits a box, then grades. The final report shows **"what you told us" vs "what we assumed."**
- **Stage 1 — Market & Opportunity.** If grounding = live, `grounding.py` runs a web search, feeds real reference points (market size, demographics) with source links into the prompt. Else reasoned Fermi estimates with stated assumptions.
- **Stages 2–5.** One focused prompt each, scoring only that stage's atoms, returning strict JSON (score + reasoning + evidence + concerns per atom).
- **Final — Synthesis.** Weighted total (code), grade, a Shark-Tank verdict ("I'm out" / "I'm in, with conditions"), top strengths, key risks, and the 3–5 questions a panel would ask next.

Each stage prompt uses: **role** (domain expert investor) · **rubric injection** · **calibration** (avg = 5, no flattery) · **grounding** (judge only what's given + provided data) · **strict JSON**.

## 6. Providers & key handling
- `providers.py`: one `complete(system, user, json=True)` interface, three adapters.
  - Anthropic default model: **claude-haiku-4-5** (cheap + capable).
  - OpenAI: gpt-4o-mini · Gemini: gemini-1.5-flash.
- Backend uses `ANTHROPIC_API_KEY`/etc. from env **if present**, else uses a key from the request (BYO). 
- **Public deploy:** do NOT set the office key on the host → BYO only. **Local:** `.env` has office key → zero-setup for your own demo. Office key never reaches a public host or the browser.

## 7. Safety & cost control
- `.env` gitignored; `.env.example` documents names only.
- Rate limit (e.g. 10 evals/hour/IP) via slowapi.
- Cheap model + short max tokens; history lets you review spend.
- CORS locked to the deployed frontend origin.

## 8. SQLite history
Table `evaluations(id, created_at, mode, provider, grounding, input_json, result_json, total_score, grade)`.
Routes: `POST /evaluate` saves a row; `GET /history` lists recent; frontend shows a simple past-evaluations panel. (This is what justifies SQLite.)

## 9. Deployment
- Frontend → **Vercel** (Vite preset).
- Backend → **Render** free web service (`uvicorn main:app`).
- Set frontend `VITE_API_URL` to the Render URL; set backend CORS to the Vercel URL.
- Public backend env: providers optional (BYO). Local `.env`: office key for your demo.

## 10. Test plan (before + after deploy)
- Unit: weighted-score math; JSON parsing/salvage; each provider adapter with a canned key.
- Flow: Mode A full pitch; Mode B quick idea → chips → grade; grounding on/off; all 3 providers.
- 3 sample ideas checked end-to-end: a strong one, a weak one, and a vague one.
- Post-deploy smoke test on the live URLs before sending to Mesa.

## 11. Build order (phased)
1. Backend skeleton: FastAPI + providers (Anthropic) + rubric + single-stage grade. Prove one call works.
2. Full 5-stage pipeline + weighted scoring + synthesis.
3. Grounding (web search) + reasoned fallback.
4. Mode B expand (assumption chips) + Mode A form.
5. OpenAI + Gemini adapters.
6. SQLite history.
7. React UI (forms, toggles, staged report, history) — clean, not fancy.
8. Local test → deploy → smoke test.

## 12. Interview hooks (fill INTERVIEW_PREP.md as we go)
- Why 5 stages / these weights. · Why score in code. · Why a backend (key security). · Reasoned vs grounded trade-off. · How Mode B handles ungradeable ideas. · Limits of AI judging (penalises novelty; treat as coaching mirror). · "I run this pattern in production at Masai."
