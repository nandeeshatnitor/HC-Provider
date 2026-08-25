# AI Hospital Staffing Assistant — MVP Technical Spec

Status: Draft v2.0 · For spec-driven development · Build window: 14 days
Companion docs: `AI_Hospital_Staffing_MVP_Requirements.docx` (product scope), `staffing_dashboard_wireframe.html` (UI reference — numbers below match it exactly)

---

## 1. Overview

A single-page web app for one hospital unit that: (1) forecasts next-shift patient volume, (2) derives required headcount across **multiple staff roles** (physicians, registered nurses, nursing assistants, on-call specialists) and compares it to the scheduled staff, (3) translates that into **operational cost** — scheduled vs. recommended dollar figures — and (4) detects and alerts on a staffing gap triggered by a simulated event (call-out), including the cost of covering it.

This spec is implementation-ready: every number, threshold, and endpoint below is a decision, not a placeholder. Change values here first if requirements change, then implement — that's the point of spec-driven development.

### 1.1 Goals

- One unit, one shift, one continuous end-to-end flow: forecast → multi-role plan → cost → alert → resolve.
- Every number on screen is computed from a real function, not hardcoded copy.
- Staffing ratios and pay rates live in **one config, not scattered constants** — swappable for a real dataset without touching calculation code (see §4).
- Runs entirely on synthetic/local data. No external integrations, no auth, no PHI.

### 1.2 Non-Goals (explicitly out of scope for MVP)

- Multi-unit, multi-shift, or multi-facility support.
- Real EHR/ADT, HR/payroll, or scheduling-system integration.
- Real pay-scale, benefits, differential, or union rate data — cost model uses the illustrative rate table in §4.2 unless a real one is supplied.
- OR block scheduling/optimization.
- Real-time streaming infrastructure (websockets, message queues). The "real-time" alert is triggered synchronously by a user action, not a live feed.
- Authentication, authorization, audit logging, HIPAA controls.
- Persistence beyond in-memory/session state (no database required for MVP).

---

## 2. System Architecture

```
┌─────────────────┐        HTTPS/JSON        ┌──────────────────────┐
│   Frontend SPA    │ ───────────────────────▶ │   Backend API          │
│  (React, single    │ ◀─────────────────────── │  (FastAPI or Express) │
│   page, no router) │                          │                        │
└─────────────────┘                          └──────────┬────────────┘
                                                          │
                              ┌───────────────┬───────────┼───────────────┬────────────────┐
                              │               │           │               │                │
                       ┌────────────┐ ┌──────────────┐ ┌──────────┐ ┌────────────┐ ┌───────────────┐
                       │ Forecast    │ │ Staffing rule │ │ Cost      │ │ Scenario /  │ │ staffing_     │
                       │ model       │ │ engine        │ │ engine    │ │ alert state │ │ config.json   │
                       │ (pretrained)│ │ (reads config)│ │(reads     │ │ (in-memory) │ │ (roles,       │
                       │             │ │               │ │ config)   │ │             │ │ ratios, rates)│
                       └────────────┘ └──────────────┘ └──────────┘ └────────────┘ └───────────────┘
                              │
                       ┌────────────┐
                       │ Historical  │
                       │ dataset     │
                       │ (CSV/JSON)  │
                       └────────────┘
```

The staffing rule engine and cost engine both read from the same `staffing_config` (§4.2) rather than embedding role-specific numbers in their own code — this is the key structural change from v1 of this spec.

### 2.1 Tech stack decisions

| Layer | Choice | Rationale |
|---|---|---|
| Frontend | React (Vite), plain CSS/inline styles | No routing needed, one screen; Vite for fast local dev |
| Backend | Python + FastAPI | Forecast model is Python-native (pandas/statsmodels or a light GBM); FastAPI gives typed request/response for free |
| Forecast model | `statsmodels` seasonal-naive or `scikit-learn` GradientBoostingRegressor | Fast to train on small synthetic data, easy to explain on stage |
| Config | `staffing_config.json`, loaded once at server startup | One file to edit before a demo, or to replace with a hackathon-provided dataset |
| Data | Local CSV, loaded at server startup into memory | No DB setup overhead; regenerable via a `generate_data.py` script |
| Alert/state | In-memory Python object (single global `SessionState`) | No persistence needed for a single-session demo |
| Hosting (demo) | Local dev server on both frontend/backend, or a single free-tier deploy (Render/Railway + Vercel) | Minimize infra time during the 14-day build |

