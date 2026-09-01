import DailyForecastChart from "./DailyForecastChart";

function fmt(n) {
  return "₹" + Math.round(n).toLocaleString("en-US");
}

export default function ForecastPanel({
  forecast,
  todayForecast,
  todayCostSummary,
  onActualCountSubmit,
  onActualCountClear,
}) {
  if (!forecast) return null;

  return (
    <div className="card">
      <div className="section-title">
        <svg className="icon" viewBox="0 0 24 24" fill="none" stroke="var(--text-secondary)">
          <path d="M3 3v18h18" strokeWidth="2" strokeLinecap="round" />
          <path d="M7 15l4-4 3 3 5-6" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
        How many patients are we expecting today?
        <span className="badge badge-model" style={{ marginLeft: "auto" }}>
          Regression model
        </span>
      </div>
      <p className="section-sub">
        A fitted regression curve (not a lookup table) — a daily rhythm learned from time of day,
        plus day-of-week and holiday adjustments. The dashed line marks right now.
      </p>

      <DailyForecastChart
        today={todayForecast}
        onActualCountSubmit={onActualCountSubmit}
        onActualCountClear={onActualCountClear}
      />

      {todayCostSummary && (
        <div className="today-cost-callout">
          <div>
            <p className="cost-stat-label">Total estimated cost for today (all shifts)</p>
            <p className="cost-stat-value">{fmt(todayCostSummary.recommended_cost)}</p>
          </div>
          <div>
            <p className="cost-stat-label">vs. current roster on the clock all day</p>
            <p className="cost-stat-value" style={{ color: "var(--text-secondary)" }}>
              {fmt(todayCostSummary.scheduled_cost)}
            </p>
          </div>
        </div>
      )}

      <div className="section-title" style={{ marginTop: 22 }}>
        Staffing window
      </div>
      <p className="section-sub">
        The staffing plan and this-shift cost below are driven automatically by the model's own
        forecast — {forecast.shift_label}, {forecast.predicted_volume} patients expected (±{forecast.confidence_range}).
      </p>
      <p className="forecast-caption">
        Model backtested at {forecast.backtest_mape}% MAPE against held-out historical shifts.
      </p>
    </div>
  );
}
