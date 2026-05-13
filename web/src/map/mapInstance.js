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

  // Circle cursor — drawn as a DOM div positioned by transform: translate3d.
  // Why not `cursor: url(svg)`?  That makes the OS cursor a *software* cursor,
  // which is repainted at the page's 60 Hz refresh.  The default OS arrow is
  // a hardware cursor sampled at ~125 Hz; the difference is perceived as
  // "the map is laggy" even when the GL render itself stays at 60 fps.
  //
  // A DOM-positioned cursor renders at the same 60 Hz cadence as the map, so
  // they move in perfect lockstep with no perceptual mismatch.  Updating via
  // `transform: translate3d(x, y, 0)` keeps the element on the GPU compositor
  // and avoids layout/paint cost per mousemove (the earlier fake-cursor used
  // `style.left/top` which forced layout each frame — that was the laggy bit).
  if (container) {
    container.style.cursor = 'none';
    const cur = document.createElement('div');
    cur.id = 'fake-cursor';
    cur.style.cssText = [
      'position:absolute',
      'left:0',
      'top:0',
      'width:20px',
      'height:20px',
      'margin:-10px 0 0 -10px',     // center on (left, top) origin
      'border-radius:50%',
      'background:rgba(140,140,140,0.35)',
      'border:1.5px solid rgba(40,40,40,0.85)',
      'pointer-events:none',
      'z-index:1000',
      'will-change:transform',
      'transform:translate3d(-100px,-100px,0)',
      'opacity:0',                  // hidden until first move
      'transition:opacity 80ms linear',
    ].join(';');
    container.appendChild(cur);

    // Update via transform only — composited on GPU, no layout flush.
    let rafPending = false;
    let lastX = 0, lastY = 0;
    const onMove = (e) => {
      const rect = container.getBoundingClientRect();
      lastX = e.clientX - rect.left;
      lastY = e.clientY - rect.top;
      if (rafPending) return;
      rafPending = true;
      requestAnimationFrame(() => {
        rafPending = false;
        cur.style.transform = `translate3d(${lastX}px,${lastY}px,0)`;
        if (cur.style.opacity !== '1') cur.style.opacity = '1';
      });
    };
    const onLeave = () => { cur.style.opacity = '0'; };
    container.addEventListener('mousemove', onMove, { passive: true });
    container.addEventListener('mouseleave', onLeave, { passive: true });
    container.addEventListener('mouseenter', onMove, { passive: true });

    // Children with their own cursor (zoom buttons etc.) should still show
    // them — inject a rule that re-shows the OS cursor over interactive
    // controls so the fake circle doesn't compete with them.
    const styleEl = document.createElement('style');
    styleEl.textContent =
      `#${containerId} .maplibregl-ctrl-group button,
       #${containerId} .maplibregl-ctrl-group button * { cursor: pointer; }`;
    document.head.appendChild(styleEl);
  }

  return mapInstance;
}

export function getMap() {
  return mapInstance;
}