If the team is stronger in Node than Python, substitute Express + a JS forecasting approach (simple moving-average/seasonal-naive implemented by hand). The contracts in §5 don't change either way.

---

## 3. Data Model

### 3.1 `HistoricalShift` (input to forecast model)

| Field | Type | Notes |
|---|---|---|
| `date` | string (ISO date) | |
| `shift` | enum: `day`, `evening`, `night` | |
| `day_of_week` | int 0–6 | derived, not stored raw if computed on load |
| `arrivals` | int | actual patient arrivals that shift |
| `is_holiday` | bool | optional feature |

### 3.2 `ForecastResult`

| Field | Type | Notes |
|---|---|---|
| `unit_id` | string | fixed value for MVP, e.g. `"ed-main"` |
| `shift_label` | string | e.g. `"Next shift — Tue night"` |
| `predicted_volume` | int | model point estimate |
| `confidence_range` | int | ± value shown in UI |
| `backtest_mape` | float | reported once at model load, surfaced in UI footer/tooltip |

### 3.3 `RoleConfig` (loaded from `staffing_config.json`, not hardcoded)

| Field | Type | Notes |
|---|---|---|
| `role_id` | string | `"physician"`, `"nurse"`, `"assistant"`, `"specialist"` for MVP; extensible |
| `display_name` | string | e.g. `"Registered nurses"` — UI never hardcodes labels |
| `ratio_per_patient` | float \| null | patients-per-staff ratio; `null` for roles not derived from volume (e.g. specialist) |
| `fixed_count` | int \| null | used instead of a ratio when `ratio_per_patient` is `null` (specialist = always 1 on call) |
| `hourly_rate` | float | standard scheduled rate, illustrative unless overridden by real data |
| `float_premium_multiplier` | float | multiplier applied to `hourly_rate` when a gap is covered via float/agency staff |

**MVP seed config** (mirrors the wireframe exactly — treat as the reference values, not fixed logic):

```json
{
  "shift_hours": 12,
  "roles": [
    { "role_id": "physician",  "display_name": "Physicians",           "ratio_per_patient": 12,  "fixed_count": null, "hourly_rate": 175, "float_premium_multiplier": 1.5 },
    { "role_id": "nurse",      "display_name": "Registered nurses",    "ratio_per_patient": 4.2, "fixed_count": null, "hourly_rate": 58,  "float_premium_multiplier": 1.5 },
    { "role_id": "assistant",  "display_name": "Nursing assistants",   "ratio_per_patient": 9,   "fixed_count": null, "hourly_rate": 28,  "float_premium_multiplier": 1.5 },
    { "role_id": "specialist", "display_name": "Specialist consultants","ratio_per_patient": null, "fixed_count": 1,   "hourly_rate": 95,  "float_premium_multiplier": 1.0 }
  ]
}
```

If the hackathon provides a real dataset with actual role mix or pay data, this file is what gets replaced — no other module should need to change.

### 3.4 `StaffMember` (mock schedule)

| Field | Type | Notes |
|---|---|---|
| `id` | string | |
| `role_id` | string | references `RoleConfig.role_id` |
| `scheduled` | bool | whether currently on the schedule for this shift |

MVP seed data: 4 physicians, 8 nurses, 5 assistants, 1 specialist on call (matches the wireframe).

### 3.5 `StaffingPlan` (derived per role, not stored — computed on request)

| Field | Type | Formula |
|---|---|---|
| `role_id` | string | |
| `required` | int | `ceil(predicted_volume / ratio_per_patient)` if ratio-based, else `fixed_count` |
| `scheduled` | int | count of `StaffMember` where `role_id` matches and `scheduled == true` |
| `status` | enum: `ok`, `short` | `scheduled >= required ? ok : short` |
| `gap` | int | `max(0, required - scheduled)` |

The plan is a **list of these**, one per configured role — not a fixed RN/CNA pair.

### 3.6 `CostSummary` (derived, not stored)

