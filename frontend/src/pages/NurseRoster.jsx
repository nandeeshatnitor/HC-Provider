import { useEffect, useState } from "react";
import { api } from "../api";

function StatusBadge({ nurse }) {
  if (!nurse.present) {
    return <span className="nurse-badge nurse-badge-absent">Absent</span>;
  }
  if (nurse.assigned) {
    return <span className="nurse-badge nurse-badge-assigned">Assigned · {nurse.patient_label}</span>;
  }
  return <span className="nurse-badge nurse-badge-free">Free</span>;
}

export default function NurseRoster() {
  const [nurses, setNurses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [busyId, setBusyId] = useState(null);
  const [labelDraft, setLabelDraft] = useState({});

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const res = await api.getNurses();
      setNurses(res.nurses);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function togglePresence(nurse) {
    setBusyId(nurse.id);
    setError(null);
    try {
      const res = await api.setNursePresence(nurse.id, !nurse.present);
      setNurses(res.nurses);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusyId(null);
    }
  }

  async function assign(nurse) {
    const label = labelDraft[nurse.id]?.trim() || "Bed —";
    setBusyId(nurse.id);
    setError(null);
    try {
      const res = await api.setNurseAssignment(nurse.id, true, label);
      setNurses(res.nurses);
      setLabelDraft((prev) => ({ ...prev, [nurse.id]: "" }));
    } catch (e) {
      setError(e.message);
    } finally {
      setBusyId(null);
    }
  }

  async function free(nurse) {
    setBusyId(nurse.id);
    setError(null);
    try {
      const res = await api.setNurseAssignment(nurse.id, false, null);
      setNurses(res.nurses);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusyId(null);
    }
  }

  const presentCount = nurses.filter((n) => n.present).length;
  const assignedCount = nurses.filter((n) => n.present && n.assigned).length;
  const freeCount = presentCount - assignedCount;

  return (
    <div className="card">
      <div className="section-title">
        <svg className="icon" viewBox="0 0 24 24" fill="none" stroke="var(--text-secondary)">
          <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" strokeWidth="2" strokeLinecap="round" />
          <circle cx="9" cy="7" r="4" strokeWidth="2" />
          <path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" strokeWidth="2" strokeLinecap="round" />
        </svg>
        Nurse roster
        <span className="badge badge-model" style={{ marginLeft: "auto" }}>
          Admin
        </span>
      </div>
      <p className="section-sub">
        Mark who's present today and who's currently assigned to a bed/patient. This is the same
        roster the staffing plan reads from — changes here update the dashboard live.
      </p>

      {loading && <p className="state-note">Loading roster…</p>}
      {error && <p className="error-note">Something went wrong: {error}</p>}

      {!loading && (
        <>
          <div className="cost-grid" style={{ gridTemplateColumns: "repeat(3, 1fr)" }}>
            <div className="cost-stat">
              <p className="cost-stat-label">Present today</p>
              <p className="cost-stat-value">{presentCount}</p>
            </div>
            <div className="cost-stat">
              <p className="cost-stat-label">Assigned to a bed/patient</p>
              <p className="cost-stat-value">{assignedCount}</p>
            </div>
            <div className="cost-stat">
              <p className="cost-stat-label">Free right now</p>
              <p className="cost-stat-value">{freeCount}</p>
            </div>
          </div>

          <div className="nurse-table-wrap">
            <table className="nurse-table">
              <thead>
                <tr>
                  <th>Nurse</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {nurses.map((nurse) => (
                  <tr key={nurse.id}>
                    <td>{nurse.name}</td>
                    <td>
                      <StatusBadge nurse={nurse} />
                    </td>
                    <td>
                      <div className="nurse-actions">
                        <button
                          className="btn btn-sm"
                          disabled={busyId === nurse.id}
                          onClick={() => togglePresence(nurse)}
                        >
                          {nurse.present ? "Mark absent" : "Mark present"}
                        </button>

                        {nurse.present && !nurse.assigned && (
                          <>
                            <input
                              className="nurse-label-input"
                              type="text"
                              placeholder="Bed / patient label"
                              value={labelDraft[nurse.id] || ""}
                              onChange={(e) =>
                                setLabelDraft((prev) => ({ ...prev, [nurse.id]: e.target.value }))
                              }
                            />
                            <button
                              className="btn btn-sm btn-primary"
                              disabled={busyId === nurse.id}
                              onClick={() => assign(nurse)}
                            >
                              Assign
                            </button>
                          </>
                        )}

                        {nurse.present && nurse.assigned && (
                          <button className="btn btn-sm" disabled={busyId === nurse.id} onClick={() => free(nurse)}>
                            Free up
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
