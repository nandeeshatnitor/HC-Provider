"""Named nurse roster: who's present today, and who's currently assigned
to a bed/patient vs. free to take one. This is the source of truth for
the nurse role's "scheduled" headcount used by the staffing plan — an
admin marking someone absent immediately reduces nurse coverage.
"""
from models import Nurse

# (name, present, assigned, patient_label) — 8 present (6 assigned / 2 free)
# + 4 reserve/off-duty, matching the original seed of 8 scheduled nurses.
SEED_ROSTER = [
    ("Aditi Rao", True, True, "Bed 3"),
    ("Brian Lee", True, True, "Bed 5"),
    ("Carmen Diaz", True, True, "Bed 7"),
    ("Deepak Nair", True, True, "Bed 9"),
    ("Emily Chen", True, True, "Bed 12"),
    ("Farah Khan", True, True, "Bed 14"),
    ("Grace Kim", True, False, None),
    ("Hana Osei", True, False, None),
    ("Ibrahim Malik", False, False, None),
    ("Julia Novak", False, False, None),
    ("Kevin Walsh", False, False, None),
    ("Liam O'Brien", False, False, None),
]


def seed_nurses() -> list[Nurse]:
    return [
        Nurse(id=f"nurse-{i}", name=name, present=present, assigned=assigned, patient_label=label)
        for i, (name, present, assigned, label) in enumerate(SEED_ROSTER)
    ]
