"""Multi-role staffing plan: required headcount per role vs. scheduled,
sourced via the cost-minimizing optimizer (see optimizer.py)."""
import math

from models import RoleConfig, StaffMember, StaffingPlanRow
from optimizer import allocate_role_coverage, coverage_status


def required_for_role(role: RoleConfig, predicted_volume: int) -> int:
    if role.ratio_per_patient is not None:
        return math.ceil(predicted_volume / role.ratio_per_patient)
    return role.fixed_count


def build_staffing_plan(
    config: list[RoleConfig], schedule: list[StaffMember], predicted_volume: int
) -> list[StaffingPlanRow]:
    plan = []
    for role in config:
        required = required_for_role(role, predicted_volume)
        scheduled = sum(1 for s in schedule if s.role_id == role.role_id and s.scheduled)
        coverage = allocate_role_coverage(role, required, scheduled)
        plan.append(StaffingPlanRow(
            role_id=role.role_id,
            display_name=role.display_name,
            required=required,
            scheduled=scheduled,
            gap=max(0, required - scheduled),
            coverage=coverage,
            status=coverage_status(coverage),
        ))
    return plan
