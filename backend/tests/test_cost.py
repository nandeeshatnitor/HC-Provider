from models import RoleConfig
from staffing import build_staffing_plan
from cost import aggregate_daily_cost_summary, build_cost_summary
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


def test_aggregate_daily_cost_summary_sums_blocks_and_relabels():
    config = [nurse_config()]
    block_a = build_cost_summary(config, build_staffing_plan(config, schedule(8), 38), shift_hours=12)
    block_b = build_cost_summary(config, build_staffing_plan(config, schedule(8), 20), shift_hours=12)

    total = aggregate_daily_cost_summary([block_a, block_b])

    assert round(total.scheduled_cost, 2) == round(block_a.scheduled_cost + block_b.scheduled_cost, 2)
    assert round(total.recommended_cost, 2) == round(block_a.recommended_cost + block_b.recommended_cost, 2)
    assert round(total.overtime_cost, 2) == round(block_a.overtime_cost + block_b.overtime_cost, 2)
    assert round(total.float_cost, 2) == round(block_a.float_cost + block_b.float_cost, 2)
    # block_a is short (exposure) and block_b is over-staffed (waste); the
    # aggregate label must reflect the summed delta, not either block alone
    expected_label = (
        "understaffing_exposure" if total.delta > 0
        else "overstaffing_waste" if total.delta < 0
        else "on_budget"
    )
    assert total.delta_label == expected_label


def test_aggregate_daily_cost_summary_empty_list_is_on_budget():
    total = aggregate_daily_cost_summary([])
    assert total.scheduled_cost == 0
    assert total.recommended_cost == 0
    assert total.delta_label == "on_budget"
