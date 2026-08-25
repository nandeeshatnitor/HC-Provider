"""In-memory session state: current schedule, named nurse roster, current
predicted volume, and active alerts. Single global instance for this
single-session demo (see main.py) — no persistence, no auth, matches the
MVP scope.

The nurse role is treated specially: its "scheduled" headcount for the
staffing plan is derived live from the named nurse roster's `present`
flags (see _full_schedule), so the admin nurse-roster page and the main
dashboard are always looking at the same underlying truth.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from models import Alert, Nurse, StaffingConfig, StaffMember
from alerts import alert_content_for_role
from cost import build_cost_summary
from nurses import seed_nurses
from staffing import build_staffing_plan

NURSE_MIN_PRESENT = 3


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _seed_schedule() -> list[StaffMember]:
    """Seed schedule for the roles NOT covered by the named nurse roster."""
    seed: list[StaffMember] = []

    def add(role_id: str, n_scheduled: int, n_reserve: int):
        for i in range(n_scheduled):
            seed.append(StaffMember(id=f"{role_id}-{i}", role_id=role_id, scheduled=True))
        for i in range(n_reserve):
            seed.append(StaffMember(id=f"{role_id}-r{i}", role_id=role_id, scheduled=False))

    add("physician", 4, 2)
    add("assistant", 5, 3)
    add("specialist", 1, 1)
    return seed


class SessionState:
    def __init__(self, config: StaffingConfig, default_volume: int):
        self.config = config
        self.default_volume = default_volume
        self.predicted_volume = default_volume
        self.schedule: list[StaffMember] = _seed_schedule()
        self.nurses: list[Nurse] = seed_nurses()
        self.alerts: dict[str, Alert] = {}
        self._sync_alerts()

    def _full_schedule(self) -> list[StaffMember]:
        nurse_entries = [
            StaffMember(id=n.id, role_id="nurse", scheduled=n.present) for n in self.nurses
        ]
        return self.schedule + nurse_entries

    def plan(self, predicted_volume: Optional[int] = None):
        vol = self.predicted_volume if predicted_volume is None else predicted_volume
        return build_staffing_plan(self.config.roles, self._full_schedule(), vol)

    def cost_summary(self, predicted_volume: Optional[int] = None):
        return build_cost_summary(self.config.roles, self.plan(predicted_volume), self.config.shift_hours)

    def set_predicted_volume(self, vol: int):
        self.predicted_volume = vol
        self._sync_alerts()

    def _sync_alerts(self):
        plan_by_role = {row.role_id: row for row in self.plan()}
        role_by_id = {r.role_id: r for r in self.config.roles}

        for role_id, row in plan_by_role.items():
            content = alert_content_for_role(role_by_id[role_id], row, self.config.unit_id, self.config.shift_hours)
            existing = self.alerts.get(role_id)

            if content is None:
                if existing and existing.status == "active":
                    existing.status = "resolved"
                    existing.resolved_at = _now_iso()
                continue

            if existing and existing.status == "active":
                existing.gap = content["gap"]
                existing.severity = content["severity"]
                existing.recommended_action = content["recommended_action"]
                existing.estimated_cost = content["estimated_cost"]
            else:
                self.alerts[role_id] = Alert(
                    id=uuid.uuid4().hex[:8],
                    status="active",
                    created_at=_now_iso(),
                    resolved_at=None,
                    **content,
                )

    def active_alerts(self) -> list[Alert]:
        return [a for a in self.alerts.values() if a.status == "active"]

    # --- nurse roster (admin) ---------------------------------------

    def set_nurse_present(self, nurse_id: str, present: bool) -> Nurse:
        nurse = next((n for n in self.nurses if n.id == nurse_id), None)
        if nurse is None:
            raise KeyError(nurse_id)

        if not present and nurse.present:
            present_count = sum(1 for n in self.nurses if n.present)
            if present_count <= NURSE_MIN_PRESENT:
                raise ValueError(f"At least {NURSE_MIN_PRESENT} nurses must stay present at once")
            nurse.assigned = False
            nurse.patient_label = None

        nurse.present = present
        self._sync_alerts()
        return nurse

    def set_nurse_assignment(self, nurse_id: str, assigned: bool, patient_label: Optional[str]) -> Nurse:
        nurse = next((n for n in self.nurses if n.id == nurse_id), None)
        if nurse is None:
            raise KeyError(nurse_id)
        if assigned and not nurse.present:
            raise ValueError("Cannot assign a nurse who isn't present today")

        nurse.assigned = assigned
        nurse.patient_label = patient_label if assigned else None
        return nurse

    # --- scenario / demo trigger --------------------------------------

    def call_out(self, role_id: str) -> Optional[Alert]:
        if role_id != "nurse":
            raise ValueError("MVP call-out scenario only supports role_id='nurse'")
        present_nurses = [n for n in self.nurses if n.present]
        if len(present_nurses) > NURSE_MIN_PRESENT:
            nurse = present_nurses[0]
            nurse.present = False
            nurse.assigned = False
            nurse.patient_label = None
        self._sync_alerts()
        return self.alerts.get("nurse")

    def resolve(self, alert_id: str) -> Alert:
        alert = next((a for a in self.alerts.values() if a.id == alert_id and a.status == "active"), None)
        if alert is None:
            raise KeyError(alert_id)

        role_id = alert.role_id
        if role_id == "nurse":
            reserve = next((n for n in self.nurses if not n.present), None)
            if reserve:
                reserve.present = True
            else:
                self.nurses.append(Nurse(id=uuid.uuid4().hex[:8], name="Float pool nurse", present=True, assigned=False))
        else:
            reserve = next((s for s in self.schedule if s.role_id == role_id and not s.scheduled), None)
            if reserve:
                reserve.scheduled = True
            else:
                self.schedule.append(StaffMember(id=uuid.uuid4().hex[:8], role_id=role_id, scheduled=True))

        self._sync_alerts()
        return self.alerts[role_id]

    def reset(self):
        self.predicted_volume = self.default_volume
        self.schedule = _seed_schedule()
        self.nurses = seed_nurses()
        self.alerts = {}
        self._sync_alerts()
