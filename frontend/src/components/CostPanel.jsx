function fmt(n) {
  return "₹" + Math.round(n).toLocaleString("en-US");
}

const DELTA_COPY = {
  understaffing_exposure: {
    bg: "var(--warning-bg)",
    fg: "var(--warning)",
    icon: "!",
    head: (d) => `${fmt(d)} under-covered`,
    body: (d) =>
      `The current schedule costs less than the recommendation because a role is short-staffed, not because it's efficient. Responsibly closing that gap with overtime/float coverage costs ${fmt(d)} more.`,
  },
  overstaffing_waste: {
    bg: "var(--danger-bg)",
    fg: "var(--danger)",
    icon: "!",
    head: (d) => `${fmt(Math.abs(d))} potential savings`,
    body: (d) =>
      `The current schedule costs more than what this shift's predicted volume actually needs. Trimming to the recommendation would free up ${fmt(Math.abs(d))}.`,
  },
  on_budget: {
    bg: "var(--success-bg)",
    fg: "var(--success)",
    icon: "✓",
    head: () => "On budget",
    body: () => "The current schedule matches what this shift's predicted volume needs. No cost gap either direction.",
  },
};

export default function CostPanel({ costSummary }) {
  if (!costSummary) return null;
  const copy = DELTA_COPY[costSummary.delta_label];
  const hasPremium = costSummary.overtime_cost > 0 || costSummary.float_cost > 0;

  return (
    <div className="card">
      <div className="section-title">
        <svg className="icon" viewBox="0 0 24 24" fill="none" stroke="var(--text-secondary)">
          <circle cx="12" cy="12" r="9" strokeWidth="2" />
          <path
            d="M12 7v10M15 9.5c0-1.4-1.3-2.5-3-2.5s-3 1-3 2.3c0 3 6 1.4 6 4.4 0 1.4-1.3 2.5-3 2.5s-3-1.1-3-2.5"
            strokeWidth="1.8"
            strokeLinecap="round"
          />
        </svg>
        What does this shift cost?
        <span className="badge badge-model" style={{ marginLeft: "auto" }}>
          Cost model
        </span>
      </div>
      <p className="section-sub">
        Labor is the largest line item in hospital operating costs. This compares what this
        shift's scheduled staff cost against the real cost of the optimizer's recommendation —
        including any overtime or float premiums needed to close a gap.
      </p>
      <div className="cost-grid">
        <div className="cost-stat">
          <p className="cost-stat-label">Scheduled cost, this shift</p>
          <p className="cost-stat-value">{fmt(costSummary.scheduled_cost)}</p>
        </div>
        <div className="cost-stat">
          <p className="cost-stat-label">Recommended cost, this shift</p>
          <p className="cost-stat-value">{fmt(costSummary.recommended_cost)}</p>
        </div>
      </div>
      {hasPremium && (
        <p className="cost-breakdown">
          Of which {fmt(costSummary.overtime_cost)} is overtime premium and{" "}
          {fmt(costSummary.float_cost)} is float/agency premium.
        </p>
      )}
      <div className="cost-delta" style={{ background: copy.bg, color: copy.fg }}>
        <div className="cost-delta-icon" style={{ background: copy.fg, color: "#fff" }}>
          {copy.icon}
        </div>
        <div>
          <strong>{copy.head(costSummary.delta)}</strong> — {copy.body(costSummary.delta)}
        </div>
      </div>
    </div>
  );
}
