function fmt(n) {
  return "₹" + Math.round(n).toLocaleString("en-US");
}

export default function AlertPanel({ alerts, onResolve, onSimulateCallOut, resolvingId, simulating }) {
  return (
    <div className="card">
      <div className="alert-header">
        <div>
          <div className="section-title" style={{ marginBottom: 3 }}>
            <svg className="icon" viewBox="0 0 24 24" fill="none" stroke="var(--text-secondary)">
              <path
                d="M18 8a6 6 0 1 0-12 0c0 7-3 9-3 9h18s-3-2-3-9"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
              <path d="M13.7 21a2 2 0 0 1-3.4 0" strokeWidth="2" strokeLinecap="round" />
            </svg>
            Is anything going wrong right now?
          </div>
          <p className="section-sub" style={{ marginBottom: 0 }}>
            Try it — simulate a nurse calling in sick and watch the alert and cost update.
          </p>
        </div>
        <button className="btn btn-primary btn-sm" onClick={onSimulateCallOut} disabled={simulating}>
          <svg className="icon" viewBox="0 0 24 24" fill="none">
            <path d="M8 5v14l11-7z" fill="#fff" />
          </svg>
          Simulate a nurse calling out
        </button>
      </div>

      {alerts.length === 0 ? (
        <div className="alert-ok">
          <svg className="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path d="M5 13l4 4L19 7" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          Everything looks fully staffed right now.
        </div>
      ) : (
        alerts
          .slice()
          .sort((a, b) => b.gap - a.gap)
          .map((alert) => (
            <div className="alert-item" key={alert.id}>
              <div
                className="status-dot"
                style={{
                  background: alert.severity === "high" ? "var(--danger)" : "var(--warning)",
                  marginTop: 1,
                }}
              >
                {alert.severity === "high" ? "!!" : "!"}
              </div>
              <div style={{ flex: 1 }}>
                <p className="alert-title">
                  Not enough {alert.display_name.toLowerCase()} scheduled
                </p>
                <p className="alert-sub">
                  Short {alert.gap} vs. plan · {alert.severity === "high" ? "Urgent" : "Needs attention"} ·{" "}
                  {alert.recommended_action.toLowerCase()} · est. {fmt(alert.estimated_cost)}
                </p>
              </div>
              <button
                className="btn btn-sm"
                onClick={() => onResolve(alert.id)}
                disabled={resolvingId === alert.id}
              >
                {alert.recommended_action}
              </button>
            </div>
          ))
      )}
    </div>
  );
}
