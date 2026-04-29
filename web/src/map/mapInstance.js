import L from 'leaflet';
import './smoothWheelZoom.js';

let mapInstance = null;

export function createMap(containerId, theme) {
  if (mapInstance) return mapInstance;

  const mapCfg = (theme && theme.map) || {};
  const center = mapCfg.center || [20.7984, -156.3319];
  const zoom = mapCfg.zoom || 7;

  const container = document.getElementById(containerId);
  if (container) container.style.backgroundColor = 'white';

  mapInstance = L.map(containerId, {
    center,
    zoom,
    zoomSnap: mapCfg.zoom_snap ?? 0,
    zoomDelta: mapCfg.zoom_delta ?? 0.5,
    fadeAnimation: mapCfg.fade_animation ?? true,
    markerZoomAnimation: mapCfg.marker_zoom_animation ?? true,
    zoomControl: false,
    attributionControl: false,
    preferCanvas: true,
    scrollWheelZoom: false,
    smoothWheelZoom: true,
    smoothSensitivity: mapCfg.smooth_sensitivity ?? 1,
  });

  L.control.zoom({ position: 'topleft' }).addTo(mapInstance);

  return mapInstance;
}

export function getMap() {
  return mapInstance;
}
