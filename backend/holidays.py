"""Illustrative holiday calendar for the synthetic demo dataset.

Real dates for Diwali/Holi shift each year with the lunar calendar;
these are the actual 2025/2026 dates so the historical window (trailing
~365 days from "today") contains real examples of each for the model
to learn a holiday multiplier from. Not a general-purpose Indian
holiday calendar — just enough for this MVP's demo period.
"""
from datetime import date

HOLIDAYS: dict[date, str] = {
    date(2025, 8, 15): "Independence Day",
    date(2025, 10, 20): "Diwali",
    date(2025, 10, 21): "Govardhan Puja",
    date(2026, 1, 1): "New Year's Day",
    date(2026, 3, 4): "Holi",
    date(2026, 8, 15): "Independence Day",
}


def holiday_name(d: date) -> str | None:
    return HOLIDAYS.get(d)


def is_holiday(d: date) -> bool:
    return d in HOLIDAYS
