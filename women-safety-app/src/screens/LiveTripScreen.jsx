import { useEffect, useRef, useState } from "react";
import "./shared.css";
import MapView from "../components/MapView";
import StatusPill from "../components/StatusPill";
import { useTripSimulation } from "../lib/useTripSimulation";
import { useLiveGps } from "../lib/useLiveGps";
import { api, apiEnabled } from "../lib/api";
import { getUserName, loadContacts, quickLinks } from "../lib/contacts";
import { ESCALATION_STEPS } from "../lib/mockData";

const PING_MS = 4000;

export default function LiveTripScreen({ route, onEndTrip }) {
  const [source, setSource] = useState("gps"); // "gps" = real phone GPS, "demo" = simulated driver
  const gps = useLiveGps(source === "gps");
  const sim = useTripSimulation(route.path, { speed: 0.006, autoStart: false });
  const position = source === "gps" ? gps.position : sim.position;
  const accuracy = source === "gps" ? gps.accuracy : 10;

  const [trip, setTrip] = useState(null); // { id, token }
  const [server, setServer] = useState(null); // latest state from the backend
  const [serverOk, setServerOk] = useState(apiEnabled);
  const [now, setNow] = useState(Date.now());
  const receivedAt = useRef(Date.now());
  const posRef = useRef({ position, accuracy });
  posRef.current = { position, accuracy };
  const [contacts] = useState(loadContacts);

  useEffect(() => { sim.setRunning(source === "demo"); }, [source]); // eslint-disable-line react-hooks/exhaustive-deps

  // Start the monitored trip on the server (and end it, deleting location data, when leaving the screen).
  useEffect(() => {
    if (!apiEnabled) return undefined;
    let cancelled = false;
    let handle = null;
    api
      .startTrip({
        mode: "cab", route_name: route.name, path: route.path, risk: route.risk || [], user_name: getUserName(),
        contacts: contacts.map((c) => ({ name: c.name, phone: c.phone, telegram_chat_id: c.telegramChatId || null })),
      })
      .then((r) => {
        const t = { id: r.trip_id, token: r.token };
        if (cancelled) return api.endTrip(t).catch(() => {});
        handle = t;
        setTrip(t);
        setServer(r.state);
        setServerOk(true);
        return undefined;
      })
      .catch(() => !cancelled && setServerOk(false));
    return () => {
      cancelled = true;
      if (handle) api.endTrip(handle).catch(() => {});
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Report position + pull state every few seconds.
  useEffect(() => {
    if (!trip) return undefined;
    const tick = async () => {
      try {
        const p = posRef.current;
        const st = p.position ? await api.location(trip, p.position, p.accuracy) : await api.getTrip(trip);
        receivedAt.current = Date.now();
        setServer(st);
        setServerOk(true);
      } catch {
        setServerOk(false);
      }
    };
    tick();
    const id = setInterval(tick, PING_MS);
    return () => clearInterval(id);
  }, [trip]);

  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);

  const level = server?.level || 0; // 0 normal, 1 check-in, 2 contacts alerted, 3 control room
  const secondsLeft = server?.seconds_left == null ? null : Math.max(0, server.seconds_left - Math.round((now - receivedAt.current) / 1000));
  const arrived = server?.status === "completed";

  async function act(fn) {
    try {
      const st = await fn(trip);
      receivedAt.current = Date.now();
      setServer(st);
      setServerOk(true);
    } catch {
      setServerOk(false);
    }
  }
  const resolveAll = () => { sim.resolveDeviation(); if (trip) act(api.checkin); };
  const manualSOS = () => { if (trip) act(api.sos); };
  const links = quickLinks(contacts, position, getUserName());

  const mapRoute = [{ id: route.id, path: route.path, color: "#49CDA8", weight: 5, opacity: 0.85 }];

  return (
    <div className="screen">
      <div className="screen-header" style={{ paddingBottom: 0 }}>
        <button className="back-btn" onClick={onEndTrip} aria-label="End trip">
          ‹ End trip
        </button>
        <div className="row" style={{ marginTop: 8, alignItems: "flex-start" }}>
          <div>
            <h1 className="screen-title" style={{ fontSize: 19 }}>{route.name}</h1>
            <p className="screen-subtitle">Live trip monitoring</p>
          </div>
          <StatusPill tone={level === 0 ? "safe" : level === 1 ? "warn" : "danger"}>
            {arrived ? "Arrived" : level === 0 ? "On expected path" : level === 1 ? "Checking in" : "Escalating"}
          </StatusPill>
        </div>
      </div>

      <div style={{ height: 230, flexShrink: 0, margin: "12px 20px 0", borderRadius: 18, overflow: "hidden", border: "1px solid var(--border)" }}>
        <MapView
          routes={mapRoute}
          marker={position}
          markerColor={level === 0 ? "var(--teal)" : "var(--coral)"}
          zoom={13}
        />
      </div>

      <div className="screen-body" style={{ paddingTop: 12 }}>
        {!apiEnabled && <Note>Safety server not configured (VITE_API_URL) — alerts are off. SOS buttons below still work.</Note>}
        {apiEnabled && !serverOk && <Note>Can't reach the safety server — alerts may not be sent. Use the call buttons below.</Note>}
        {source === "gps" && gps.error && <Note>{gps.error}</Note>}
        {source === "gps" && !gps.error && !gps.position && <Note>Waiting for a GPS fix…</Note>}
        {arrived && <Note tone="safe">You've reached your destination. Tap "End trip" to finish.</Note>}

        {level === 0 ? (
          <div className="card" style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <p style={{ margin: 0, fontSize: 13.5, color: "var(--text-secondary)", lineHeight: 1.55 }}>
              We're comparing this trip's live path against the route you chose. If it drifts or stalls in a
              low-safety zone, we'll check in with you before doing anything else.
            </p>
            <p style={{ margin: 0, fontSize: 12, color: "var(--text-muted)", lineHeight: 1.5 }}>
              Keep Raahi open with the screen on — phone browsers pause GPS when the screen locks.
            </p>
            {source === "demo" && (
              <button className="btn btn-ghost" onClick={sim.triggerDeviation}>
                Simulate a route deviation (demo)
              </button>
            )}
            <button className="btn btn-ghost" onClick={() => setSource(source === "gps" ? "demo" : "gps")}>
              {source === "gps" ? "Use demo GPS instead" : "Use my real GPS"}
            </button>
          </div>
        ) : (
          <div className="card card-raised">
            <p className="section-label" style={{ marginBottom: 10 }}>Alert escalation</p>
            <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
              {ESCALATION_STEPS.map((step, i) => {
                const stepNumber = i + 1;
                const state = stepNumber < level ? "done" : stepNumber === level ? "active" : "pending";
                return (
                  <div key={step.id} style={{ display: "flex", gap: 12 }}>
                    <div
                      style={{
                        width: 22,
                        height: 22,
                        borderRadius: "50%",
                        flexShrink: 0,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        fontSize: 11,
                        fontWeight: 600,
                        background:
                          state === "pending" ? "rgba(244,241,234,0.08)" : state === "active" ? "var(--coral)" : "var(--teal)",
                        color: state === "pending" ? "var(--text-muted)" : "#0B0F1D",
                      }}
                    >
                      {state === "done" ? "✓" : stepNumber}
                    </div>
                    <div>
                      <div style={{ fontSize: 13.5, fontWeight: 600, color: state === "pending" ? "var(--text-muted)" : "var(--text-primary)" }}>
                        {step.title}
                        {state === "active" && stepNumber === 1 && secondsLeft != null ? ` · ${secondsLeft}s` : ""}
                      </div>
                      <div style={{ fontSize: 12.5, color: "var(--text-muted)", marginTop: 2, lineHeight: 1.5 }}>
                        {step.detail}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
            <button className="btn btn-primary" style={{ marginTop: 16 }} onClick={resolveAll}>
              I'm safe — stop the alert
            </button>
            {level >= 2 && <QuickActions links={links} />}
          </div>
        )}

        <button className="btn btn-danger" onClick={manualSOS} disabled={!trip}>
          SOS — alert my contacts now
        </button>
        <a className="btn btn-secondary" href="tel:112" style={{ textDecoration: "none", textAlign: "center" }}>
          Call 112 (emergency)
        </a>
        {contacts.length === 0 && (
          <p style={{ margin: 0, fontSize: 12, color: "var(--text-muted)" }}>No emergency contacts yet — add some in the Alerts tab so we can notify them.</p>
        )}
        {level < 2 && <QuickActions links={links} compact />}
      </div>
    </div>
  );
}

function Note({ children, tone = "warn" }) {
  return (
    <p style={{ margin: 0, fontSize: 12.5, lineHeight: 1.5, color: tone === "safe" ? "var(--teal)" : "var(--amber)" }}>
      {children}
    </p>
  );
}

// One-tap call / WhatsApp / SMS to each contact: free, user-initiated, works even if the server is down.
function QuickActions({ links, compact }) {
  if (!links.length) return null;
  const a = { textDecoration: "none", textAlign: "center", flex: 1, width: "auto", padding: "9px 6px", fontSize: 12.5 };
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8, marginTop: compact ? 0 : 14 }}>
      {links.map((l) => (
        <div key={l.tel} style={{ display: "flex", gap: 6, alignItems: "center" }}>
          <span style={{ fontSize: 12.5, minWidth: 70, color: "var(--text-secondary)" }}>{l.name}</span>
          <a className="btn btn-secondary" style={a} href={l.tel}>Call</a>
          <a className="btn btn-secondary" style={a} href={l.whatsapp} target="_blank" rel="noreferrer">WhatsApp</a>
          <a className="btn btn-secondary" style={a} href={l.sms}>SMS</a>
        </div>
      ))}
    </div>
  );
}
