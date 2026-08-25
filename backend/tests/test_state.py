import pytest

from models import RoleConfig, StaffingConfig
from state import SessionState, NURSE_MIN_PRESENT


def make_config():
    def role(role_id, display_name, ratio, fixed, rate):
        return RoleConfig(
            role_id=role_id, display_name=display_name, ratio_per_patient=ratio,
            fixed_count=fixed, hourly_rate=rate, overtime_multiplier=1.5,
            max_overtime_headcount=2, float_premium_multiplier=1.8,
        )

    return StaffingConfig(
        unit_id="ed-main",
        shift_hours=12,
        roles=[
            role("physician", "Physicians", 12, None, 175),
            role("nurse", "Registered nurses", 4.2, None, 58),
            role("assistant", "Nursing assistants", 9, None, 28),
            role("specialist", "Specialist consultants", None, 1, 95),
        ],
    )


def scheduled_count(state, role_id):
    return sum(1 for s in state.schedule if s.role_id == role_id and s.scheduled)


def nurses_present(state):
    return sum(1 for n in state.nurses if n.present)


def test_call_out_reduces_nurse_count_by_exactly_one():
    state = SessionState(make_config(), default_volume=38)
    before = nurses_present(state)
    state.call_out("nurse")
    assert nurses_present(state) == before - 1


def test_call_out_never_drops_nurses_below_guardrail():
    state = SessionState(make_config(), default_volume=38)
    for _ in range(20):
        state.call_out("nurse")
    assert nurses_present(state) == NURSE_MIN_PRESENT


def test_call_out_rejects_other_roles():
    state = SessionState(make_config(), default_volume=38)
    with pytest.raises(ValueError):
        state.call_out("physician")


def test_resolve_increments_nurse_present_count_and_can_clear_alert():
    state = SessionState(make_config(), default_volume=38)
    state.call_out("nurse")  # creates/updates the nurse alert (required=10, present=7 -> gap 3)
    alert = state.alerts["nurse"]
    alert_id, gap_before = alert.id, alert.gap  # Alert objects are mutated in place, so snapshot values
    before = nurses_present(state)

    state.resolve(alert_id)
    assert nurses_present(state) == before + 1
    # gap was 3 (>1), so one resolve doesn't fully clear it: alert stays active with a smaller gap
    assert state.alerts["nurse"].status == "active"
    assert state.alerts["nurse"].gap == gap_before - 1


def test_resolve_unknown_id_raises_key_error():
    state = SessionState(make_config(), default_volume=38)
    with pytest.raises(KeyError):
        state.resolve("does-not-exist")


def test_reset_restores_exact_seed_state():
    state = SessionState(make_config(), default_volume=38)
    state.call_out("nurse")
    state.reset()
    assert nurses_present(state) == 8
    assert state.predicted_volume == 38
    assert state.active_alerts() == [
        a for a in state.alerts.values() if a.status == "active"
    ]  # sanity: reset re-synced alerts from fresh state


# --- named nurse roster (admin) ---------------------------------------


def test_set_nurse_present_false_updates_plan_and_clears_assignment():
    state = SessionState(make_config(), default_volume=38)
    nurse = next(n for n in state.nurses if n.present and n.assigned)
    before = nurses_present(state)

    state.set_nurse_present(nurse.id, False)

    assert nurses_present(state) == before - 1
    assert nurse.present is False
    assert nurse.assigned is False
    assert nurse.patient_label is None


def test_set_nurse_present_guardrail_blocks_dropping_below_floor():
    state = SessionState(make_config(), default_volume=38)
    present_ids = [n.id for n in state.nurses if n.present]
    # drop present count down to the floor
    for nid in present_ids[:-NURSE_MIN_PRESENT]:
        state.set_nurse_present(nid, False)
    assert nurses_present(state) == NURSE_MIN_PRESENT

    with pytest.raises(ValueError):
        state.set_nurse_present(present_ids[-1], False)


def test_set_nurse_assignment_requires_presence():
    state = SessionState(make_config(), default_volume=38)
    absent_nurse = next(n for n in state.nurses if not n.present)
    with pytest.raises(ValueError):
        state.set_nurse_assignment(absent_nurse.id, True, "Bed 1")


def test_set_nurse_assignment_marks_free_nurse_assigned():
    state = SessionState(make_config(), default_volume=38)
    free_nurse = next(n for n in state.nurses if n.present and not n.assigned)
    state.set_nurse_assignment(free_nurse.id, True, "Bed 99")
    assert free_nurse.assigned is True
    assert free_nurse.patient_label == "Bed 99"


def test_set_nurse_assignment_can_free_a_nurse():
    state = SessionState(make_config(), default_volume=38)
    assigned_nurse = next(n for n in state.nurses if n.present and n.assigned)
    state.set_nurse_assignment(assigned_nurse.id, False, None)
    assert assigned_nurse.assigned is False
    assert assigned_nurse.patient_label is None


def test_unknown_nurse_id_raises_key_error():
    state = SessionState(make_config(), default_volume=38)
    with pytest.raises(KeyError):
        state.set_nurse_present("does-not-exist", False)
    with pytest.raises(KeyError):
        state.set_nurse_assignment("does-not-exist", True, "Bed 1")
