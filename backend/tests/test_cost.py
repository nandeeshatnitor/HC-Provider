from models import RoleConfig
from staffing import build_staffing_plan
from cost import build_cost_summary
from models import StaffMember


def nurse_config(max_overtime=2):
    return RoleConfig(
        role_id="nurse", display_name="Registered nurses", ratio_per_patient=4.2,
        fixed_count=None, hourly_rate=58, overtime_multiplier=1.5,
        max_overtime_headcount=max_overtime, float_premium_multiplier=1.8,
    )


def schedule(n_scheduled: int):
    return [StaffMember(id=f"n{i}", role_id="nurse", scheduled=True) for i in range(n_scheduled)]


def test_understaffing_gives_positive_delta_and_correct_label():
    config = [nurse_config()]
    plan = build_staffing_plan(config, schedule(8), predicted_volume=38)  # required=10, scheduled=8
    summary = build_cost_summary(config, plan, shift_hours=12)
    assert summary.delta > 0
    assert summary.delta_label == "understaffing_exposure"


def test_overstaffing_gives_negative_delta_and_correct_label():
    config = [nurse_config()]
    plan = build_staffing_plan(config, schedule(12), predicted_volume=20)  # required=5, scheduled=12
    summary = build_cost_summary(config, plan, shift_hours=12)
    assert summary.delta < 0
    assert summary.delta_label == "overstaffing_waste"


def test_on_budget_when_scheduled_matches_required():
    config = [nurse_config()]
    plan = build_staffing_plan(config, schedule(10), predicted_volume=38)  # required=10, scheduled=10
    summary = build_cost_summary(config, plan, shift_hours=12)
    assert summary.delta == 0
    assert summary.delta_label == "on_budget"


def test_overtime_and_float_cost_breakdown_sums_to_recommended_cost():
    config = [nurse_config(max_overtime=1)]
    # required=11, scheduled=8 -> shortfall 3, overtime capped at 1, float 2
    plan = build_staffing_plan(config, schedule(8), predicted_volume=46)
    row = plan[0]
    assert (row.coverage.regular, row.coverage.overtime, row.coverage.float_) == (8, 1, 2)

    summary = build_cost_summary(config, plan, shift_hours=12)
    regular_cost = 8 * 58 * 12
    expected_recommended = regular_cost + summary.overtime_cost + summary.float_cost
    assert round(summary.recommended_cost, 2) == round(expected_recommended, 2)
    assert summary.overtime_cost > 0
    assert summary.float_cost > 0
