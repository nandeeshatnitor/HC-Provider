from models import RoleConfig
from staffing import required_for_role


def role(**overrides):
    base = dict(
        role_id="nurse", display_name="Registered nurses", ratio_per_patient=4.2,
        fixed_count=None, hourly_rate=58, overtime_multiplier=1.5,
        max_overtime_headcount=2, float_premium_multiplier=1.8,
    )
    base.update(overrides)
    return RoleConfig(**base)


def test_required_for_role_ratio_based():
    assert required_for_role(role(), 38) == 10  # ceil(38 / 4.2)


def test_required_for_role_physician_ratio():
    phys = role(role_id="physician", ratio_per_patient=12)
    assert required_for_role(phys, 38) == 4  # ceil(38 / 12)


def test_required_for_role_fixed_count_ignores_volume():
    specialist = role(role_id="specialist", ratio_per_patient=None, fixed_count=1)
    assert required_for_role(specialist, 38) == 1
    assert required_for_role(specialist, 100) == 1