| Field | Type | Formula |
|---|---|---|
| `scheduled_cost` | float | `sum(role.scheduled × role.hourly_rate × shift_hours)` across all roles |
| `recommended_cost` | float | same, using `role.required` instead of `role.scheduled` |
| `delta` | float | `recommended_cost - scheduled_cost` |
| `delta_label` | enum: `understaffing_exposure`, `overstaffing_waste`, `on_budget` | `delta > 0` → exposure, `delta < 0` → waste, `== 0` → on budget |

### 3.7 `Alert`

| Field | Type | Notes |
|---|---|---|
| `id` | string (uuid) | |
| `role_id` | string | which role has the gap |
| `gap` | int | always > 0 when alert exists |
| `severity` | enum: `medium`, `high` | see §4.4 |
| `cause` | string | e.g. `"Nurse call-out, ed-main"` |
| `recommended_action` | string | e.g. `"Call in float coverage"` |
| `estimated_cost` | float | `gap × role.hourly_rate × role.float_premium_multiplier × shift_hours` |
| `status` | enum: `active`, `resolved` | |
| `created_at` | string (ISO datetime) | |
| `resolved_at` | string \| null | |

---

## 4. Core Business Logic

These are the load-bearing formulas. They read from `staffing_config` (§3.3) rather than embedding role-specific numbers — this is the difference between "a hardcoded rule" and "a data-driven config," and it's the thing to point to if a judge asks "why 4.2 patients per nurse, and would that work at a different hospital?"

### 4.1 Forecast

```python
# Input: last N shifts of HistoricalShift for this unit/shift-type
# Output: ForecastResult
def forecast_next_shift(history: list[HistoricalShift]) -> ForecastResult:
    # baseline: seasonal-naive (same day-of-week, same shift-type, trailing avg)
    # or: trained regressor with [day_of_week, shift, trailing_7_avg] as features
    ...
    return ForecastResult(
        predicted_volume=...,
        confidence_range=...,   # e.g. 1.3x the backtest MAE, rounded
        backtest_mape=...,
    )
```

Acceptance: model must be backtested against held-out historical data before the demo, and the resulting MAPE is the number shown in the UI — never a hardcoded "~92% accurate" claim.

### 4.2 Multi-role staffing rule

```python
def required_for_role(role: RoleConfig, predicted_volume: int) -> int:
    if role.ratio_per_patient is not None:
        return math.ceil(predicted_volume / role.ratio_per_patient)
    return role.fixed_count

def build_staffing_plan(config: list[RoleConfig], schedule: list[StaffMember], predicted_volume: int) -> list[StaffingPlan]:
    plan = []
    for role in config:
        required = required_for_role(role, predicted_volume)
        scheduled = sum(1 for s in schedule if s.role_id == role.role_id and s.scheduled)
        plan.append(StaffingPlan(
            role_id=role.role_id,
            required=required,
            scheduled=scheduled,
            status="ok" if scheduled >= required else "short",
            gap=max(0, required - scheduled),
        ))
    return plan
```

This loops over **whatever roles are in the config** — adding a fifth role later (e.g., respiratory therapist) means editing `staffing_config.json`, not this function.

### 4.3 Cost calculation

```python
def build_cost_summary(config: list[RoleConfig], plan: list[StaffingPlan], shift_hours: float) -> CostSummary:
    rate_by_role = {r.role_id: r.hourly_rate for r in config}
    scheduled_cost = sum(p.scheduled * rate_by_role[p.role_id] * shift_hours for p in plan)
    recommended_cost = sum(p.required * rate_by_role[p.role_id] * shift_hours for p in plan)
    delta = recommended_cost - scheduled_cost
    label = "understaffing_exposure" if delta > 0 else "overstaffing_waste" if delta < 0 else "on_budget"
    return CostSummary(scheduled_cost, recommended_cost, delta, label)
```

Acceptance: the sign of `delta` must never be mislabeled — a positive delta (recommended > scheduled) means the unit is *under*-resourced relative to the plan, which is an exposure, not a saving. This distinction is demo-critical; get it backwards and the pitch says the opposite of what's intended.

### 4.4 Gap detection, severity & alert cost

```python
def severity(gap: int) -> str:
    if gap >= 2:
        return "high"
    if gap == 1:
        return "medium"
    return "none"  # no alert created

def alert_cost(role: RoleConfig, gap: int, shift_hours: float) -> float:
    return gap * role.hourly_rate * role.float_premium_multiplier * shift_hours
```

