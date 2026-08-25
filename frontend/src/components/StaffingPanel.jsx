import { roleColor, roleIcon } from "../roleStyle";

function statusColor(status) {
  if (status === "ok") return "var(--success)";
  if (status === "covered_overtime") return "var(--overtime)";
  return "var(--float)";
}

function statusText(row, isRatioBased) {
  if (row.status === "ok") {
    return isRatioBased ? "Fully staffed" : "Available, not volume-based";
  }
  if (row.status === "covered_overtime") {
    return `Short by ${row.gap} · covered via overtime`;
  }
  return `Short by ${row.gap} · needs float coverage`;
}

function RoleCard({ role, row }) {
  const color = roleColor(role.role_id);
  const isRatioBased = role.ratio_per_patient != null;
  const { regular, overtime, float: floatCount } = row.coverage;
  const denom = Math.max(1, row.required);
  const pct = (n) => `${Math.min(100, (n / denom) * 100)}%`;

  return (
    <div className="role-card" style={{ "--role-color": color }}>
      <div className="role-head">
        <div className="role-icon">{roleIcon(role.role_id, role.display_name)}</div>
        <span className="role-name">{role.display_name}</span>
      </div>
      <div className="role-count-row">
        <span className="role-count">{row.scheduled}</span>
        <span className="role-count-label">
          scheduled of {row.required} {isRatioBased ? "needed" : "on call"}
        </span>
      </div>
      <div className="role-bar-track">
        <div className="role-bar-seg" style={{ width: pct(regular), background: color }} />
        <div className="role-bar-seg" style={{ width: pct(overtime), background: "var(--overtime)" }} />
        <div className="role-bar-seg" style={{ width: pct(floatCount), background: "var(--float)" }} />
      </div>
      <p className="role-status" style={{ color: statusColor(row.status) }}>
        <span className="status-dot" style={{ background: statusColor(row.status) }}>
          {row.status === "ok" ? "✓" : "!"}
        </span>
        {statusText(row, isRatioBased)}
      </p>
      {(overtime > 0 || floatCount > 0) && (
        <p className="coverage-caption">
          <span className="coverage-swatch" style={{ background: color }} />
          {regular} regular
          {overtime > 0 && (
            <>
              {" · "}
              <span className="coverage-swatch" style={{ background: "var(--overtime)" }} />
              {overtime} overtime
            </>
          )}
          {floatCount > 0 && (
            <>
              {" · "}
              <span className="coverage-swatch" style={{ background: "var(--float)" }} />
              {floatCount} float
            </>
          )}
        </p>
      )}
    </div>
  );
}

export default function StaffingPanel({ roleConfig, plan }) {
  if (!roleConfig.length || !plan.length) return null;
  const planByRole = Object.fromEntries(plan.map((row) => [row.role_id, row]));

  return (
    <div className="card">
      <div className="section-title">
        <svg className="icon" viewBox="0 0 24 24" fill="none" stroke="var(--text-secondary)">
          <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" strokeWidth="2" strokeLinecap="round" />
          <circle cx="9" cy="7" r="4" strokeWidth="2" />
          <path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" strokeWidth="2" strokeLinecap="round" />
        </svg>
        How do we cover it at the lowest cost?
        <span className="badge badge-model" style={{ marginLeft: "auto" }}>
          Rule-based + optimizer
        </span>
      </div>
      <p className="section-sub">
        Each role's requirement is compared to who's scheduled. Any shortfall is filled with the
        cheapest source first — existing staff on overtime, capped so nobody is pushed into heavy
        overtime, then float/agency coverage for anything left over. Ratios, rates, and overtime
        caps are configurable, not fixed in the app.
      </p>
      <div className="role-grid">
        {roleConfig.map((role) => (
          <RoleCard key={role.role_id} role={role} row={planByRole[role.role_id]} />
        ))}
      </div>
    </div>
  );
}
