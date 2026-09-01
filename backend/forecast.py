"""Hourly patient-arrival forecasting via a fitted regression curve.

This is a real (if small) ML model: ordinary least-squares linear
regression (scikit-learn) fit on:
  - a 2-harmonic Fourier expansion of hour-of-day (sin/cos terms), which
    lets the model fit a smooth curve with two peaks (morning + evening)
    instead of just averaging each hour's historical arrivals,
  - one-hot day-of-week dummies (Monday is the reference day),
  - a holiday dummy.

predicted(hour, day_of_week, is_holiday) = model.predict([fourier(hour), dow_dummies, is_holiday])

The model is still explainable: dow_adjustment[d] and holiday_adjustment
are literally the fitted regression coefficients for those terms (an
additive patients/hour delta versus an ordinary Monday), and
daily_rhythm is what the curve alone predicts for that hour on an
ordinary non-holiday Monday. predicted_volume = daily_rhythm + the
applicable day-type adjustment(s) — a real, inspectable decomposition
of the regression's own output, not a separate hand-built formula.
"""
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

from holidays import HOLIDAYS, holiday_name
from models import HourPoint, ForecastResult, TodayForecast

WEEKDAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
HOUR_LABELS = [f"{h % 12 or 12} {'AM' if h < 12 else 'PM'}" for h in range(24)]

BACKTEST_DAYS = 30
FOURIER_HARMONICS = 2  # 2 harmonics is enough to fit a bimodal (morning+evening) daily curve
DOW_DUMMY_DAYS = [1, 2, 3, 4, 5, 6]  # Tue..Sun; Monday (0) is the reference category
FEATURE_COLUMNS = (
    [c for k in range(1, FOURIER_HARMONICS + 1) for c in (f"sin{k}", f"cos{k}")]
    + [f"dow_{d}" for d in DOW_DUMMY_DAYS]
    + ["is_holiday"]
)
MODEL_TYPE = "Linear regression (Fourier daily curve + day-of-week/holiday terms)"


class HourlyForecastModel:
    def __init__(self, csv_path: str, unit_id: str = "ed-main"):
        self.unit_id = unit_id
        self.df = self._load(csv_path)
        self.backtest_mape, self.backtest_mae = self._backtest(self.df)
        # the production model is fit on the full history
        self.model = self._fit(self.df)
        self.dow_adjustment, self.holiday_adjustment = self._extract_day_effects()

    @staticmethod
    def _load(csv_path: str) -> pd.DataFrame:
        df = pd.read_csv(csv_path, parse_dates=["date"])
        df["is_holiday"] = df["is_holiday"].astype(bool)
        return df.sort_values(["date", "hour"]).reset_index(drop=True)

    @staticmethod
    def _feature_frame(df: pd.DataFrame) -> pd.DataFrame:
        hours = df["hour"].astype(float)
        frame = pd.DataFrame(index=df.index)
        for k in range(1, FOURIER_HARMONICS + 1):
            angle = 2 * np.pi * k * hours / 24
            frame[f"sin{k}"] = np.sin(angle)
            frame[f"cos{k}"] = np.cos(angle)
        for d in DOW_DUMMY_DAYS:
            frame[f"dow_{d}"] = (df["day_of_week"] == d).astype(float)
        frame["is_holiday"] = df["is_holiday"].astype(float)
        return frame[FEATURE_COLUMNS]

    def _fit(self, df: pd.DataFrame) -> LinearRegression:
        model = LinearRegression()
        model.fit(self._feature_frame(df), df["arrivals"])
        return model

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

        model = self._fit(train)
        test["predicted"] = model.predict(self._feature_frame(test))
        hourly_errors = (test["arrivals"] - test["predicted"]).abs()
        hourly_mae = float(hourly_errors.mean())

        test["half"] = test["hour"] // 12
        shift_groups = test.groupby([test["date"], test["half"]])[["arrivals", "predicted"]].sum()
        shift_errors = (shift_groups["arrivals"] - shift_groups["predicted"]).abs()
        safe_actual = shift_groups["arrivals"].clip(lower=1)
        shift_mape = float((shift_errors / safe_actual).mean() * 100)

        return round(shift_mape, 1), hourly_mae

    def _extract_day_effects(self):
        coef = dict(zip(FEATURE_COLUMNS, self.model.coef_))
        dow_adjustment = {0: 0.0}  # Monday is the reference category, coefficient 0 by construction
        for d in DOW_DUMMY_DAYS:
            dow_adjustment[d] = float(coef[f"dow_{d}"])
        holiday_adjustment = float(coef["is_holiday"])
        return dow_adjustment, holiday_adjustment

    def _predict_row(self, hour: int, dow: int, is_holiday: bool) -> tuple[float, float, float]:
        """Returns (predicted_volume, daily_rhythm, day_type_adjustment)."""
        row = pd.DataFrame([{"hour": hour, "day_of_week": dow, "is_holiday": is_holiday}])
        predicted = float(self.model.predict(self._feature_frame(row))[0])

        baseline_row = pd.DataFrame([{"hour": hour, "day_of_week": 0, "is_holiday": False}])
        daily_rhythm = float(self.model.predict(self._feature_frame(baseline_row))[0])

        day_type_adjustment = predicted - daily_rhythm
        return max(0.1, predicted), daily_rhythm, day_type_adjustment

    def predict_hour(self, dt: datetime) -> HourPoint:
        d = dt.date()
        hour = dt.hour
        dow = dt.weekday()
        is_hol = d in HOLIDAYS

        predicted, daily_rhythm, day_type_adjustment = self._predict_row(hour, dow, is_hol)

        return HourPoint(
            hour=hour,
            label=HOUR_LABELS[hour],
            predicted_volume=round(predicted, 1),
            daily_rhythm=round(daily_rhythm, 2),
            day_type_adjustment=round(day_type_adjustment, 2),
            is_holiday=is_hol,
        )

    def forecast_today(
        self,
        now: datetime | None = None,
        actual_so_far: int | None = None,
        actual_as_of_hour: int | None = None,
    ) -> TodayForecast:
        now = now or datetime.now()
        today = now.date()
        points = [self.predict_hour(datetime.combine(today, datetime.min.time()) + timedelta(hours=h)) for h in range(24)]
        model_total_today = round(sum(p.predicted_volume for p in points))

        remaining_predicted = None
        revised_total_today = model_total_today
        as_of = None
        if actual_so_far is not None:
            as_of = actual_as_of_hour if actual_as_of_hour is not None else now.hour
            remaining_predicted = sum(p.predicted_volume for p in points if p.hour > as_of)
            revised_total_today = round(actual_so_far + remaining_predicted)

        return TodayForecast(
            unit_id=self.unit_id,
            date=today.isoformat(),
            day_of_week=WEEKDAY_NAMES[today.weekday()],
            is_saturday=today.weekday() == 5,
            is_holiday=today in HOLIDAYS,
            holiday_name=holiday_name(today),
            points=points,
            model_total_today=model_total_today,
            actual_so_far=actual_so_far,
            actual_as_of_hour=as_of,
            remaining_predicted=round(remaining_predicted, 1) if remaining_predicted is not None else None,
            revised_total_today=revised_total_today,
            current_hour=now.hour,
            backtest_mape=self.backtest_mape,
            hourly_mae=round(self.backtest_mae, 2),
            dow_adjustments={WEEKDAY_NAMES[d]: round(f, 2) for d, f in sorted(self.dow_adjustment.items())},
            holiday_adjustment=round(self.holiday_adjustment, 2),
            model_type=MODEL_TYPE,
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
