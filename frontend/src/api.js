const BASE = "/api";

async function request(path, options) {
  const res = await fetch(BASE + path, options);
  let data = null;
  try {
    data = await res.json();
  } catch {
    data = null;
  }
  if (!res.ok) {
    const message = data?.error?.message || `Request failed (${res.status})`;
    throw new Error(message);
  }
  return data;
}

export const api = {
  getForecast: () => request("/forecast"),
  getTodayForecast: () => request("/forecast/today"),
  getTodayCostSummary: () => request("/cost-summary/today"),
  postActualCount: (count) =>
    request("/today/actual-count", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ count }),
    }),
  clearActualCount: () => request("/today/actual-count/clear", { method: "POST" }),
  getStaffingConfig: () => request("/staffing-config"),
  getStaffingPlan: (predictedVolume) =>
    request(`/staffing-plan?predicted_volume=${predictedVolume}`),
  getCostSummary: (predictedVolume) =>
    request(`/cost-summary?predicted_volume=${predictedVolume}`),
  getAlerts: () => request("/alerts"),
  simulateCallOut: (roleId = "nurse") =>
    request("/scenario/call-out", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ role_id: roleId }),
    }),
  resolveAlert: (id) => request(`/alerts/${id}/resolve`, { method: "POST" }),
  reset: () => request("/scenario/reset", { method: "POST" }),
  getNurses: () => request("/nurses"),
  setNursePresence: (id, present) =>
    request(`/nurses/${id}/presence`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ present }),
    }),
  setNurseAssignment: (id, assigned, patientLabel) =>
    request(`/nurses/${id}/assignment`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ assigned, patient_label: patientLabel ?? null }),
    }),
};
