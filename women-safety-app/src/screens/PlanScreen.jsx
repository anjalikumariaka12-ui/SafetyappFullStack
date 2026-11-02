import { useState } from "react";
import "./shared.css";
import { ORIGIN, SAVED_PLACES } from "../lib/mockData";
import { getCurrentPosition } from "../lib/useLiveGps";

export default function PlanScreen({ onFindRoute }) {
  const [mode, setMode] = useState("cab");
  const [destination, setDestination] = useState("");
  const [origin, setOrigin] = useState(ORIGIN);
  const [gpsMsg, setGpsMsg] = useState("");

  async function useMyLocation() {
    setGpsMsg("Getting your location…");
    try {
      const p = await getCurrentPosition();
      setOrigin({ label: "My current location", lat: p.lat, lng: p.lng });
      setGpsMsg("");
    } catch {
      setGpsMsg("Couldn't get your location — check permission.");
    }
  }

  return (
    <div className="screen">
      <div className="screen-header">
        <div className="brand-row">
          <div className="brand-mark">R</div>
          <div className="brand-name">Raahi</div>
        </div>
        <h1 className="screen-title">Where are you headed?</h1>
        <p className="screen-subtitle">
          Tell us your destination and we'll compare routes before you set out — not after something goes wrong.
        </p>
      </div>

      <div className="screen-body">
        <div className="card" style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <div>
            <span className="field-label">From</span>
            <div className="input" style={{ display: "flex", alignItems: "center", gap: 8, color: "var(--text-secondary)" }}>
              <DotIcon color="var(--teal)" />
              {origin.label}
            </div>
            <button className="back-btn" style={{ marginTop: 6 }} onClick={useMyLocation}>
              {origin === ORIGIN ? "📍 Use my current location" : "📍 Update my location"}
            </button>
            {gpsMsg && <p style={{ margin: "4px 0 0", fontSize: 12, color: "var(--text-muted)" }}>{gpsMsg}</p>}
          </div>
          <div>
            <span className="field-label">To</span>
            <input
              className="input"
              placeholder="Enter a destination"
              value={destination}
              onChange={(e) => setDestination(e.target.value)}
            />
          </div>
        </div>

        <div>
          <span className="field-label" style={{ marginLeft: 2 }}>Travelling by</span>
          <div className="chip-toggle">
            <button className={mode === "cab" ? "is-active" : ""} onClick={() => setMode("cab")}>
              Cab / Auto
            </button>
            <button className={mode === "walk" ? "is-active" : ""} onClick={() => setMode("walk")}>
              On foot
            </button>
          </div>
        </div>

        <button className="btn btn-primary" onClick={() => onFindRoute({ destination: destination || SAVED_PLACES[1].label, mode, origin })}>
          Find the safest route
        </button>

        <div className="card" style={{ padding: "6px 12px" }}>
          <p className="section-label">Saved places</p>
          {SAVED_PLACES.map((place) => (
            <button
              key={place.id}
              className="saved-place"
              onClick={() => {
                setDestination(place.label);
                onFindRoute({ destination: place.label, mode, origin });
              }}
            >
              <span className="saved-place-icon">
                <PlaceIcon kind={place.icon} />
              </span>
              {place.label}
            </button>
          ))}
        </div>

        <div className="card card-raised" style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
          <span style={{ fontSize: 18, lineHeight: 1 }}>🌙</span>
          <p style={{ margin: 0, fontSize: 12.5, color: "var(--text-secondary)", lineHeight: 1.55 }}>
            Route scores update by time of day — the same road can look different at 9 PM than at noon, based on
            lighting, foot traffic, and past reports.
          </p>
        </div>
      </div>
    </div>
  );
}

function DotIcon({ color }) {
  return (
    <svg width="10" height="10" viewBox="0 0 10 10">
      <circle cx="5" cy="5" r="4" fill={color} />
    </svg>
  );
}

function PlaceIcon({ kind }) {
  if (kind === "home") {
    return (
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
        <path d="M4 11.5 12 4l8 7.5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M6 10v9h12v-9" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" />
      </svg>
    );
  }
  if (kind === "train") {
    return (
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
        <rect x="6" y="4" width="12" height="13" rx="3" stroke="currentColor" strokeWidth="1.8" />
        <path d="M6 17 4 21m14-4 2 4M8 21h8" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
        <circle cx="9.5" cy="12" r="0.9" fill="currentColor" />
        <circle cx="14.5" cy="12" r="0.9" fill="currentColor" />
      </svg>
    );
  }
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
      <path d="M12 21s7-6.2 7-11.4A7 7 0 0 0 5 9.6C5 14.8 12 21 12 21Z" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" />
      <circle cx="12" cy="9.5" r="2.2" stroke="currentColor" strokeWidth="1.8" />
    </svg>
  );
}