Alerts are generated **per role**, not just for nurses — any role whose `StaffingPlan.status == "short"` gets an alert. This mirrors the wireframe, where raising the forecast slider alone (no call-out click) can already put physicians or assistants into a "short" state.

### 4.5 Scenario trigger ("simulate a nurse calling out")

- Action: mark one currently-scheduled `nurse` `StaffMember` as `scheduled = false`.
- Guardrail: do not let scheduled nurse count drop below 3 (prevents a nonsensical/broken demo state if clicked repeatedly).
- After mutation: recompute the full `StaffingPlan` list and `CostSummary`; regenerate alerts for any role now `short` that doesn't already have an `active` alert; update `gap`/`severity`/`estimated_cost` in place for roles that already have one, rather than duplicating.

MVP scope only wires this trigger to the nurse role, matching the wireframe's single "Simulate a nurse calling out" button — but because §4.2–§4.4 are role-agnostic, adding a second trigger (e.g., "simulate a physician running late") is a small addition, not a rewrite (see §11).

### 4.6 Resolve action

- Action: mark one currently-unscheduled `StaffMember` of the alert's `role_id` as `scheduled = true` (simulating float pool fill).
- After mutation: recompute plan and cost; if that role's status flips to `ok`, set the matching `Alert.status = "resolved"` and stamp `resolved_at`.

---

## 5. API Specification

Base path: `/api`. All responses `application/json`. No auth for MVP.

### 5.1 `GET /api/forecast`

Query params: `unit_id` (default `ed-main`), `shift` (default `next`).

Response `200`:
```json
{
  "unit_id": "ed-main",
  "shift_label": "Next shift — Tue night",
  "predicted_volume": 38,
  "confidence_range": 5,
  "backtest_mape": 11.4
}
```

### 5.2 `GET /api/staffing-plan`

Query params: `predicted_volume` (int, required — frontend passes the current forecast, including any slider-adjusted value).

Response `200`:
```json
{
  "plan": [
    { "role_id": "physician",  "display_name": "Physicians",         "required": 4,  "scheduled": 4, "status": "ok",    "gap": 0 },
    { "role_id": "nurse",      "display_name": "Registered nurses",  "required": 10, "scheduled": 8, "status": "short", "gap": 2 },
    { "role_id": "assistant",  "display_name": "Nursing assistants", "required": 5,  "scheduled": 5, "status": "ok",    "gap": 0 },
    { "role_id": "specialist", "display_name": "Specialist consultants", "required": 1, "scheduled": 1, "status": "ok", "gap": 0 }
  ]
}
```

### 5.3 `GET /api/cost-summary`

Query params: `predicted_volume` (int, required).

Response `200`:
```json
{
  "scheduled_cost": 16788,
  "recommended_cost": 18180,
  "delta": 1392,
  "delta_label": "understaffing_exposure"
}
```

### 5.4 `GET /api/alerts`

Response `200`:
```json
{
  "alerts": [
    {
      "id": "a1b2c3",
      "role_id": "nurse",
      "gap": 2,
      "severity": "high",
      "cause": "Nurse call-out, ed-main",
      "recommended_action": "Call in float coverage",
      "estimated_cost": 2088,
      "status": "active",
      "created_at": "2026-08-19T22:14:00Z",
      "resolved_at": null
    }
  ]
}
```

### 5.5 `POST /api/scenario/call-out`

Body: `{ "role_id": "nurse" }` (MVP only supports `"nurse"`; the field exists so a second trigger is additive, not breaking).

Behavior: applies §4.5. Returns the updated plan, cost summary, and any new/updated alert.

Response `200`:
```json
{
  "plan": [ "...": "as in 5.2" ],
  "cost_summary": { "...": "as in 5.3" },
  "alert": { "...": "as in 5.4, or null if still ok" }
}
```

### 5.6 `POST /api/alerts/{id}/resolve`

Behavior: applies §4.6.

Response `200`:
```json
{
  "plan": [ "...": "as in 5.2" ],
  "cost_summary": { "...": "as in 5.3" },
  "alert": { "id": "a1b2c3", "status": "resolved", "resolved_at": "2026-08-19T22:16:40Z" }
}
```

Response `404` if `id` doesn't match an active alert.

### 5.7 `POST /api/scenario/reset`

Resets scheduled staff, forecast volume, and alerts to the initial seed state. Used by the UI's "Start over" button.

Response `200`: `{ "reset": true }`

