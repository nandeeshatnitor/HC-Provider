import json
import os

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from cost import aggregate_daily_cost_summary, build_cost_summary
from forecast import HourlyForecastModel
from models import (
    AlertsResponse,
    CostSummary,
    ForecastResult,
    NursesResponse,
    ResolveResult,
    ScenarioResult,
    StaffingConfig,
    StaffingPlan,
    TodayForecast,
)
from state import SessionState

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "staffing_config.json")
DATA_PATH = os.path.join(BASE_DIR, "data", "historical_hourly.csv")

with open(CONFIG_PATH) as f:
    staffing_config = StaffingConfig.model_validate(json.load(f))

forecast_model = HourlyForecastModel(DATA_PATH, unit_id=staffing_config.unit_id)
_baseline_forecast = forecast_model.shift_volume_from_now(int(staffing_config.shift_hours))

state = SessionState(config=staffing_config, default_volume=_baseline_forecast.predicted_volume)

app = FastAPI(title="AI Hospital Staffing Assistant")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def error_response(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"error": {"code": code, "message": message}})


@app.exception_handler(ValueError)
async def value_error_handler(request, exc: ValueError):
    return error_response(400, "bad_request", str(exc))


@app.exception_handler(KeyError)
async def key_error_handler(request, exc: KeyError):
    return error_response(404, "not_found", f"No matching record for id {exc}")


@app.get("/api/forecast", response_model=ForecastResult)
def get_forecast():
    return forecast_model.shift_volume_from_now(int(staffing_config.shift_hours))


@app.get("/api/forecast/today", response_model=TodayForecast)
def get_forecast_today():
    return forecast_model.forecast_today(
        actual_so_far=state.actual_patients_so_far,
        actual_as_of_hour=state.actual_as_of_hour,
    )


@app.post("/api/today/actual-count", response_model=TodayForecast)
def post_actual_count(body: dict):
    count = body.get("count")
    if count is None:
        raise ValueError("count is required")
    state.set_actual_patient_count(int(count))
    return forecast_model.forecast_today(
        actual_so_far=state.actual_patients_so_far,
        actual_as_of_hour=state.actual_as_of_hour,
    )


@app.post("/api/today/actual-count/clear", response_model=TodayForecast)
def post_clear_actual_count():
    state.clear_actual_patient_count()
    return forecast_model.forecast_today()


@app.get("/api/cost-summary/today", response_model=CostSummary)
def get_cost_summary_today():
    """Total estimated cost for the whole day: the day's predicted volume
    split into shift_hours-sized blocks (e.g. two 12-hour halves), each
    costed against the current roster via the same optimizer used for the
    single-shift cost panel, then summed."""
    today = forecast_model.forecast_today()
    shift_hours = int(staffing_config.shift_hours)
    block_summaries = []
    for start in range(0, 24, shift_hours):
        block_points = today.points[start:start + shift_hours]
        if not block_points:
            continue
        block_volume = max(1, round(sum(p.predicted_volume for p in block_points)))
        block_plan = state.plan(block_volume)
        block_summaries.append(build_cost_summary(staffing_config.roles, block_plan, shift_hours))
    return aggregate_daily_cost_summary(block_summaries)


@app.get("/api/staffing-plan", response_model=StaffingPlan)
def get_staffing_plan(predicted_volume: int = Query(..., ge=1)):
    state.set_predicted_volume(predicted_volume)
    return StaffingPlan(plan=state.plan())


@app.get("/api/cost-summary", response_model=CostSummary)
def get_cost_summary(predicted_volume: int = Query(..., ge=1)):
    state.set_predicted_volume(predicted_volume)
    return state.cost_summary()


@app.get("/api/alerts", response_model=AlertsResponse)
def get_alerts():
    return AlertsResponse(alerts=state.active_alerts())


@app.post("/api/scenario/call-out", response_model=ScenarioResult)
def post_call_out(body: dict):
    role_id = body.get("role_id", "nurse")
    alert = state.call_out(role_id)
    return ScenarioResult(plan=state.plan(), cost_summary=state.cost_summary(), alert=alert)


@app.post("/api/alerts/{alert_id}/resolve", response_model=ResolveResult)
def post_resolve(alert_id: str):
    alert = state.resolve(alert_id)
    return ResolveResult(plan=state.plan(), cost_summary=state.cost_summary(), alert=alert)


@app.post("/api/scenario/reset")
def post_reset():
    state.reset()
    return {"reset": True}


@app.get("/api/staffing-config", response_model=StaffingConfig)
def get_staffing_config():
    return staffing_config


@app.get("/api/nurses", response_model=NursesResponse)
def get_nurses():
    return NursesResponse(nurses=state.nurses)


@app.post("/api/nurses/{nurse_id}/presence", response_model=NursesResponse)
def post_nurse_presence(nurse_id: str, body: dict):
    state.set_nurse_present(nurse_id, bool(body.get("present")))
    return NursesResponse(nurses=state.nurses)


@app.post("/api/nurses/{nurse_id}/assignment", response_model=NursesResponse)
def post_nurse_assignment(nurse_id: str, body: dict):
    state.set_nurse_assignment(nurse_id, bool(body.get("assigned")), body.get("patient_label"))
    return NursesResponse(nurses=state.nurses)
