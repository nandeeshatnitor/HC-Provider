"""Generate a synthetic hourly ED-arrivals dataset for the ed-main unit.

Produces one row per hour for ~365 trailing days with:
  - a bimodal intraday curve (morning rush ~9-11am, evening rush ~6-9pm,
    overnight trough ~2-5am),
  - a day-of-week multiplier (Saturdays busiest, per the brief),
  - a holiday multiplier on the dates in holidays.py (Diwali, Holi, etc.),
  - Poisson-ish count noise around each hour's expected rate.

This gives the forecast model real historical examples of "the ED gets
busier on Saturdays/holidays and in the morning/evening" to learn a
multiplier from, rather than that pattern being hardcoded into the app.
"""
import csv
import os
import sys
from datetime import date, timedelta

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from holidays import HOLIDAYS, holiday_name  # noqa: E402

RNG = np.random.default_rng(42)

DAYS = 365
END = date.today() - timedelta(days=1)
START = END - timedelta(days=DAYS - 1)

# expected arrivals per hour on an ordinary (non-holiday) weekday, index = hour of day
HOURLY_BASE = [
    1.5, 1.2, 1.0, 0.9, 0.9, 1.0, 1.4, 2.0, 3.0, 4.2, 4.8, 4.5,
    3.8, 3.4, 3.2, 3.2, 3.4, 3.8, 4.5, 5.0, 4.6, 3.8, 2.8, 2.0,
]

# Mon=0 .. Sun=6 — Saturday busiest, per the brief
DOW_FACTOR = {0: 1.05, 1: 1.0, 2: 0.98, 3: 1.0, 4: 1.05, 5: 1.25, 6: 1.12}
HOLIDAY_MULTIPLIER = 1.5


def expected_rate(d: date, hour: int) -> float:
    base = HOURLY_BASE[hour]
    dow_f = DOW_FACTOR[d.weekday()]
    hol_f = HOLIDAY_MULTIPLIER if d in HOLIDAYS else 1.0
    return base * dow_f * hol_f


def main():
    rows = []
    d = START
    while d <= END:
        for hour in range(24):
            lam = expected_rate(d, hour)
            arrivals = int(RNG.poisson(lam))
            rows.append({
                "date": d.isoformat(),
                "hour": hour,
                "day_of_week": d.weekday(),
                "is_saturday": d.weekday() == 5,
                "is_holiday": d in HOLIDAYS,
                "holiday_name": holiday_name(d) or "",
                "arrivals": arrivals,
            })
        d += timedelta(days=1)

    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "historical_hourly.csv")
    fieldnames = ["date", "hour", "day_of_week", "is_saturday", "is_holiday", "holiday_name", "arrivals"]
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows ({START} to {END}) to {out_path}")


if __name__ == "__main__":
    main()
