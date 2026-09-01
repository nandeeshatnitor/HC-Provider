import os
from datetime import date, datetime, timedelta

from forecast import HourlyForecastModel

CSV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "historical_hourly.csv")


def _next_saturday(start: date) -> date:
    d = start
    while d.weekday() != 5:
        d += timedelta(days=1)
    return d


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


def test_model_total_matches_sum_of_hourly_points():
    model = HourlyForecastModel(CSV_PATH)
    today = model.forecast_today()
    expected_total = round(sum(p.predicted_volume for p in today.points))
    assert today.model_total_today == expected_total
    assert today.model_total_today > 0
    # with no actual count reported, the revised total is just the model total
    assert today.revised_total_today == today.model_total_today
    assert today.actual_so_far is None


def test_saturday_and_holiday_adjustments_are_learned_above_baseline():
    model = HourlyForecastModel(CSV_PATH)
    # generate_data.py seeds Saturday and holidays as busier than an ordinary day;
    # a regression coefficient > 0 means "more patients/hour than the Monday baseline"
    assert model.dow_adjustment[5] > 0  # Saturday (Mon=0..Sun=6)
    assert model.holiday_adjustment > 0


def test_predict_hour_breakdown_sums_to_predicted_volume():
    model = HourlyForecastModel(CSV_PATH)
    saturday = _next_saturday(date(2026, 6, 1))
    point = model.predict_hour(datetime.combine(saturday, datetime.min.time()).replace(hour=9))
    expected = point.daily_rhythm + point.day_type_adjustment
    assert abs(point.predicted_volume - expected) < 0.1


def test_holiday_flag_is_detected_on_a_known_holiday_date():
    model = HourlyForecastModel(CSV_PATH)
    point = model.predict_hour(datetime(2025, 10, 20, 12))  # Diwali, per holidays.py
    assert point.is_holiday is True


def test_shift_volume_from_now_is_positive_and_has_confidence_range():
    model = HourlyForecastModel(CSV_PATH)
    result = model.shift_volume_from_now(12)
    assert result.predicted_volume > 0
    assert result.confidence_range > 0


def test_forecast_today_blends_actual_count_with_predicted_remainder():
    model = HourlyForecastModel(CSV_PATH)
    now = datetime.now().replace(hour=12, minute=0, second=0, microsecond=0)
    today = model.forecast_today(now=now, actual_so_far=50, actual_as_of_hour=12)

    remaining = sum(p.predicted_volume for p in today.points if p.hour > 12)
    assert today.actual_so_far == 50
    assert today.actual_as_of_hour == 12
    assert round(today.remaining_predicted, 1) == round(remaining, 1)
    assert today.revised_total_today == round(50 + remaining)
