import { useEffect, useState } from "react";
import "./shared.css";
import MapView from "../components/MapView";
import SafetyScoreRing from "../components/SafetyScoreRing";
import StatusPill from "../components/StatusPill";
import { ORIGIN, ROUTES } from "../lib/mockData";
import { api, apiEnabled } from "../lib/api";

function toneFor(score) {
  if (score >= 75) return "safe";
  if (score >= 55) return "warn";
  return "danger";
}

function colorFor(score) {
  if (score >= 75) return "#49CDA8";
  if (score >= 55) return "#E8A94C";
  return "#E8604C";
}

export default function RouteResultsScreen({ trip, onBack, onStartTrip }) {
  const [routes, setRoutes] = useState(null); // null while loading
  const [meta, setMeta] = useState({ source: "mock" });
  const [activeId, setActiveId] = useState(null);

  useEffect(() => {
    let off = false;
    (async () => {
      if (!apiEnabled) return setRoutes(ROUTES);
      try {
        const r = await api.analyze({ origin: trip?.origin || ORIGIN, destination_text: trip?.destination || "Bhubaneswar Railway Station", mode: trip?.mode });
        if (!off) { setRoutes(r.routes); setMeta(r); setActiveId(r.routes[0].id); }
      } catch {
        if (!off) { setRoutes(ROUTES); setMeta({ source: "mock", offline: true }); }
      }
    })();
    return () => { off = true; };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const list = routes || [];
  const active = list.find((r) => r.id === activeId) || list[0];
  const currentId = active?.id;
  const notice =
    meta.offline ? "Couldn't reach the safety server — showing sample routes."
    : meta.source === "demo" ? "No live route found for that place — showing sample routes."
    : meta.engine === "heuristic" ? "Estimated scores — trained model not connected yet."
    : list[0]?.confidence === "low" ? "Limited road data here — scores are rough." : "";

  const mapRoutes = list.map((r) => ({
    id: r.id,
    path: r.path,
    color: colorFor(r.score),
    weight: r.id === currentId ? 6 : 3,
    opacity: r.id === currentId ? 0.95 : 0.35,
  }));
  // Draw the active route last so it renders on top of the others.
  mapRoutes.sort((a, b) => (a.id === currentId ? 1 : 0) - (b.id === currentId ? 1 : 0));

  return (
    <div className="screen">
      <div className="screen-header" style={{ paddingBottom: 0 }}>
        <button className="back-btn" onClick={onBack} aria-label="Back">
          ‹ Back
        </button>
        <h1 className="screen-title" style={{ fontSize: 20, marginTop: 10 }}>
          To {trip?.destination || "your destination"}
        </h1>
        <p className="screen-subtitle">{routes ? list.length : "…"} routes compared · {trip?.mode === "walk" ? "on foot" : "by cab"}</p>
      </div>

      <div style={{ height: 190, flexShrink: 0, margin: "12px 20px 0", borderRadius: 18, overflow: "hidden", border: "1px solid var(--border)" }}>
        {routes ? <MapView routes={mapRoutes} zoom={13} /> : <p style={{ padding: 20, color: "var(--text-muted)", fontSize: 13 }}>Scoring routes… (the first search can take up to a minute while the server wakes up)</p>}
      </div>

      <div className="screen-body" style={{ paddingTop: 12 }}>
        {notice && <p style={{ margin: 0, fontSize: 12, color: "var(--amber)" }}>{notice}</p>}
        {list.map((route) => {
          const isActive = route.id === currentId;
          return (
            <button
              key={route.id}
              className={`card route-card ${isActive ? "route-card-active" : ""}`}
              onClick={() => setActiveId(route.id)}
            >
              <div className="row" style={{ alignItems: "flex-start" }}>
                <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
                  <SafetyScoreRing score={route.score} size={48} />
                  <div style={{ textAlign: "left" }}>
                    <div style={{ fontWeight: 600, fontSize: 14.5 }}>{route.name}</div>
                    <div style={{ fontSize: 12.5, color: "var(--text-muted)", marginTop: 2 }}>
                      {route.minutes} min · {route.distanceKm} km
                    </div>
                  </div>
                </div>
                <StatusPill tone={toneFor(route.score)}>{route.tag}</StatusPill>
              </div>

              {isActive && (
                <div style={{ marginTop: 14, display: "flex", flexDirection: "column", gap: 10 }}>
                  {route.factors.map((f) => (
                    <div key={f.label}>
                      <div className="row" style={{ marginBottom: 4 }}>
                        <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>{f.label}</span>
                        <span style={{ fontSize: 12, color: "var(--text-muted)" }}>{Math.round(f.value * 100)}%</span>
                      </div>
                      <div className="factor-bar-track">
                        <div
                          className="factor-bar-fill"
                          style={{ width: `${f.value * 100}%`, background: colorFor(route.score) }}
                        />
                      </div>
                    </div>
                  ))}
                  <p style={{ fontSize: 12.5, color: "var(--text-secondary)", margin: "2px 0 0", lineHeight: 1.5 }}>
                    {route.note}
                  </p>
                </div>
              )}
            </button>
          );
        })}
      </div>

      <div style={{ padding: "0 20px 22px" }}>
        <button className="btn btn-primary" disabled={!active} onClick={() => onStartTrip(active)}>
          Start trip{active ? ` on ${active.name}` : ""}
        </button>
      </div>
    </div>
  );
}