### 5.8 `GET /api/staffing-config`

Returns the loaded `staffing_config.json` verbatim, so the frontend never hardcodes role labels, ratios, or rates — it renders whatever roles the config defines.

### 5.9 Error format (all endpoints)

```json
{ "error": { "code": "string", "message": "human-readable string" } }
```

---

## 6. Frontend Spec

### 6.1 Component tree

```
<App>
  <Header />                 title, unit/shift label, "Start over" button
  <ForecastPanel />          chart + slider, calls GET /forecast on mount
  <StaffingPanel />          renders one <RoleCard> per entry in GET /staffing-config, driven by GET /staffing-plan
  <CostPanel />               two stat blocks + delta callout, driven by GET /cost-summary
  <AlertPanel />              active alert card(s) or "no active gaps" state, driven by GET /alerts
</App>
```

Note the shift from v1: `StaffingPanel` no longer hardcodes "RN" and "CNA" rows — it maps over whatever the config returns, so a role added to `staffing_config.json` shows up in the UI automatically.

### 6.2 State ownership

Single top-level state object in `<App>` (React `useState`/`useReducer` — no external state library needed):

```ts
interface AppState {
  roleConfig: RoleConfig[];          // from GET /staffing-config, fetched once
  forecast: ForecastResult;
  stagingVolume: number;             // slider value
  plan: StaffingPlanRow[];
  costSummary: CostSummary;
  alerts: Alert[];
}
```

The slider updates `stagingVolume` locally and re-fetches `GET /api/staffing-plan?predicted_volume=...` and `GET /api/cost-summary?predicted_volume=...` together (debounced ~150ms) — this reproduces the live-recompute behavior already validated in the wireframe.

### 6.3 Component contracts

**`ForecastPanel`** — Props: `forecast`, `onVolumeChange(vol)`. Renders line chart, slider, backtest MAPE caption.

**`StaffingPanel`** — Props: `plan: StaffingPlanRow[]`, `roleConfig: RoleConfig[]`. Renders one card per role: name, `scheduled` of `required`, a progress bar, and a status line. Pure display — no local state, no fetches.

**`CostPanel`** — Props: `costSummary: CostSummary`. Renders `scheduled_cost` and `recommended_cost` as stat blocks, plus a delta callout whose color/copy switches on `delta_label` (never label a shortfall as savings — see §4.3 acceptance note).

**`AlertPanel`** — Props: `alerts: Alert[]`, `onResolve(id)`, `onSimulateCallOut()`. Renders the trigger button (always visible) and one card per active alert with role, severity, gap, `estimated_cost`, and a resolve button. If no active alerts, renders the "no active gaps" state.

### 6.4 Visual reference

Component layout, spacing, colors, and interaction states are defined by `staffing_dashboard_wireframe.html`, a self-contained file with its own inline CSS — open it directly in a browser as the source of truth for visual details this spec doesn't repeat (colors, role-card styling, badge treatment). The role ratios, rates, and shift length hardcoded into that file's `<script>` block are the same values as §3.3 — keep them in sync if either changes.

---

## 7. Non-Functional Requirements (MVP-scoped only)

