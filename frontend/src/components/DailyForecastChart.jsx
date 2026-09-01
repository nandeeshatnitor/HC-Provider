import { useEffect, useState } from "react";
import { smoothLinePath, smoothAreaPath } from "../smoothPath";

const WIDTH = 680;
const HEIGHT = 240;
const PAD_LEFT = 32;
const PAD_RIGHT = 12;
const PAD_TOP = 16;
const PAD_BOTTOM = 26;
const PLOT_W = WIDTH - PAD_LEFT - PAD_RIGHT;
const PLOT_H = HEIGHT - PAD_TOP - PAD_BOTTOM;
const BASELINE_Y = PAD_TOP + PLOT_H;

const TICK_HOURS = [0, 6, 12, 18, 23];

function fmtHourShort(h) {
  const hour = Math.floor(h) % 24;
  const label = hour % 12 || 12;
  return `${label}${hour < 12 ? "a" : "p"}`;
}

function fmtSigned(n) {
  const rounded = Math.round(n * 100) / 100;
  return rounded >= 0 ? `+${rounded}` : `${rounded}`;
}

function ActualCountForm({ today, onSubmit, onClear }) {
  const [value, setValue] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  async function handleSubmit(e) {
    e.preventDefault();
    const count = parseInt(value, 10);
    if (Number.isNaN(count) || count < 0) {
      setError("Enter a non-negative number");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await onSubmit(count);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function handleClear() {
    setBusy(true);
    setError(null);
    try {
      await onClear();
      setValue("");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="actual-count-form">
      <form onSubmit={handleSubmit} style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
        <label htmlFor="actual-count">How many patients have come in so far today?</label>
        <input
          id="actual-count"
          className="actual-count-input"
          type="number"
          min="0"
          placeholder="e.g. 40"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          disabled={busy}
        />
        <button className="btn btn-sm btn-primary" type="submit" disabled={busy}>
          Update
        </button>
        {today.actual_so_far != null && (
          <button className="btn btn-sm" type="button" onClick={handleClear} disabled={busy}>
            Clear
          </button>
        )}
      </form>
      {error && <p className="error-note" style={{ padding: 0, margin: "4px 0 0" }}>{error}</p>}
      {today.actual_so_far != null ? (
        <p className="actual-count-note">
          {today.actual_so_far} actual so far (as of {today.points[today.actual_as_of_hour]?.label}) +{" "}
          {today.remaining_predicted} predicted for the rest of the day ={" "}
          <strong>{today.revised_total_today} revised estimate</strong> (model alone said{" "}
          {today.model_total_today}).
        </p>
      ) : (
        <p className="actual-count-note">
          Not reported yet — showing the model's own prediction ({today.model_total_today}).
        </p>
      )}
    </div>
  );
}

export default function DailyForecastChart({ today, onActualCountSubmit, onActualCountClear }) {
  const [now, setNow] = useState(() => new Date());

  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 30_000);
    return () => clearInterval(id);
  }, []);

  if (!today) return null;

  const maxV = Math.max(1, ...today.points.map((p) => p.predicted_volume)) * 1.15;
  const x = (hour) => PAD_LEFT + (hour / 23) * PLOT_W;
  const y = (v) => PAD_TOP + (1 - v / maxV) * PLOT_H;

  const points = today.points.map((p) => ({ x: x(p.hour), y: y(p.predicted_volume), raw: p }));
  const linePath = smoothLinePath(points);
  const areaPath = smoothAreaPath(points, BASELINE_Y);

  const nowFracHour = now.getHours() + now.getMinutes() / 60;
  const floor = today.points[Math.floor(nowFracHour) % 24];
  const ceil = today.points[(Math.floor(nowFracHour) + 1) % 24] || floor;
  const frac = nowFracHour - Math.floor(nowFracHour);
  const currentValue = floor.predicted_volume + (ceil.predicted_volume - floor.predicted_volume) * frac;
  const markerX = x(nowFracHour);
  const markerY = y(currentValue);

  const dowEntries = Object.entries(today.dow_adjustments);
  const todayLabel = today.day_of_week;
  const displayTotal = today.actual_so_far != null ? today.revised_total_today : today.model_total_today;

  return (
    <div>
      <div className="forecast-row" style={{ marginTop: 0, marginBottom: 12 }}>
        <span className="forecast-num">{displayTotal}</span>
        <span className="forecast-label">
          patients expected in total today ({todayLabel}
          {today.is_holiday ? ` · ${today.holiday_name}` : ""})
        </span>
      </div>

      <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} style={{ width: "100%", height: "auto" }}>
        {/* horizontal gridlines */}
        {[0.25, 0.5, 0.75, 1].map((f) => (
          <line
            key={f}
            x1={PAD_LEFT}
            x2={WIDTH - PAD_RIGHT}
            y1={PAD_TOP + PLOT_H * (1 - f)}
            y2={PAD_TOP + PLOT_H * (1 - f)}
            stroke="var(--border)"
            strokeWidth="1"
          />
        ))}

        <path d={areaPath} fill="var(--accent)" opacity="0.12" />
        <path d={linePath} fill="none" stroke="var(--accent)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />

        {/* current-time marker */}
        <line x1={markerX} x2={markerX} y1={PAD_TOP} y2={BASELINE_Y} stroke="var(--navy)" strokeWidth="1.5" strokeDasharray="3 3" />
        <circle cx={markerX} cy={markerY} r="5" fill="var(--navy)" stroke="#fff" strokeWidth="2" />

        {/* hour axis labels */}
        {TICK_HOURS.map((h) => (
          <text key={h} x={x(h)} y={HEIGHT - 8} fontSize="10.5" fill="var(--text-muted)" textAnchor="middle">
            {fmtHourShort(h)}
          </text>
        ))}
      </svg>

      <div className="forecast-now-row">
        <div className="forecast-now-stat">
          <span className="forecast-now-value">{currentValue.toFixed(1)}</span>
          <span className="forecast-now-label">patients/hour expected right now ({now.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })})</span>
        </div>
        {(today.is_saturday || today.is_holiday) && (
          <span className="badge badge-sim">
            {today.is_holiday ? today.holiday_name : "Saturday"}
          </span>
        )}
      </div>

      {onActualCountSubmit && (
        <ActualCountForm today={today} onSubmit={onActualCountSubmit} onClear={onActualCountClear} />
      )}

      <details className="calc-details">
        <summary>Show the calculation</summary>
        <p className="calc-line">
          <strong>{floor.daily_rhythm}</strong> from the fitted daily curve at {floor.label}
          {" "}
          {floor.day_type_adjustment !== 0 && (
            <>
              {floor.day_type_adjustment > 0 ? "+ " : "− "}
              <strong>{Math.abs(floor.day_type_adjustment)}</strong> {todayLabel}
              {floor.is_holiday ? "/holiday" : ""} adjustment{" "}
            </>
          )}
          {"= "}
          <strong>{floor.predicted_volume}</strong> expected patients that hour.
        </p>
        <p className="calc-caption">
          Fit by linear regression on a 2-cycle Fourier daily curve + day-of-week/holiday terms.
          Backtested to within ±{today.hourly_mae} patients/hour on held-out historical data
          ({today.backtest_mape}% error at the 12-hour aggregate level used for staffing).
        </p>
        <table className="calc-table">
          <thead>
            <tr>
              <th>Day</th>
              <th>Learned adjustment</th>
            </tr>
          </thead>
          <tbody>
            {dowEntries.map(([day, adjustment]) => (
              <tr key={day} className={day === todayLabel ? "calc-row-today" : ""}>
                <td>{day}</td>
                <td>{fmtSigned(adjustment)} patients/hour</td>
              </tr>
            ))}
            <tr>
              <td>Holiday (e.g. Diwali, Holi)</td>
              <td>{fmtSigned(today.holiday_adjustment)} patients/hour</td>
            </tr>
          </tbody>
        </table>
      </details>
    </div>
  );
}
