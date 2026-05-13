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
    pixelRatio: Math.min(window.devicePixelRatio ?? 1, 1.5),
  });
  mapInstance.touchZoomRotate?.disableRotation();

  mapInstance.addControl(new maplibregl.NavigationControl({ showCompass: false, visualizePitch: false }), 'top-left');
  mapInstance.addControl(new ResetControl(center, zoom), 'top-left');

  // Dev only: expose the map on window for in-browser debugging.
  if (typeof window !== 'undefined' && import.meta.env?.DEV) window.__map = mapInstance;

  // Grey circle cursor — native OS cursor via base64 SVG data URI.
  // Hotspot at center of 24×24 SVG (12, 12). Covers the inner canvas as well
  // as the canvas-container with all three MapLibre cursor-state classes
  // (interactive / track-pointer / :active grabbing) so our cursor wins
  // regardless of which state MapLibre toggles into.
  const CURSOR_SVG_SRC =
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24">' +
      '<circle cx="12" cy="12" r="9.5" ' +
        'fill="rgba(140,140,140,0.35)" ' +
        'stroke="rgba(40,40,40,0.85)" stroke-width="1.5"/>' +
    '</svg>';
  const CURSOR_B64 = btoa(CURSOR_SVG_SRC);
  const CURSOR_VAL = `url("data:image/svg+xml;base64,${CURSOR_B64}") 12 12, auto`;
  if (containerId) {
    const styleEl = document.createElement('style');
    // Cover every MapLibre cursor-state class + the inner canvas with both
    // !important and high specificity (ID + multiple classes) so MapLibre's
    // CSS-class-driven cursor changes can never win.
    styleEl.textContent =
      `#${containerId} .maplibregl-canvas-container,
       #${containerId} .maplibregl-canvas-container.maplibregl-interactive,
       #${containerId} .maplibregl-canvas-container.maplibregl-interactive:active,
       #${containerId} .maplibregl-canvas-container.maplibregl-interactive.maplibregl-track-pointer,
       #${containerId} .maplibregl-canvas {
         cursor: ${CURSOR_VAL} !important;
       }`;
    document.head.appendChild(styleEl);
  }

  return mapInstance;
}

export function getMap() {
  return mapInstance;
}
