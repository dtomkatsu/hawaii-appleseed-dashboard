import L from 'leaflet';

let mapInstance = null;

export function createMap(containerId, theme) {
  if (mapInstance) return mapInstance;

  const mapCfg = (theme && theme.map) || {};
  const center = mapCfg.center || [20.7984, -156.3319];
  const zoom = mapCfg.zoom || 7;

  mapInstance = L.map(containerId, {
    center,
    zoom,
    zoomSnap: mapCfg.zoom_snap ?? 0,
    zoomDelta: mapCfg.zoom_delta ?? 0.5,
    fadeAnimation: mapCfg.fade_animation ?? true,
    markerZoomAnimation: mapCfg.marker_zoom_animation ?? true,
    zoomControl: true,
  });

  L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png', {
    attribution:
      '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
    maxZoom: 18,
    subdomains: 'abcd',
  }).addTo(mapInstance);

  return mapInstance;
}

export function getMap() {
  return mapInstance;
}