| Area | Requirement |
|---|---|
| Performance | All API responses return in <500ms locally; forecast model loads once at server startup, not per-request. |
| Browser support | Latest Chrome/Edge/Firefox. Layout should degrade gracefully to a single column below ~640px (matches the wireframe's responsive behavior). |
| Reliability | `POST /api/scenario/call-out` must produce a deterministic, correct alert every time it's called from the baseline state — the single most demo-critical guarantee (see §10). |
| Data privacy | No real patient data anywhere in the codebase or demo data files. |
| Config integrity | Changing `staffing_config.json` and restarting the server must be sufficient to change every role/ratio/rate shown in the UI — no other file should need edits. |

---

## 8. Repository Structure

```
staffing-assistant/
├── backend/
│   ├── main.py                     # FastAPI app, route definitions
│   ├── staffing_config.json        # roles, ratios, rates, shift_hours — see §3.3
│   ├── models.py                   # pydantic schemas matching §3
│   ├── forecast.py                 # forecast_next_shift()
│   ├── staffing.py                 # required_for_role(), build_staffing_plan()
│   ├── cost.py                     # build_cost_summary()
│   ├── alerts.py                   # severity(), alert_cost()
│   ├── state.py                    # in-memory SessionState + scenario/resolve/reset logic
│   ├── data/
│   │   ├── generate_data.py        # synthetic HistoricalShift generator
│   │   ├── calibrate_config.py     # optional: derive ratios from historical data (stretch goal)
│   │   └── historical_shifts.csv
│   └── tests/
│       ├── test_forecast.py
│       ├── test_staffing.py
│       └── test_cost.py
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/
│   │   │   ├── Header.jsx
│   │   │   ├── ForecastPanel.jsx
│   │   │   ├── StaffingPanel.jsx
│   │   │   ├── CostPanel.jsx
│   │   │   └── AlertPanel.jsx
│   │   └── api.js                  # fetch wrappers for §5 endpoints
│   └── package.json
├── staffing_dashboard_wireframe.html   # standalone visual reference, §6.4
└── README.md
```

---

## 9. Environment & Setup

```bash
# backend
cd backend
python -m venv venv && source venv/bin/activate
pip install fastapi uvicorn pandas scikit-learn
python data/generate_data.py        # regenerate synthetic dataset if needed
uvicorn main:app --reload --port 8000

# frontend
cd frontend
npm install
npm run dev                          # served on :5173, proxy /api to :8000
```

No `.env` secrets required for MVP — no external API keys, no database credentials.

---

## 10. Test Plan / Acceptance Criteria

### 10.1 Unit tests (backend, pytest)

| Test | Assertion |
|---|---|
| `required_for_role(nurse_config, 38) == 10` | `ceil(38 / 4.2) == 10` |
| `required_for_role(physician_config, 38) == 4` | `ceil(38 / 12) == 4` |
| `required_for_role(specialist_config, 38) == 1` | fixed count, ignores volume |
| `severity(2) == "high"`, `severity(1) == "medium"`, `severity(0) == "none"` | thresholds from §4.4 |
| `build_cost_summary(...).delta_label == "understaffing_exposure"` when scheduled < required | sign/label correctness — see §4.3 acceptance note |
| Call-out endpoint reduces scheduled nurse count by exactly 1 and never below 3 | guardrail from §4.5 |
| Resolve endpoint increments the correct role's scheduled count by 1 and flips alert to `resolved` | §4.6 |
| Reset endpoint restores exact seed state | §5.7 |
| Adding a role to `staffing_config.json` produces a new card in `GET /staffing-plan` without code changes | config-integrity requirement, §7 |

### 10.2 Manual QA checklist (run before every demo/dry-run — ties to the demo story beats)

- [ ] Fresh page load shows a real forecast number and chart, not a static placeholder.
- [ ] Moving the volume slider updates all four role cards and both cost figures within ~200ms, no flicker.
- [ ] At the baseline forecast, physicians and assistants show "fully staffed" and nurses show a shortfall — matches the wireframe's default state.
- [ ] The cost delta callout is colored/labeled correctly (amber "exposure" when short, not green "savings").
- [ ] Clicking "Simulate a nurse calling out" produces exactly one new/updated alert with correct gap, severity, and estimated cost.
- [ ] "Call in float coverage" resolves the alert, and the staffing panel + cost panel both update.
- [ ] "Start over" returns every panel to the exact baseline values.
- [ ] Full demo script (open → forecast → multi-role plan → cost → trigger → alert → resolve) completes in under 3 minutes with no console errors.

---

## 11. Open Questions / Assumptions To Confirm With The Team

- Confirm the illustrative ratios and rates in §3.3 against whatever the pitch narrative cites, or against a dataset if the hackathon organizers provide one — these should be the same numbers in the requirements doc, this spec, and the wireframe.
- Confirm whether the forecast model should be a real trained model with a reported MAPE (recommended) or a seasonal-naive baseline if time runs short.
- Decide whether to attempt `calibrate_config.py` (§8) — deriving ratios from historical "well-staffed" shifts instead of assuming them — as the calibration stretch goal referenced in the requirements doc §6.2. Low risk to attempt since it only touches `staffing_config.json` generation, not the API or frontend.
- Decide whether to add a second scenario trigger (e.g., "simulate a physician running late") given §4.2–§4.5 are already role-agnostic — likely a half-day addition, not a rewrite, if time allows.
- Confirm hosting plan for the live demo (local laptop vs. a deployed URL).
