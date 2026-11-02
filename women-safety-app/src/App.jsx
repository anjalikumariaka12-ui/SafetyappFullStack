import { useEffect, useState } from "react";
import { api, apiEnabled } from "./lib/api";
import PhoneFrame from "./components/PhoneFrame";
import BottomNav from "./components/BottomNav";
import PlanScreen from "./screens/PlanScreen";
import RouteResultsScreen from "./screens/RouteResultsScreen";
import LiveTripScreen from "./screens/LiveTripScreen";
import AlertsScreen from "./screens/AlertsScreen";
import ProfileScreen from "./screens/ProfileScreen";

// view: "plan" | "results" | "trip" — trip/results are pushed on top of a tab,
// tab: which bottom-nav tab is active underneath
export default function App() {
  const [tab, setTab] = useState("plan");
  const [view, setView] = useState("plan");
  const [trip, setTrip] = useState(null);
  const [activeRoute, setActiveRoute] = useState(null);

  // Free hosts sleep when idle; ping once on load so the server is awake by the time a route is searched.
  useEffect(() => {
    if (apiEnabled) api.health().catch(() => {});
  }, []);

  function handleTabChange(nextTab) {
    setTab(nextTab);
    setView(nextTab);
  }

  function handleFindRoute(tripInfo) {
    setTrip(tripInfo);
    setView("results");
  }

  function handleStartTrip(route) {
    setActiveRoute(route);
    setView("trip");
  }

  function handleEndTrip() {
    setActiveRoute(null);
    setView("plan");
    setTab("plan");
  }

  let screen;
  if (view === "results") {
    screen = (
      <RouteResultsScreen
        trip={trip}
        onBack={() => setView("plan")}
        onStartTrip={handleStartTrip}
      />
    );
  } else if (view === "trip" && activeRoute) {
    screen = <LiveTripScreen route={activeRoute} onEndTrip={handleEndTrip} />;
  } else if (tab === "alerts") {
    screen = <AlertsScreen />;
  } else if (tab === "profile") {
    screen = <ProfileScreen />;
  } else if (tab === "trip") {
    screen = activeRoute ? (
      <LiveTripScreen route={activeRoute} onEndTrip={handleEndTrip} />
    ) : (
      <NoActiveTrip onPlan={() => handleTabChange("plan")} />
    );
  } else {
    screen = <PlanScreen onFindRoute={handleFindRoute} />;
  }

  const showNav = view !== "results";

  return (
    <PhoneFrame>
      <div style={{ flex: 1, minHeight: 0 }}>{screen}</div>
      {showNav && <BottomNav active={tab} onChange={handleTabChange} />}
    </PhoneFrame>
  );
}

function NoActiveTrip({ onPlan }) {
  return (
    <div className="screen">
      <div className="empty-state" style={{ marginTop: 80 }}>
        <p style={{ fontSize: 14, marginBottom: 14 }}>No trip in progress.</p>
        <button className="btn btn-primary" onClick={onPlan}>
          Plan a trip
        </button>
      </div>
    </div>
  );
}
