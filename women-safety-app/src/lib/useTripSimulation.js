import { useEffect, useMemo, useRef, useState } from "react";

// Breaks a route's waypoints into even-length segments so progress
// (0..1) maps to a smoothly interpolated [lat, lng] position.
function useSegments(path) {
  return useMemo(() => {
    const segments = [];
    let total = 0;
    for (let i = 0; i < path.length - 1; i++) {
      const [lat1, lng1] = path[i];
      const [lat2, lng2] = path[i + 1];
      const length = Math.hypot(lat2 - lat1, lng2 - lng1);
      segments.push({ from: path[i], to: path[i + 1], length });
      total += length;
    }
    return { segments, total };
  }, [path]);
}

function positionAt(progress, segments, total) {
  const target = progress * total;
  let covered = 0;
  for (const seg of segments) {
    if (covered + seg.length >= target || seg === segments[segments.length - 1]) {
      const segProgress = seg.length === 0 ? 0 : (target - covered) / seg.length;
      const clamped = Math.min(Math.max(segProgress, 0), 1);
      const lat = seg.from[0] + (seg.to[0] - seg.from[0]) * clamped;
      const lng = seg.from[1] + (seg.to[1] - seg.from[1]) * clamped;
      return [lat, lng];
    }
    covered += seg.length;
  }
  return segments[segments.length - 1].to;
}

// Drives a simulated GPS trip along `path`. Call `triggerDeviation()` to
// demo what the anomaly-detection module would see when a driver strays
// off the recommended path.
export function useTripSimulation(path, { speed = 0.006, autoStart = true } = {}) {
  const { segments, total } = useSegments(path);
  const [progress, setProgress] = useState(0);
  const [running, setRunning] = useState(autoStart);
  const [deviated, setDeviated] = useState(false);
  const deviationOffsetRef = useRef([0, 0]);

  useEffect(() => {
    if (!running) return undefined;
    const id = setInterval(() => {
      setProgress((p) => Math.min(p + speed, 1));
    }, 300);
    return () => clearInterval(id);
  }, [running, speed]);

  useEffect(() => {
    if (progress >= 1) setRunning(false);
  }, [progress]);

  const basePosition = positionAt(progress, segments, total);
  const position = deviated
    ? [basePosition[0] + deviationOffsetRef.current[0], basePosition[1] + deviationOffsetRef.current[1]]
    : basePosition;

  function triggerDeviation() {
    deviationOffsetRef.current = [0.0045, -0.0035];
    setDeviated(true);
  }

  function resolveDeviation() {
    setDeviated(false);
  }

  function reset() {
    setProgress(0);
    setDeviated(false);
    setRunning(true);
  }

  return {
    position,
    progress,
    running,
    deviated,
    setRunning,
    triggerDeviation,
    resolveDeviation,
    reset,
  };
}
