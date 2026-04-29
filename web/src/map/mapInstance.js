import L from 'leaflet';

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
    zoomDelta: 0.25,
    fadeAnimation: mapCfg.fade_animation ?? true,
    markerZoomAnimation: mapCfg.marker_zoom_animation ?? true,
    zoomControl: false,
    attributionControl: false,
    preferCanvas: false,
    renderer: L.svg({ padding: 1.0 }),
    scrollWheelZoom: true,
    wheelPxPerZoomLevel: 40,
    wheelDebounceTime: 20,
  });

  L.control.zoom({ position: 'topleft' }).addTo(mapInstance);

  const ResetControl = L.Control.extend({
    options: { position: 'topleft' },
    onAdd(map) {
      const btn = L.DomUtil.create('button', 'leaflet-bar leaflet-control leaflet-reset-zoom');
      btn.title = 'Reset view';
      btn.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="14" height="14"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/></svg>';
      L.DomEvent.on(btn, 'click', (e) => {
        L.DomEvent.stopPropagation(e);
        map.setView(center, zoom);
      });
      return btn;
    },
  });
  new ResetControl().addTo(mapInstance);

  return mapInstance;
}

export function getMap() {
  return mapInstance;
}
