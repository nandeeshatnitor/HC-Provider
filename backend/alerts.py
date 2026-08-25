"""Gap detection, severity, and alert content — one alert per role
currently short, describing the actual regular/overtime/float sourcing
decision made by the optimizer, not a generic "call in coverage" line.
"""
from models import RoleConfig, StaffingPlanRow


def severity(gap: int) -> str:
    if gap >= 2:
        return "high"
    if gap == 1:
        return "medium"
    return "none"  # no alert created


def recommended_action_for(row: StaffingPlanRow) -> str:
    overtime, float_ = row.coverage.overtime, row.coverage.float_
    parts = []
    if overtime > 0:
        parts.append(f"Approve {overtime} overtime shift{'s' if overtime != 1 else ''}")
    if float_ > 0:
        parts.append(f"Call in {float_} float hire{'s' if float_ != 1 else ''}")
    return " + ".join(parts) if parts else "No action needed"


def estimated_cost_for(role: RoleConfig, row: StaffingPlanRow, shift_hours: float) -> float:
    overtime_cost = row.coverage.overtime * role.hourly_rate * role.overtime_multiplier * shift_hours
    float_cost = row.coverage.float_ * role.hourly_rate * role.float_premium_multiplier * shift_hours
    return round(overtime_cost + float_cost, 2)


def alert_content_for_role(role: RoleConfig, row: StaffingPlanRow, unit_id: str, shift_hours: float) -> dict:
    """Returns the content fields for an alert on this role, or None if not short."""
    if row.gap <= 0:
        return None
    return {
        "role_id": role.role_id,
        "display_name": role.display_name,
        "gap": row.gap,
        "severity": severity(row.gap),
        "cause": f"{role.display_name} shortfall, {unit_id}",
        "recommended_action": recommended_action_for(row),
        "estimated_cost": estimated_cost_for(role, row, shift_hours),
    }
