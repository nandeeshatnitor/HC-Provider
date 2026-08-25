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

export default function DailyForecastChart({ today }) {
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

  const dowEntries = Object.entries(today.dow_factors);
  const todayLabel = today.day_of_week;

  return (
    <div>
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

      <details className="calc-details">
        <summary>Show the calculation</summary>
        <p className="calc-line">
          <strong>{floor.base}</strong> avg arrivals in the {floor.label} hour
          {" × "}
          <strong>{floor.dow_factor}×</strong> {todayLabel} factor
          {floor.is_holiday && (
            <>
              {" × "}
              <strong>{floor.holiday_factor}×</strong> holiday factor
            </>
          )}
          {" = "}
          <strong>{floor.predicted_volume}</strong> expected patients that hour.
        </p>
        <p className="calc-caption">
          Backtested to within ±{today.hourly_mae} patients/hour on held-out historical data
          ({today.backtest_mape}% error at the 12-hour aggregate level used for staffing).
        </p>
        <table className="calc-table">
          <thead>
            <tr>
              <th>Day</th>
              <th>Learned factor</th>
            </tr>
          </thead>
          <tbody>
            {dowEntries.map(([day, factor]) => (
              <tr key={day} className={day === todayLabel ? "calc-row-today" : ""}>
                <td>{day}</td>
                <td>{factor}×</td>
              </tr>
            ))}
            <tr>
              <td>Holiday (e.g. Diwali, Holi)</td>
              <td>{today.holiday_factor}×</td>
            </tr>
          </tbody>
        </table>
      </details>
    </div>
  );
}
