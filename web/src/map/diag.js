// Comprehensive runtime diagnostics for the map.
//
// window.__diag exposes:
//   __diag.startCapture()       → begin recording frame/event/task data
//   __diag.stopCapture()        → end recording, returns summary
//   __diag.reset()              → clear all buffers
//   __diag.fps()                → mean FPS over the last 1s window
//   __diag.dump()               → one-line summary
//   __diag.snapshot()           → full snapshot of recorded data
//
// Capture buffers (all reset on startCapture):
//   __diag._frames              → array of frame intervals (ms)
//   __diag._longTasks           → array of {start, duration, name}
//   __diag._wheelLatencies      → array of {wheelTs, firstPaintTs, dt}
//   __diag._renderEvents        → array of timestamps of MapLibre render fires
//
// Designed to be cheap when not capturing: most observers stay attached
// but their callbacks check the _capturing flag and bail.

let _fpsBucketStart = performance.now();
let _fpsCount = 0;
let _lastFps = 0;
let _rafId = null;

let _capturing = false;
let _captureStart = 0;
let _frames = [];
let _longTasks = [];
let _wheelLatencies = [];
let _renderEvents = [];
let _pendingWheel = null; // { ts } awaiting next paint

let _lastFrameTs = 0;

function fpsAndFrameTick() {
  _fpsCount++;
  const now = performance.now();

  // FPS bucket (always-on, 1s rolling mean — same as before).
  if (now - _fpsBucketStart >= 1000) {
    _lastFps = (_fpsCount * 1000) / (now - _fpsBucketStart);
    _fpsBucketStart = now;
    _fpsCount = 0;
  }

  // Frame-interval capture.
  if (_capturing) {
    if (_lastFrameTs) _frames.push(+(now - _lastFrameTs).toFixed(2));
    if (_pendingWheel) {
      _wheelLatencies.push({ wheelTs: _pendingWheel.ts, firstPaintTs: now, dt: +(now - _pendingWheel.ts).toFixed(2) });
      _pendingWheel = null;
    }
  }
  _lastFrameTs = now;

  _rafId = requestAnimationFrame(fpsAndFrameTick);
}

function attachLongTaskObserver() {
  if (typeof PerformanceObserver === 'undefined') return;
  try {
    const obs = new PerformanceObserver((list) => {
      if (!_capturing) return;
      for (const e of list.getEntries()) {
        _longTasks.push({ start: +e.startTime.toFixed(2), duration: +e.duration.toFixed(2), name: e.name });
      }
    });
    obs.observe({ entryTypes: ['longtask'] });
  } catch (_) { /* not supported */ }
}

function attachWheelInputLatency() {
  // Capture-phase listener on window so we get the wheel event before any
  // handler runs. The next rAF callback (which happens after MapLibre has
  // processed the wheel and committed any layout) marks "first paint after
  // wheel" — the perceived input→visual lag.
  window.addEventListener('wheel', () => {
    if (!_capturing) return;
    if (!_pendingWheel) _pendingWheel = { ts: performance.now() };
  }, { capture: true, passive: true });
}

function attachRenderCounter(map) {
  if (!map || map._diagRenderAttached) return;
  map._diagRenderAttached = true;
  map.on('render', () => {
    if (_capturing) _renderEvents.push(+performance.now().toFixed(2));
  });
}

function pct(sorted, p) {
  if (!sorted.length) return 0;
  const i = Math.min(sorted.length - 1, Math.floor(sorted.length * p));
  return sorted[i];
}

function summarizeFrames(frames) {
  if (!frames.length) return { n: 0 };
  const sorted = frames.slice().sort((a, b) => a - b);
  const sum = sorted.reduce((s, v) => s + v, 0);
  return {
    n: sorted.length,
    mean: +(sum / sorted.length).toFixed(2),
    p50: +pct(sorted, 0.5).toFixed(2),
    p95: +pct(sorted, 0.95).toFixed(2),
    p99: +pct(sorted, 0.99).toFixed(2),
    max: +sorted[sorted.length - 1].toFixed(2),
    // Histogram bins (ms)
    bins: {
      '<17': sorted.filter((v) => v < 17).length,
      '17-20': sorted.filter((v) => v >= 17 && v < 20).length,
      '20-25': sorted.filter((v) => v >= 20 && v < 25).length,
      '25-33': sorted.filter((v) => v >= 25 && v < 33).length,
      '33-50': sorted.filter((v) => v >= 33 && v < 50).length,
      '50-100': sorted.filter((v) => v >= 50 && v < 100).length,
      '>=100': sorted.filter((v) => v >= 100).length,
    },
  };
}

function summarize() {
  const elapsed = performance.now() - _captureStart;
  return {
    elapsed_ms: +elapsed.toFixed(0),
    frames: summarizeFrames(_frames),
    long_tasks: {
      n: _longTasks.length,
      total_ms: +_longTasks.reduce((s, e) => s + e.duration, 0).toFixed(1),
      worst: _longTasks.slice().sort((a, b) => b.duration - a.duration).slice(0, 5),
    },
    wheel_latency: summarizeFrames(_wheelLatencies.map((w) => w.dt)),
    render_events: _renderEvents.length,
    render_rate_per_s: +((_renderEvents.length / elapsed) * 1000).toFixed(1),
  };
}

function startCapture() {
  _capturing = true;
  _captureStart = performance.now();
  _frames = [];
  _longTasks = [];
  _wheelLatencies = [];
  _renderEvents = [];
  _pendingWheel = null;
}

function stopCapture() {
  _capturing = false;
  return summarize();
}

function reset() { startCapture(); stopCapture(); }

function dump() {
  const map = window.__map;
  return {
    fps: Math.round(_lastFps),
    canvas: map ? `${map.getCanvas().width}x${map.getCanvas().height}` : null,
    dpr: window.devicePixelRatio,
    flags: window.__perfFlags || null,
  };
}

export function initDiag() {
  if (typeof window === 'undefined') return;
  _fpsBucketStart = performance.now();
  _rafId = requestAnimationFrame(fpsAndFrameTick);
  attachLongTaskObserver();
  attachWheelInputLatency();
  const iv = setInterval(() => {
    if (window.__map) {
      attachRenderCounter(window.__map);
      clearInterval(iv);
    }
  }, 200);

  window.__diag = {
    fps: () => Math.round(_lastFps),
    startCapture, stopCapture, reset, dump,
    snapshot: () => ({
      frames: _frames.slice(),
      longTasks: _longTasks.slice(),
      wheelLatencies: _wheelLatencies.slice(),
      renderEvents: _renderEvents.slice(),
    }),
  };
  console.log('[diag] window.__diag ready. Try __diag.startCapture() / __diag.stopCapture()');
}
