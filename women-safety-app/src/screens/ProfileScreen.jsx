import { useState } from "react";
import "./shared.css";
import { api, apiEnabled } from "../lib/api";
import { getCurrentPosition } from "../lib/useLiveGps";

const TOGGLES = [
  { id: "share", label: "Share live location with contacts during trips", defaultOn: true },
  { id: "crowd", label: "Contribute anonymous safety ratings", defaultOn: true },
  { id: "night", label: "Stricter scoring after 9 PM", defaultOn: true },
];

export default function ProfileScreen() {
  const [toggles, setToggles] = useState(() => Object.fromEntries(TOGGLES.map((t) => [t.id, t.defaultOn])));
  const [rating, setRating] = useState(70);
  const [submitted, setSubmitted] = useState(false);
  const [ratingMsg, setRatingMsg] = useState("");

  // Sends a 1-5 rating for wherever you are right now; the backend blends nearby ratings into route scores.
  async function submitRating() {
    if (!apiEnabled) return setSubmitted(true); // original demo behaviour
    try {
      const p = await getCurrentPosition();
      await api.rate([p.lat, p.lng], Math.round((1 + (rating / 100) * 4) * 10) / 10);
      setSubmitted(true);
      setRatingMsg("");
    } catch {
      setRatingMsg("Couldn't submit — check location permission and connection.");
    }
  }

  return (
    <div className="screen">
      <div className="screen-header">
        <div className="row" style={{ alignItems: "center" }}>
          <div>
            <h1 className="screen-title" style={{ fontSize: 22 }}>Priya Sharma</h1>
            <p className="screen-subtitle">priya.sharma@kiit.ac.in</p>
          </div>
          <div
            style={{
              width: 46,
              height: 46,
              borderRadius: "50%",
              background: "var(--surface-raised)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontFamily: "var(--font-display)",
              fontWeight: 600,
              color: "var(--amber)",
            }}
          >
            PS
          </div>
        </div>
      </div>

      <div className="screen-body">
        <div className="card" style={{ padding: "6px 14px" }}>
          {TOGGLES.map((t) => (
            <div key={t.id} className="row" style={{ padding: "13px 0", borderBottom: "1px solid var(--border)" }}>
              <span style={{ fontSize: 13.5, color: "var(--text-primary)", maxWidth: 230 }}>{t.label}</span>
              <Switch checked={toggles[t.id]} onChange={() => setToggles((s) => ({ ...s, [t.id]: !s[t.id] }))} />
            </div>
          ))}
        </div>

        <div className="card">
          <p className="section-label" style={{ marginBottom: 8 }}>Rate a road you've travelled</p>
          <p style={{ margin: "0 0 12px", fontSize: 12.5, color: "var(--text-secondary)", lineHeight: 1.5 }}>
            Your rating feeds the crowd-sourced safety layer and helps the model score this stretch for the next
            traveller.
          </p>
          <input
            type="range"
            min="0"
            max="100"
            value={rating}
            onChange={(e) => {
              setRating(Number(e.target.value));
              setSubmitted(false);
            }}
            style={{ width: "100%", accentColor: "var(--amber)" }}
          />
          <div className="row" style={{ marginTop: 4 }}>
            <span style={{ fontSize: 12, color: "var(--text-muted)" }}>Felt unsafe</span>
            <span style={{ fontSize: 12, color: "var(--text-muted)" }}>Felt safe</span>
          </div>
          <button
            className="btn btn-secondary"
            style={{ marginTop: 12 }}
            onClick={submitRating}
          >
            {submitted ? "Thanks — rating submitted" : apiEnabled ? "Submit rating for where I am now" : "Submit rating for Patia Main Road"}
          </button>
          {ratingMsg && <p style={{ margin: "8px 0 0", fontSize: 12, color: "var(--amber)" }}>{ratingMsg}</p>}
        </div>

        <div className="card card-raised">
          <p className="section-label" style={{ marginBottom: 6 }}>How the safety score works</p>
          <p style={{ margin: 0, fontSize: 12.5, color: "var(--text-secondary)", lineHeight: 1.6 }}>
            Each route is scored from public crime-density data, street lighting and population-density layers,
            proximity to police stations, and ratings from travellers like you. Nothing here replaces your own
            judgement — it's one more input before you head out.
          </p>
        </div>

        <button className="btn btn-ghost">Sign out</button>
      </div>
    </div>
  );
}

function Switch({ checked, onChange }) {
  return (
    <button
      onClick={onChange}
      aria-pressed={checked}
      style={{
        width: 42,
        height: 24,
        borderRadius: 999,
        border: "none",
        background: checked ? "var(--amber)" : "rgba(244,241,234,0.14)",
        position: "relative",
        flexShrink: 0,
        transition: "background 0.15s ease",
      }}
    >
      <span
        style={{
          position: "absolute",
          top: 3,
          left: checked ? 21 : 3,
          width: 18,
          height: 18,
          borderRadius: "50%",
          background: "#0B0F1D",
          transition: "left 0.15s ease",
        }}
      />
    </button>
  );
}
