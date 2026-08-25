# AI Hospital Staffing Assistant

A locally-hosted dashboard for one hospital unit that:

1. **Forecasts patient arrivals hour-by-hour for today** using an explainable multiplicative
   model (hourly baseline × day-of-week factor × holiday factor, all learned from historical
   data, not hardcoded) — shown as a smooth 24-hour curve with the current time highlighted and
   the calculation spelled out (see `backend/forecast.py`).
2. **Derives required headcount** per staff role (physicians, registered nurses, nursing
   assistants, on-call specialists) from a configurable ratio table, using the sum of predicted
   arrivals over the upcoming staffing window.
3. **Optimizes coverage at minimum cost while limiting overtime**: any shortfall is filled with
   the cheapest source first — existing staff picking up overtime, capped per role so nobody is
   pushed into heavy overtime — then float/agency staff for anything left over.
4. **Detects gaps and raises cost-aware alerts**, with a "simulate a nurse calling out" trigger
   and a resolve action, so the full predict → optimize → cost → alert → resolve loop runs live.
5. **Nurse roster admin page** — mark which named nurses are present today and which are
   currently assigned to a bed/patient vs. free; this roster is the live source of truth for the
   nurse role's headcount on the main dashboard.

`AI_Hospital_Staffing_MVP_Requirements (1).docx`, `staffing_assistant_mvp_spec.md`, and
`staffing_dashboard_wireframe.html` are the original hackathon requirements/reference materials
kept for context — the wireframe was used only as a visual/UX reference; the actual staffing and
cost logic is the cost-minimizing, overtime-capped optimizer described above.

## Project layout

```
backend/    FastAPI app: forecast model, staffing rule engine, cost optimizer, alerts, API
frontend/   React (Vite) single-page dashboard
```

## Run it locally

Two terminals, both from the repo root.

**Backend** (Python 3.11+):

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # on macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
python data/generate_data.py  # regenerate the synthetic hourly dataset if needed
uvicorn main:app --reload --port 8000
```

(The bundled `.claude/launch.json` dev preview runs the backend on port 8010 to avoid clashing
with other local services — either port works, just keep the frontend's `vite.config.js` proxy
target in sync with whichever one you use.)

**Frontend** (Node 18+):

```bash
cd frontend
npm install
npm run dev                   # served on http://localhost:5173, proxies /api per vite.config.js
```

Open http://localhost:5173. No `.env`/secrets, no database, no auth — everything runs in-memory
against synthetic data, as scoped for this MVP.

## Backend tests

```bash
cd backend
pytest
```

Covers the ratio math, the optimizer's regular → overtime (capped) → float allocation order,
cost sign/label correctness (never mislabeling a shortfall as savings), the call-out guardrail,
resolve/reset behavior, and the forecast backtest.

## Configuration

- `backend/staffing_config.json` — single source of truth for role list, patient ratios, hourly
  rates, overtime multiplier/cap, and float premium multiplier. Editing it and restarting the
  backend changes every role/number shown in the UI — no other file needs to change.
- `backend/holidays.py` — the illustrative holiday calendar (Diwali, Holi, etc.) the data
  generator and forecast model use to learn a holiday demand multiplier.
- `backend/nurses.py` — the seed nurse roster (name, present, assigned, patient/bed label) shown
  on the Nurse Roster admin page.

## Out of scope for this MVP

Multi-unit/multi-shift support, real EHR/payroll integration, real pay-scale data, named-individual
scheduling for roles other than nurses, authentication, and persistence beyond in-memory session
state (a server restart resets everything to the seed data).
