import os
from datetime import datetime

from forecast import HourlyForecastModel

CSV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "historical_hourly.csv")


def test_backtest_metrics_are_real_and_bounded():
    model = HourlyForecastModel(CSV_PATH)
    assert model.backtest_mae >= 0
    assert 0 <= model.backtest_mape < 100  # shift-level MAPE should be well-behaved


def test_forecast_today_returns_24_points_and_marks_current_hour():
    model = HourlyForecastModel(CSV_PATH)
    today = model.forecast_today()
    assert len(today.points) == 24
    assert 0 <= today.current_hour <= 23
    assert all(p.predicted_volume >= 0 for p in today.points)


def test_total_predicted_matches_sum_of_hourly_points():
    model = HourlyForecastModel(CSV_PATH)
    today = model.forecast_today()
    expected_total = round(sum(p.predicted_volume for p in today.points))
    assert today.total_predicted == expected_total
    assert today.total_predicted > 0


def test_saturday_and_holiday_factors_are_learned_above_baseline():
    model = HourlyForecastModel(CSV_PATH)
    # generate_data.py seeds Saturday and holidays as busier than an ordinary day
    assert model.dow_factor[5] > 1.0  # Saturday (Mon=0..Sun=6)
    assert model.holiday_factor > 1.0


def test_predict_hour_breakdown_multiplies_to_predicted_volume():
    model = HourlyForecastModel(CSV_PATH)
    point = model.predict_hour(datetime(2026, 6, 20, 9))  # an arbitrary Saturday morning
    # factor fields are independently rounded for display, so allow the
    # small tolerance that reintroduces vs. the unrounded predicted_volume
    expected = point.base * point.dow_factor * point.holiday_factor
    assert abs(point.predicted_volume - expected) < 0.1


def test_shift_volume_from_now_is_positive_and_has_confidence_range():
    model = HourlyForecastModel(CSV_PATH)
    result = model.shift_volume_from_now(12)
    assert result.predicted_volume > 0
    assert result.confidence_range > 0
