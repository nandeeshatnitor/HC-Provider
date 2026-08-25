import DailyForecastChart from "./DailyForecastChart";

export default function ForecastPanel({ forecast, todayForecast, volume, onVolumeChange }) {
  if (!forecast) return null;

  const min = Math.max(1, forecast.predicted_volume - 15);
  const max = forecast.predicted_volume + 15;

  return (
    <div className="card">
      <div className="section-title">
        <svg className="icon" viewBox="0 0 24 24" fill="none" stroke="var(--text-secondary)">
          <path d="M3 3v18h18" strokeWidth="2" strokeLinecap="round" />
          <path d="M7 15l4-4 3 3 5-6" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
        How many patients are we expecting today?
        <span className="badge badge-model" style={{ marginLeft: "auto" }}>
          Forecast model
        </span>
      </div>
      <p className="section-sub">
        Predicted arrivals per hour, learned from how this unit trends by time of day, day of
        week, and holidays. The dashed line marks right now.
      </p>

      <DailyForecastChart today={todayForecast} />

      <div className="section-title" style={{ marginTop: 22 }}>
        Staffing window
      </div>
      <p className="section-sub">
        Sum of the predicted arrivals over the staffing window — {forecast.shift_label}. Move the
        slider to see how staffing needs — and the cost of covering them — shift with demand.
      </p>

      <div className="forecast-row">
        <span className="forecast-num">{volume}</span>
        <span className="forecast-label">
          patients expected, give or take {forecast.confidence_range}
        </span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={1}
        value={volume}
        onChange={(e) => onVolumeChange(parseInt(e.target.value, 10))}
        aria-label="Adjust the predicted number of patients"
      />
      <div className="slider-labels">
        <span>Quiet shift</span>
        <span>Busy shift</span>
      </div>
      <p className="forecast-caption">
        Model backtested at {forecast.backtest_mape}% MAPE against held-out historical shifts.
      </p>
    </div>
  );
}
