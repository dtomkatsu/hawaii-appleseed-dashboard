import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { FLAGS } from './perfFlags.js';
import { installSmoothWheelZoom } from './smoothWheelZoom.js';

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

  const mapOpts = {
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
  };
  if (FLAGS.lowDpr != null && !Number.isNaN(FLAGS.lowDpr)) {
    mapOpts.pixelRatio = FLAGS.lowDpr;
  }
  mapInstance = new maplibregl.Map(mapOpts);
  mapInstance.touchZoomRotate?.disableRotation();

  if (!FLAGS.noNav) {
    mapInstance.addControl(new maplibregl.NavigationControl({ showCompass: false, visualizePitch: false }), 'top-left');
    mapInstance.addControl(new ResetControl(center, zoom), 'top-left');
  }

  // Replace MapLibre's built-in wheel-zoom handler with a custom rAF-driven
  // one that produces 0% zoom-progression stalls (the built-in handler
  // stalls every ~3rd frame during continuous wheel input). Opt out with
  // ?stock=1 for A/B testing.
  if (!FLAGS.stockWheelZoom) {
    installSmoothWheelZoom(mapInstance);
  }

  // Dev only: expose the map on window for in-browser debugging.
  if (typeof window !== 'undefined' && import.meta.env?.DEV) window.__map = mapInstance;


  return mapInstance;
}

export function getMap() {
  return mapInstance;
}
