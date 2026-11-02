import { MapContainer, TileLayer, Polyline, CircleMarker, useMap } from "react-leaflet";
import { useEffect } from "react";
import "leaflet/dist/leaflet.css";
import "./MapView.css";

const TILE_URL = "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png";
const TILE_ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>';

function FitBounds({ bounds }) {
  const map = useMap();
  useEffect(() => {
    if (bounds && bounds.length) {
      // The map container's size can still be settling (flex layout, phone
      // frame transitions) right after mount, so nudge Leaflet to recompute
      // it before fitting bounds — otherwise routes can render off-canvas.
      const id = requestAnimationFrame(() => {
        map.invalidateSize();
        map.fitBounds(bounds, { padding: [28, 28], animate: false }); // no animation: avoids a Leaflet error if the map unmounts mid-pan
      });
      return () => cancelAnimationFrame(id);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [JSON.stringify(bounds)]);
  return null;
}

/**
 * routes: [{ id, path: [[lat,lng],...], color, weight, dashed }]
 * marker: [lat, lng] | null  — a live-position dot (e.g. the trip simulation)
 * markerColor: css color for the live marker
 */
export default function MapView({ routes = [], marker = null, markerColor = "var(--teal)", center, zoom = 13 }) {
  const allPoints = routes.flatMap((r) => r.path);
  const bounds = allPoints.length ? allPoints : null;

  return (
    <div className="map-view">
      <MapContainer
        center={center || allPoints[0] || [20.35, 85.82]}
        zoom={zoom}
        scrollWheelZoom={false}
        zoomControl={false}
        attributionControl={false}
        style={{ width: "100%", height: "100%" }}
      >
        <TileLayer url={TILE_URL} attribution={TILE_ATTRIBUTION} />
        {bounds && <FitBounds bounds={bounds} />}
        {routes.map((route) => (
          <Polyline
            key={route.id}
            positions={route.path}
            pathOptions={{
              color: route.color || "#49CDA8",
              weight: route.weight || 5,
              opacity: route.opacity ?? 0.9,
              dashArray: route.dashed ? "2 10" : undefined,
              lineCap: "round",
            }}
          />
        ))}
        {routes.map((route) => (
          <CircleMarker
            key={`${route.id}-start`}
            center={route.path[0]}
            radius={5}
            pathOptions={{ color: "#F3F0E8", fillColor: "#F3F0E8", fillOpacity: 1, weight: 2 }}
          />
        ))}
        {routes[0] && (
          <CircleMarker
            center={routes[0].path[routes[0].path.length - 1]}
            radius={6}
            pathOptions={{ color: "#E8A94C", fillColor: "#E8A94C", fillOpacity: 1, weight: 2 }}
          />
        )}
        {marker && (
          <CircleMarker
            center={marker}
            radius={7}
            pathOptions={{ color: markerColor, fillColor: markerColor, fillOpacity: 1, weight: 3 }}
          />
        )}
      </MapContainer>
      <div className="map-attribution">OpenStreetMap &amp; CARTO</div>
    </div>
  );
}
