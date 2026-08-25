export default function Header({ shiftLabel, onReset, resetting }) {
  return (
    <div className="header">
      <div className="header-left">
        <div className="logo">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
            <path d="M12 3v18M3 12h18" stroke="#fff" strokeWidth="2.5" strokeLinecap="round" />
            <rect x="4" y="4" width="16" height="16" rx="4" stroke="#fff" strokeWidth="1.6" />
          </svg>
        </div>
        <div>
          <p className="header-title">Hospital Staffing Assistant</p>
          <p className="header-sub">
            Emergency department · {shiftLabel || "loading shift…"}
          </p>
        </div>
      </div>
      <button className="btn" onClick={onReset} disabled={resetting}>
        <svg className="icon" viewBox="0 0 24 24" fill="none">
          <path
            d="M21 12a9 9 0 1 1-3-6.7M21 4v5h-5"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
        Start over
      </button>
    </div>
  );
}
