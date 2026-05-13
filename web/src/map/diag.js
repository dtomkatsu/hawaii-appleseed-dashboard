// Lightweight runtime diagnostics for the map.
// Exposes window.__diag with:
//   __diag.fps()              → mean FPS over the last 1s window
//   __diag.start()/stop()     → toggle FPS sampler
//   __diag.disableCursor()    → strip our custom-cursor <style> (restore native)
//   __diag.enableCursor()     → reinsert it
//   __diag.events()           → recent mousemove / render rate (ev/s)
//   __diag.dump()             → one-line summary
//
// Goal: enable/disable suspected lag sources LIVE so we can A/B test in the
// browser without code edits + reloads. Dev-mode only — no overhead in prod.

let _fpsBucketStart = performance.now();
let _fpsCount = 0;
let _lastFps = 0;
let _rafId = null;

let _mmCount = 0;
let _mmBucketStart = performance.now();
let _mmRate = 0;

let _renderCount = 0;
let _renderBucketStart = performance.now();
let _renderRate = 0;

function fpsTick() {
  _fpsCount++;
  const now = performance.now();
  if (now - _fpsBucketStart >= 1000) {
    _lastFps = (_fpsCount * 1000) / (now - _fpsBucketStart);
    _fpsBucketStart = now;
    _fpsCount = 0;
  }
  _rafId = requestAnimationFrame(fpsTick);
}

function startFps() {
  if (_rafId) return;
  _fpsBucketStart = performance.now();
  _fpsCount = 0;
  _rafId = requestAnimationFrame(fpsTick);
}

function stopFps() {
  if (_rafId) { cancelAnimationFrame(_rafId); _rafId = null; }
}

function attachMouseMoveCounter() {
  const el = document.getElementById('main-map');
  if (!el || el._diagAttached) return;
  el._diagAttached = true;
  el.addEventListener('mousemove', () => {
    _mmCount++;
    const now = performance.now();
    if (now - _mmBucketStart >= 1000) {
      _mmRate = (_mmCount * 1000) / (now - _mmBucketStart);
      _mmBucketStart = now;
      _mmCount = 0;
    }
  }, { capture: true, passive: true });
}

function attachRenderCounter(map) {
  if (!map || map._diagRenderAttached) return;
  map._diagRenderAttached = true;
  map.on('render', () => {
    _renderCount++;
    const now = performance.now();
    if (now - _renderBucketStart >= 1000) {
      _renderRate = (_renderCount * 1000) / (now - _renderBucketStart);
      _renderBucketStart = now;
      _renderCount = 0;
    }
  });
}

let _cursorHidden = false;

function disableCursor() {
  const el = document.getElementById('fake-cursor');
  if (el) {
    el.style.display = 'none';
    _cursorHidden = true;
    console.log('[diag] fake cursor hidden');
  }
}

function enableCursor() {
  const el = document.getElementById('fake-cursor');
  if (el) {
    el.style.display = '';
    _cursorHidden = false;
    console.log('[diag] fake cursor shown');
  }
}

function dump() {
  const map = window.__map;
  const layers = map ? map.getStyle().layers.length : 0;
  const hasShadow = map ? !!map.getLayer('selection-shadow') : false;
  const dpr = window.devicePixelRatio;
  const buf = map ? map.getCanvas() : null;
  return {
    fps: Math.round(_lastFps),
    mousemove_per_s: Math.round(_mmRate),
    map_render_per_s: Math.round(_renderRate),
    map_layers: layers,
    has_shadow_layer: hasShadow,
    dpr,
    canvas_size: buf ? `${buf.width}×${buf.height}` : null,
    cursor_disabled: _cursorHidden,
  };
}

export function initDiag() {
  if (typeof window === 'undefined' || !import.meta.env?.DEV) return;
  startFps();
  attachMouseMoveCounter();
  // Map may not exist yet — poll briefly.
  const iv = setInterval(() => {
    if (window.__map) {
      attachRenderCounter(window.__map);
      clearInterval(iv);
    }
  }, 200);

  window.__diag = {
    fps: () => Math.round(_lastFps),
    events: () => ({
      mousemove_per_s: Math.round(_mmRate),
      map_render_per_s: Math.round(_renderRate),
    }),
    start: startFps,
    stop: stopFps,
    disableCursor,
    enableCursor,
    dump,
  };
  console.log('[diag] window.__diag ready. Try __diag.dump() while panning.');
}
