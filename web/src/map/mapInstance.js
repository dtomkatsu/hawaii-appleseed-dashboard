import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';

let mapInstance = null;

class ResetControl {
  constructor(center, zoom) {
    this._center = center;
    this._zoom = zoom;
  }
  onAdd(map) {
    this._map = map;
    const container = document.createElement('div');
    container.className = 'maplibregl-ctrl maplibregl-ctrl-group';
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'maplibre-reset-zoom';
    btn.title = 'Reset view';
    btn.setAttribute('aria-label', 'Reset view');
    btn.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="14" height="14"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/></svg>';
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      map.easeTo({ center: this._center, zoom: this._zoom, duration: 400 });
    });
    container.appendChild(btn);
    this._container = container;
    return container;
  }
  onRemove() {
    this._container?.parentNode?.removeChild(this._container);
    this._map = undefined;
  }
}

export function createMap(containerId, theme) {
  if (mapInstance) return mapInstance;

  const mapCfg = (theme && theme.map) || {};
  // theme.json stores center as [lat, lng] (Leaflet order). MapLibre wants [lng, lat].
  const themeCenter = mapCfg.center || [20.7984, -156.3319];
  const center = [themeCenter[1], themeCenter[0]];
  const zoom = mapCfg.zoom || 7;
  const background = (theme && theme.background) || '#fcfcf9';

  const container = document.getElementById(containerId);
  if (container) container.style.backgroundColor = 'white';

  mapInstance = new maplibregl.Map({
    container: containerId,
    style: {
      version: 8,
      sources: {},
      layers: [
        { id: 'bg', type: 'background', paint: { 'background-color': background } },
      ],
    },
    center,
    zoom,
    minZoom: 5,
    maxZoom: 16,
    attributionControl: false,
    fadeDuration: mapCfg.fade_animation === false ? 0 : 300,
    dragRotate: false,
    pitchWithRotate: false,
    touchZoomRotate: true,
  });
  mapInstance.touchZoomRotate?.disableRotation();

  mapInstance.addControl(new maplibregl.NavigationControl({ showCompass: false, visualizePitch: false }), 'top-left');
  mapInstance.addControl(new ResetControl(center, zoom), 'top-left');

  // Dev only: expose the map on window for in-browser debugging.
  if (typeof window !== 'undefined' && import.meta.env?.DEV) window.__map = mapInstance;

  // Grey circle cursor — native OS cursor via SVG data URI. Hotspot at the
  // center of the 24×24 SVG (12, 12). Updated by the compositor at hardware
  // refresh rate without any JS or layout work per pointer move. Falls back to
  // `auto` over child elements that set their own cursor (e.g. control buttons).
  const CURSOR_SVG =
    "<svg xmlns='http://www.w3.org/2000/svg' width='24' height='24'>" +
      "<circle cx='12' cy='12' r='10' " +
        "fill='%238c8c8c' fill-opacity='0.25' " +
        "stroke='%23646464' stroke-opacity='0.55' stroke-width='1.5'/>" +
    "</svg>";
  if (container) {
    container.style.cursor = `url("data:image/svg+xml;utf8,${CURSOR_SVG}") 12 12, auto`;
  }

  return mapInstance;
}

export function getMap() {
  return mapInstance;
}
