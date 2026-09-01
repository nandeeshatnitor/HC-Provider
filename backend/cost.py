"""Cost engine: what the current schedule costs vs. what it actually
costs to responsibly source the recommended headcount (regular +
capped overtime + float), and the signed delta between them.

Acceptance (see spec discussion): the sign of `delta` must never be
mislabeled. `delta > 0` (recommended > scheduled) means the unit is
under-resourced relative to the plan — an exposure, never "savings."
"""
from models import RoleConfig, StaffingPlanRow, CostSummary


def build_cost_summary(
    config: list[RoleConfig], plan: list[StaffingPlanRow], shift_hours: float
) -> CostSummary:
    rate_by_role = {r.role_id: r for r in config}

    scheduled_cost = 0.0
    recommended_cost = 0.0
    overtime_cost = 0.0
    float_cost = 0.0

    for row in plan:
        role = rate_by_role[row.role_id]
        scheduled_cost += row.scheduled * role.hourly_rate * shift_hours

        regular_cost = row.coverage.regular * role.hourly_rate * shift_hours
        role_overtime_cost = (
            row.coverage.overtime * role.hourly_rate * role.overtime_multiplier * shift_hours
        )
        role_float_cost = (
            row.coverage.float_ * role.hourly_rate * role.float_premium_multiplier * shift_hours
        )

        recommended_cost += regular_cost + role_overtime_cost + role_float_cost
        overtime_cost += role_overtime_cost
        float_cost += role_float_cost

    delta = recommended_cost - scheduled_cost
    if delta > 0:
        label = "understaffing_exposure"
    elif delta < 0:
        label = "overstaffing_waste"
    else:
        label = "on_budget"

    return CostSummary(
        scheduled_cost=round(scheduled_cost, 2),
        recommended_cost=round(recommended_cost, 2),
        overtime_cost=round(overtime_cost, 2),
        float_cost=round(float_cost, 2),
        delta=round(delta, 2),
        delta_label=label,
    )


def aggregate_daily_cost_summary(block_summaries: list[CostSummary]) -> CostSummary:
    """Sums several shift-length CostSummary blocks (e.g. today's day-half
    and night-half) into one whole-day total, re-deriving the delta label
    from the summed totals rather than summing the per-block labels."""
    scheduled_cost = sum(b.scheduled_cost for b in block_summaries)
    recommended_cost = sum(b.recommended_cost for b in block_summaries)
    overtime_cost = sum(b.overtime_cost for b in block_summaries)
    float_cost = sum(b.float_cost for b in block_summaries)

    delta = recommended_cost - scheduled_cost
    if delta > 0:
        label = "understaffing_exposure"
    elif delta < 0:
        label = "overstaffing_waste"
    else:
        label = "on_budget"

    return CostSummary(
        scheduled_cost=round(scheduled_cost, 2),
        recommended_cost=round(recommended_cost, 2),
        overtime_cost=round(overtime_cost, 2),
        float_cost=round(float_cost, 2),
        delta=round(delta, 2),
        delta_label=label,
    )
