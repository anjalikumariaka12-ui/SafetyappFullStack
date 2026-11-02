import { useEffect, useState } from "react";

// Real GPS via the browser Geolocation API (free). Also asks the screen to stay awake, because mobile
// browsers pause location updates when the screen locks or the tab is backgrounded.
export function useLiveGps(enabled) {
  const [state, setState] = useState({ position: null, accuracy: null, error: null });

  useEffect(() => {
    if (!enabled) return undefined;
    if (!("geolocation" in navigator)) {
      setState((s) => ({ ...s, error: "This browser has no GPS support." }));
      return undefined;
    }
    const watchId = navigator.geolocation.watchPosition(
      (p) => setState({ position: [p.coords.latitude, p.coords.longitude], accuracy: p.coords.accuracy, error: null }),
      (e) => setState((s) => ({ ...s, error: e.code === 1 ? "Location permission denied." : "Can't get a GPS fix." })),
      { enableHighAccuracy: true, maximumAge: 2000, timeout: 20000 }
    );

    let lock = null;
    const acquire = async () => {
      try {
        if ("wakeLock" in navigator && document.visibilityState === "visible") lock = await navigator.wakeLock.request("screen");
      } catch {
        /* not supported / denied: non-fatal */
      }
    };
    acquire();
    document.addEventListener("visibilitychange", acquire);

    return () => {
      navigator.geolocation.clearWatch(watchId);
      document.removeEventListener("visibilitychange", acquire);
      lock?.release?.().catch(() => {});
    };
  }, [enabled]);

  return state;
}

export function getCurrentPosition() {
  return new Promise((resolve, reject) => {
    if (!("geolocation" in navigator)) return reject(new Error("no geolocation"));
    navigator.geolocation.getCurrentPosition(
      (p) => resolve({ lat: p.coords.latitude, lng: p.coords.longitude }),
      reject,
      { enableHighAccuracy: true, timeout: 15000 }
    );
  });
}
