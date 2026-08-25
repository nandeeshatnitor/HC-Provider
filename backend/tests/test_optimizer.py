from models import RoleConfig
from optimizer import allocate_role_coverage, coverage_status


def role(**overrides):
    base = dict(
        role_id="nurse", display_name="Registered nurses", ratio_per_patient=4.2,
        fixed_count=None, hourly_rate=58, overtime_multiplier=1.5,
        max_overtime_headcount=2, float_premium_multiplier=1.8,
    )
    base.update(overrides)
    return RoleConfig(**base)


def test_no_shortfall_uses_only_regular():
    cov = allocate_role_coverage(role(), required=8, scheduled=8)
    assert (cov.regular, cov.overtime, cov.float_) == (8, 0, 0)
    assert coverage_status(cov) == "ok"


def test_shortfall_within_overtime_cap_uses_no_float():
    cov = allocate_role_coverage(role(max_overtime_headcount=2), required=10, scheduled=8)
    assert (cov.regular, cov.overtime, cov.float_) == (8, 2, 0)
    assert coverage_status(cov) == "covered_overtime"


def test_shortfall_beyond_overtime_cap_spills_to_float():
    cov = allocate_role_coverage(role(max_overtime_headcount=1), required=11, scheduled=8)
    # shortfall=3, overtime capped at 1, remaining 2 must go to float
    assert (cov.regular, cov.overtime, cov.float_) == (8, 1, 2)
    assert coverage_status(cov) == "needs_float"


def test_overstaffed_uses_only_required_as_regular():
    cov = allocate_role_coverage(role(), required=5, scheduled=8)
    assert (cov.regular, cov.overtime, cov.float_) == (5, 0, 0)
    assert coverage_status(cov) == "ok"
