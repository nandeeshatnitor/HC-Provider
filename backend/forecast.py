"""Explainable hourly patient-arrival forecasting.

Rather than a black-box regressor, this decomposes historical arrivals
multiplicatively into three learned, inspectable factors:

    predicted(hour, day_of_week, is_holiday)
        = hourly_baseline[hour] * dow_factor[day_of_week] * (holiday_factor if is_holiday else 1)

Each factor is computed from real historical data (see data/generate_data.py
for how that history was produced), not hand-set — so "Saturdays run busier"
and "holidays run busier" are genuinely learned, and the breakdown is cheap
to show verbatim in the UI (the whole point of this module).
"""
from datetime import datetime, timedelta

import pandas as pd

from holidays import HOLIDAYS, holiday_name
from models import HourPoint, ForecastResult, TodayForecast

WEEKDAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
HOUR_LABELS = [f"{h % 12 or 12} {'AM' if h < 12 else 'PM'}" for h in range(24)]

BACKTEST_DAYS = 30


class HourlyForecastModel:
    def __init__(self, csv_path: str, unit_id: str = "ed-main"):
        self.unit_id = unit_id
        self.df = self._load(csv_path)
        self.backtest_mape, self.backtest_mae = self._backtest(self.df)
        # factors used for actual predictions are fit on the full history
        self.hourly_baseline, self.dow_factor, self.holiday_factor = self._fit_factors(self.df)

    @staticmethod
    def _load(csv_path: str) -> pd.DataFrame:
        df = pd.read_csv(csv_path, parse_dates=["date"])
        df["is_holiday"] = df["is_holiday"].astype(bool)
        df = df.sort_values(["date", "hour"]).reset_index(drop=True)
        return df

    @staticmethod
    def _fit_factors(df: pd.DataFrame):
        hourly_baseline = df.groupby("hour")["arrivals"].mean()

        ratio1 = df["arrivals"] / df["hour"].map(hourly_baseline).clip(lower=0.1)
        dow_factor = ratio1.groupby(df["day_of_week"]).mean()

        ratio2 = ratio1 / df["day_of_week"].map(dow_factor).clip(lower=0.1)
        holiday_rows = ratio2[df["is_holiday"]]
        holiday_factor = float(holiday_rows.mean()) if len(holiday_rows) else 1.0

        return hourly_baseline.to_dict(), dow_factor.to_dict(), holiday_factor

    def _backtest(self, df: pd.DataFrame):
        """Returns (shift_level_mape, hourly_mae).

        Hourly MAPE is a poor metric here (counts are small, so missing a
        1-patient hour by 1 patient reads as "100% error"). We report MAE
        for the hourly chart, and a MAPE computed on 12-hour aggregates —
        the granularity actually used for staffing — as the headline
        backtested accuracy number.
        """
        cutoff = df["date"].max() - pd.Timedelta(days=BACKTEST_DAYS)
        train, test = df[df["date"] <= cutoff], df[df["date"] > cutoff].copy()
        if test.empty:
            return 0.0, 0.0

        baseline, dow, holiday = self._fit_factors(train)
        overall_mean = train["arrivals"].mean()

        def predict_row(row):
            base = baseline.get(row["hour"], overall_mean)
            dow_f = dow.get(row["day_of_week"], 1.0)
            hol_f = holiday if row["is_holiday"] else 1.0
            return base * dow_f * hol_f

        test["predicted"] = test.apply(predict_row, axis=1)
        hourly_errors = (test["arrivals"] - test["predicted"]).abs()
        hourly_mae = float(hourly_errors.mean())

        test["half"] = test["hour"] // 12
        shift_groups = test.groupby([test["date"], test["half"]])[["arrivals", "predicted"]].sum()
        shift_errors = (shift_groups["arrivals"] - shift_groups["predicted"]).abs()
        safe_actual = shift_groups["arrivals"].clip(lower=1)
        shift_mape = float((shift_errors / safe_actual).mean() * 100)

        return round(shift_mape, 1), hourly_mae

    def predict_hour(self, dt: datetime) -> HourPoint:
        d = dt.date()
        hour = dt.hour
        dow = dt.weekday()
        is_hol = d in HOLIDAYS

        base = self.hourly_baseline.get(hour, sum(self.hourly_baseline.values()) / 24)
        dow_f = self.dow_factor.get(dow, 1.0)
        hol_f = self.holiday_factor if is_hol else 1.0
        predicted = base * dow_f * hol_f

        return HourPoint(
            hour=hour,
            label=HOUR_LABELS[hour],
            predicted_volume=round(predicted, 1),
            base=round(base, 2),
            dow_factor=round(dow_f, 2),
            holiday_factor=round(hol_f, 2),
            is_holiday=is_hol,
        )

    def forecast_today(self, now: datetime | None = None) -> TodayForecast:
        now = now or datetime.now()
        today = now.date()
        points = [self.predict_hour(datetime.combine(today, datetime.min.time()) + timedelta(hours=h)) for h in range(24)]
        total_predicted = round(sum(p.predicted_volume for p in points))

        return TodayForecast(
            unit_id=self.unit_id,
            date=today.isoformat(),
            day_of_week=WEEKDAY_NAMES[today.weekday()],
            is_saturday=today.weekday() == 5,
            is_holiday=today in HOLIDAYS,
            holiday_name=holiday_name(today),
            points=points,
            total_predicted=total_predicted,
            current_hour=now.hour,
            backtest_mape=self.backtest_mape,
            hourly_mae=round(self.backtest_mae, 2),
            dow_factors={WEEKDAY_NAMES[d]: round(f, 2) for d, f in sorted(self.dow_factor.items())},
            holiday_factor=round(self.holiday_factor, 2),
        )

    def shift_volume_from_now(self, shift_hours: int, now: datetime | None = None) -> ForecastResult:
        now = now or datetime.now()
        rounded_now = now.replace(minute=0, second=0, microsecond=0)
        points = [self.predict_hour(rounded_now + timedelta(hours=h)) for h in range(shift_hours)]

        total = sum(p.predicted_volume for p in points)
        predicted_volume = max(1, round(total))
        confidence_range = max(1, round(self.backtest_mae * (shift_hours ** 0.5) * 1.3))

        end_label = points[-1].label
        shift_label = f"Now ({points[0].label}) through {end_label}"

        return ForecastResult(
            unit_id=self.unit_id,
            shift_label=shift_label,
            predicted_volume=predicted_volume,
            confidence_range=confidence_range,
            backtest_mape=self.backtest_mape,
        )
