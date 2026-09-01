from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


class RoleConfig(BaseModel):
    role_id: str
    display_name: str
    ratio_per_patient: Optional[float] = None
    fixed_count: Optional[int] = None
    hourly_rate: float
    overtime_multiplier: float
    max_overtime_headcount: int
    float_premium_multiplier: float


class StaffingConfig(BaseModel):
    unit_id: str
    shift_hours: float
    roles: list[RoleConfig]


class HistoricalShift(BaseModel):
    date: str
    shift: Literal["day", "evening", "night"]
    day_of_week: int
    arrivals: int
    is_holiday: bool = False


class ForecastResult(BaseModel):
    unit_id: str
    shift_label: str
    predicted_volume: int
    confidence_range: int
    backtest_mape: float


class HourPoint(BaseModel):
    hour: int
    label: str
    predicted_volume: float
    daily_rhythm: float
    day_type_adjustment: float
    is_holiday: bool


class TodayForecast(BaseModel):
    unit_id: str
    date: str
    day_of_week: str
    is_saturday: bool
    is_holiday: bool
    holiday_name: Optional[str] = None
    points: list[HourPoint]
    model_total_today: int
    actual_so_far: Optional[int] = None
    actual_as_of_hour: Optional[int] = None
    remaining_predicted: Optional[float] = None
    revised_total_today: int
    current_hour: int
    backtest_mape: float
    hourly_mae: float
    dow_adjustments: dict[str, float]
    holiday_adjustment: float
    model_type: str


class StaffMember(BaseModel):
    id: str
    role_id: str
    scheduled: bool


class Nurse(BaseModel):
    id: str
    name: str
    present: bool
    assigned: bool
    patient_label: Optional[str] = None


class NursesResponse(BaseModel):
    nurses: list[Nurse]


class RoleCoverage(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    regular: int
    overtime: int
    float_: int = Field(serialization_alias="float", validation_alias="float")


class StaffingPlanRow(BaseModel):
    role_id: str
    display_name: str
    required: int
    scheduled: int
    gap: int
    coverage: RoleCoverage
    status: Literal["ok", "covered_overtime", "needs_float"]


class StaffingPlan(BaseModel):
    plan: list[StaffingPlanRow]


class CostSummary(BaseModel):
    scheduled_cost: float
    recommended_cost: float
    overtime_cost: float
    float_cost: float
    delta: float
    delta_label: Literal["understaffing_exposure", "overstaffing_waste", "on_budget"]


class Alert(BaseModel):
    id: str
    role_id: str
    display_name: str
    gap: int
    severity: Literal["medium", "high"]
    cause: str
    recommended_action: str
    estimated_cost: float
    status: Literal["active", "resolved"]
    created_at: str
    resolved_at: Optional[str] = None


class AlertsResponse(BaseModel):
    alerts: list[Alert]


class ScenarioResult(BaseModel):
    plan: list[StaffingPlanRow]
    cost_summary: CostSummary
    alert: Optional[Alert] = None


class ResolveResult(BaseModel):
    plan: list[StaffingPlanRow]
    cost_summary: CostSummary
    alert: Alert
