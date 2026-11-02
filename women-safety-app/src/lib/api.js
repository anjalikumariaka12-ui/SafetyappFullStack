// Thin client for the Raahi backend. If VITE_API_URL isn't set, apiEnabled is false and the app
// keeps working in its original mock-data mode.
const BASE = (import.meta.env.VITE_API_URL || "").replace(/\/$/, "");
export const apiEnabled = Boolean(BASE);

async function req(path, { method = "GET", body, token, timeout = 15000 } = {}) {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeout);
  try {
    const res = await fetch(`${BASE}${path}`, {
      method,
      signal: ctrl.signal,
      headers: { "Content-Type": "application/json", ...(token ? { "X-Trip-Token": token } : {}) },
      body: body ? JSON.stringify(body) : undefined,
    });
    if (!res.ok) throw new Error(`API ${res.status}`);
    return await res.json();
  } finally {
    clearTimeout(timer);
  }
}

const pt = (p) => ({ lat: p[0], lng: p[1] });

export const api = {
  health: () => req("/api/health", { timeout: 70000 }), // also wakes a sleeping free-tier server
  analyze: ({ origin, destination_text, mode }) =>
    req("/api/routes/analyze", {
      method: "POST",
      timeout: 70000, // free hosts can take ~1 min to wake up
      body: {
        origin: { lat: origin.lat, lng: origin.lng },
        destination_text: /bhubaneswar/i.test(destination_text) ? destination_text : `${destination_text}, Bhubaneswar`,
        mode,
      },
    }),
  startTrip: (body) => req("/api/trips", { method: "POST", body }),
  location: (trip, p, accuracy) =>
    req(`/api/trips/${trip.id}/location`, { method: "POST", token: trip.token, body: { ...pt(p), accuracy } }),
  getTrip: (trip) => req(`/api/trips/${trip.id}`, { token: trip.token }),
  checkin: (trip) => req(`/api/trips/${trip.id}/checkin`, { method: "POST", token: trip.token }),
  sos: (trip) => req(`/api/trips/${trip.id}/sos`, { method: "POST", token: trip.token }),
  endTrip: (trip) => req(`/api/trips/${trip.id}/end`, { method: "POST", token: trip.token }),
  rate: (p, rating) => req("/api/ratings", { method: "POST", body: { ...pt(p), rating } }),
  telegramLink: () => req("/api/telegram/link", { method: "POST" }),
  telegramStatus: (code) => req(`/api/telegram/link/${code}`),
};
