"""Cost-minimizing, overtime-capped coverage allocation.

Given a role's required headcount and its currently scheduled pool,
decide how to source the required coverage:

1. Regular (already-scheduled) staff first — cheapest, no premium.
2. Overtime from the existing pool for any shortfall, capped at
   ``max_overtime_headcount`` so people aren't pushed into heavy
   overtime.
3. Float/agency staff for anything still short beyond the overtime cap.

This greedy fill-cheapest-first order is cost-optimal as long as
``overtime_multiplier <= float_premium_multiplier`` (a documented
config convention — see staffing_config.json) since every unit of
coverage is homogeneous (one headcount for the full shift).
"""
from models import RoleConfig, RoleCoverage


def allocate_role_coverage(role: RoleConfig, required: int, scheduled: int) -> RoleCoverage:
    regular = min(required, scheduled)
    shortfall = max(0, required - scheduled)
    overtime = min(shortfall, role.max_overtime_headcount)
    float_ = shortfall - overtime
    return RoleCoverage(regular=regular, overtime=overtime, float_=float_)


def coverage_status(coverage: RoleCoverage) -> str:
    if coverage.overtime == 0 and coverage.float_ == 0:
        return "ok"
    if coverage.float_ == 0:
        return "covered_overtime"
    return "needs_float"
