import { useEffect, useState } from "react";
import { api } from "./api";
import Header from "./components/Header";
import ForecastPanel from "./components/ForecastPanel";
import StaffingPanel from "./components/StaffingPanel";
import CostPanel from "./components/CostPanel";
import AlertPanel from "./components/AlertPanel";
import NurseRoster from "./pages/NurseRoster";

function useHashRoute(defaultRoute) {
  const [route, setRoute] = useState(() => window.location.hash.slice(1) || defaultRoute);

  useEffect(() => {
    const onHashChange = () => setRoute(window.location.hash.slice(1) || defaultRoute);
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, [defaultRoute]);

  return route;
}

function Nav({ route }) {
  return (
    <div className="nav-tabs">
      <a href="#dashboard" className={`nav-tab ${route === "dashboard" ? "nav-tab-active" : ""}`}>
        Dashboard
      </a>
      <a href="#roster" className={`nav-tab ${route === "roster" ? "nav-tab-active" : ""}`}>
        Nurse roster
      </a>
    </div>
  );
}

export default function App() {
  const route = useHashRoute("dashboard");

  const [roleConfig, setRoleConfig] = useState([]);
  const [forecast, setForecast] = useState(null);
  const [todayForecast, setTodayForecast] = useState(null);
  const [todayCostSummary, setTodayCostSummary] = useState(null);
  const [plan, setPlan] = useState([]);
  const [costSummary, setCostSummary] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [simulating, setSimulating] = useState(false);
  const [resolvingId, setResolvingId] = useState(null);
  const [resetting, setResetting] = useState(false);

  async function refreshPlanAndCost(volume) {
    const [planRes, costRes, alertsRes] = await Promise.all([
      api.getStaffingPlan(volume),
      api.getCostSummary(volume),
      api.getAlerts(),
    ]);
    setPlan(planRes.plan);
    setCostSummary(costRes);
    setAlerts(alertsRes.alerts);
  }

  async function loadInitial() {
    setLoading(true);
    setError(null);
    try {
      const [configRes, forecastRes, todayRes, todayCostRes] = await Promise.all([
        api.getStaffingConfig(),
        api.getForecast(),
        api.getTodayForecast(),
        api.getTodayCostSummary(),
      ]);
      setRoleConfig(configRes.roles);
      setForecast(forecastRes);
      setTodayForecast(todayRes);
      setTodayCostSummary(todayCostRes);
      // Staffing is driven automatically by the model's own forecast for the
      // upcoming shift window — no manual override.
      await refreshPlanAndCost(forecastRes.predicted_volume);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadInitial();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // The nurse roster page can change who's present/assigned, which changes
  // the staffing plan server-side. Refetch when coming back to the
  // dashboard so it doesn't show stale pre-navigation numbers.
  useEffect(() => {
    if (route === "dashboard" && forecast && !loading) {
      refreshPlanAndCost(forecast.predicted_volume).catch((e) => setError(e.message));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [route]);

  async function handleActualCountSubmit(count) {
    const res = await api.postActualCount(count);
    setTodayForecast(res);
  }

  async function handleActualCountClear() {
    const res = await api.clearActualCount();
    setTodayForecast(res);
  }

  async function handleSimulateCallOut() {
    setSimulating(true);
    setError(null);
    try {
      const res = await api.simulateCallOut("nurse");
      setPlan(res.plan);
      setCostSummary(res.cost_summary);
      if (res.alert) {
        setAlerts((prev) => {
          const others = prev.filter((a) => a.id !== res.alert.id);
          return [...others, res.alert];
        });
      }
    } catch (e) {
      setError(e.message);
    } finally {
      setSimulating(false);
    }
  }

  async function handleResolve(alertId) {
    setResolvingId(alertId);
    setError(null);
    try {
      const res = await api.resolveAlert(alertId);
      setPlan(res.plan);
      setCostSummary(res.cost_summary);
      setAlerts((prev) => {
        const others = prev.filter((a) => a.id !== res.alert.id);
        return res.alert.status === "active" ? [...others, res.alert] : others;
      });
    } catch (e) {
      setError(e.message);
    } finally {
      setResolvingId(null);
    }
  }

  async function handleReset() {
    setResetting(true);
    setError(null);
    try {
      await api.reset();
      await loadInitial();
    } catch (e) {
      setError(e.message);
    } finally {
      setResetting(false);
    }
  }

  return (
    <div className="wrap">
      <Header shiftLabel={forecast?.shift_label} onReset={handleReset} resetting={resetting} />
      <Nav route={route} />

      {route === "roster" ? (
        <NurseRoster />
      ) : (
        <>
          {loading && <p className="state-note">Loading forecast and staffing plan…</p>}
          {error && <p className="error-note">Something went wrong: {error}</p>}

          {!loading && !error && (
            <>
              <ForecastPanel
                forecast={forecast}
                todayForecast={todayForecast}
                todayCostSummary={todayCostSummary}
                onActualCountSubmit={handleActualCountSubmit}
                onActualCountClear={handleActualCountClear}
              />
              <StaffingPanel roleConfig={roleConfig} plan={plan} />
              <CostPanel costSummary={costSummary} />
              <AlertPanel
                alerts={alerts}
                onResolve={handleResolve}
                onSimulateCallOut={handleSimulateCallOut}
                resolvingId={resolvingId}
                simulating={simulating}
              />
            </>
          )}
        </>
      )}
    </div>
  );
}
