import { getMap } from './mapInstance.js';
import { getThresholds, getSchemeColors } from './colors.js';
import { loadLayer, fetchJson } from '../data/loader.js';
import { bindLayerInteraction, bindPointsInteraction, clearSelectedLayer } from './popup.js';
import { registerShadowLayer, prewarmShadowLayer, setShadowFeature, SHADOW_LAYER_ID } from './shadowLayer.js';
import { FLAGS } from './perfFlags.js';

// Variables config — needed to look up render_type / points_data per variable.
// Set once at boot via initLayerManager(config.variables).
let VARIABLES = null;
export function initLayerManager(variablesConfig) {
  VARIABLES = variablesConfig?.variables || null;
}

function isPointsVariable(varKey) {
  return VARIABLES?.[varKey]?.render_type === 'points';
}

// Tracks the currently-rendered city-points layer (Millionaires-style data).
// Null when no points variable is active.
let pointsLayerActive = null; // { layerId, sourceId, varKey, countField }

// Muted backdrop fill applied to the choropleth when points mode is active —
// the underlying islands stay recognizable since this map has no tile basemap.
const POINTS_MODE_MUTED_FILL = '#b8cdaf';
const POINTS_MODE_MUTED_LINE = '#5c7757';

// When ?notrans=1 strip the 300ms opacity transitions; when ?nofade=1 also
// skip the layer-switch fade-in/fade-out animation.
const TRANSITION_PAINT = FLAGS.noTransitions
  ? {}
  : { 'fill-opacity-transition': { duration: 300, delay: 0 } };
const LINE_TRANSITION_PAINT = FLAGS.noTransitions
  ? {}
  : { 'line-opacity-transition': { duration: 300, delay: 0 } };

const LEVELS = ['state', 'county', 'house', 'senate'];
const cachedGeoJson = new Map();
const registeredLevels = new Set();
let currentLevel = null;
let currentVariable = null;
let currentScheme = null;
let reliabilityOn = false;

// ── Reliability hatch overlay ───────────────────────────────────────────────
// Opt-in (checkbox) diagonal-hatch overlay marking districts whose ACS estimate
// for the active variable is statistically shaky. Two tiers by coefficient of
// variation (CV = (MOE/1.645)/|value|): caution 15–30% (sparse single hatch),
// unreliable >30% (denser cross-hatch). Computed client-side from the value and
// its <var>_moe column — no data change. A near-zero guard skips tiny estimates
// (where CV explodes but the absolute error is immaterial).
const RELIABILITY_PATTERN_CAUTION = 'reliability-hatch-caution';
const RELIABILITY_PATTERN_UNRELIABLE = 'reliability-hatch-unreliable';
const CV_CAUTION = 0.15;
const CV_UNRELIABLE = 0.30;
let hatchPatternsReady = false;

function makeHatchImage({ size, spacing, cross, alpha }) {
  const canvas = document.createElement('canvas');
  canvas.width = canvas.height = size;
  const ctx = canvas.getContext('2d');
  ctx.clearRect(0, 0, size, size);
  ctx.strokeStyle = `rgba(40, 50, 56, ${alpha})`;
  ctx.lineWidth = 1;
  ctx.beginPath();
  for (let i = -size; i < size * 2; i += spacing) {
    ctx.moveTo(i, 0); ctx.lineTo(i + size, size);        // "\" diagonal
    if (cross) { ctx.moveTo(i + size, 0); ctx.lineTo(i, size); } // "/" diagonal
  }
  ctx.stroke();
  const img = ctx.getImageData(0, 0, size, size);
  return { width: size, height: size, data: new Uint8Array(img.data.buffer) };
}

function registerHatchPatterns(map) {
  if (hatchPatternsReady) return;
  if (!map.hasImage(RELIABILITY_PATTERN_CAUTION)) {
    map.addImage(RELIABILITY_PATTERN_CAUTION,
      makeHatchImage({ size: 12, spacing: 6, cross: false, alpha: 0.40 }), { pixelRatio: 2 });
  }
  if (!map.hasImage(RELIABILITY_PATTERN_UNRELIABLE)) {
    map.addImage(RELIABILITY_PATTERN_UNRELIABLE,
      makeHatchImage({ size: 12, spacing: 4, cross: true, alpha: 0.55 }), { pixelRatio: 2 });
  }
  hatchPatternsReady = true;
}

// Reliability flags only apply to Census (ACS) variables that carry a margin of
// error. Other sources (SNAP/ALICE/tax credits) have no sampling MOE to assess.
function variableHasMoe(varKey) {
  return VARIABLES?.[varKey]?.data_source === 'acs';
}

function cvExpression(variable) {
  // CV = (MOE / 1.645) / max(|value|, ε)
  return ['/',
    ['/', ['to-number', ['get', `${variable}_moe`]], 1.645],
    ['max', ['abs', ['to-number', ['get', variable]]], 1e-9],
  ];
}

function reliabilityFilter(variable) {
  const thresholds = getThresholds(variable) || [];
  const floor = (thresholds[0] || 0) * 0.5; // near-zero guard anchored to scale
  return [
    'all',
    ['has', variable],
    ['has', `${variable}_moe`],
    ['==', ['typeof', ['get', variable]], 'number'],
    ['==', ['typeof', ['get', `${variable}_moe`]], 'number'],
    ['>=', ['abs', ['to-number', ['get', variable]]], floor],
    ['>', cvExpression(variable), CV_CAUTION],
  ];
}

function reliabilityPatternExpr(variable) {
  return ['case',
    ['>', cvExpression(variable), CV_UNRELIABLE], RELIABILITY_PATTERN_UNRELIABLE,
    RELIABILITY_PATTERN_CAUTION,
  ];
}

const FADE_MS = 300;
const pendingHide = new Map(); // level → setTimeout id

// Opacity expressions as constants so fade-in can restore them after zeroing out.
// 0.75 idle → 0.92 on hover → 1.0 when selected. Combined with the
// fill-opacity-transition (300ms) this gives a soft "brighten" feel when the
// cursor enters a geo — no extra layer needed.
const FILL_OPACITY_EXPR = [
  'case',
  ['boolean', ['feature-state', 'selected'], false], 1.0,
  ['boolean', ['feature-state', 'hover'], false], 0.92,
  0.75,
];

// Feature-state gated value: returns `whenSelected` if the feature has selected
// state, else `whenNot` (0). Used for opacity, width, etc.
const selectedCase = (whenSelected, whenNot = 0) => [
  'case',
  ['boolean', ['feature-state', 'selected'], false], whenSelected,
  whenNot,
];

// The selected-feature drop shadow lives in a custom WebGL layer
// (`./shadowLayer.js`) registered globally on the map — see
// `registerShadowLayer()`. The legacy stacked fill-translate shadow has
// been removed in favor of a true Gaussian blur.

// Some variables carry text-prefixed numeric values (e.g., cep_display = "5/9 CEP
// schools"). MapLibre's to-number returns NaN for those strings, so we mirror
// every string-numeric property as `_num_<key>` (a real number) at cache time
// and prefer that mirror in the color expression.
function preprocessFeatures(data) {
  if (!data || !data.features) return data;
  for (const feat of data.features) {
    const props = feat.properties;
    if (!props) continue;
    for (const [k, v] of Object.entries(props)) {
      if (typeof v !== 'string' || v.length === 0) continue;
      if (k.startsWith('_num_')) continue;
      const n = parseFloat(v);
      if (isFinite(n)) props['_num_' + k] = n;
    }
  }
  return data;
}

function colorExpression(variable, scheme) {
  const thresholds = getThresholds(variable);
  const colors = getSchemeColors(scheme);
  if (!variable || !thresholds || thresholds.length === 0 || !colors || colors.length === 0) {
    return '#cccccc';
  }
  const numField = '_num_' + variable;
  // Resolve a numeric value: prefer the precomputed mirror, else the native
  // number if the property is numeric, else 0 (the outer case catches missing
  // data and routes to gray, so this 0 path is unreachable for real renders).
  const numericValue = [
    'case',
    ['has', numField], ['get', numField],
    ['==', ['typeof', ['get', variable]], 'number'], ['to-number', ['get', variable]],
    0,
  ];
  const step = ['step', numericValue, colors[0]];
  for (let i = 0; i < thresholds.length; i++) {
    step.push(thresholds[i], colors[Math.min(i + 1, colors.length - 1)]);
  }
  return [
    'case',
    ['all',
      ['!', ['has', numField]],
      ['!=', ['typeof', ['get', variable]], 'number'],
    ], '#cccccc',
    step,
  ];
}

function fillLayerIds(level) {
  return [
    `${level}-fill`,
    `${level}-line`,
    `${level}-selected`,
    `${level}-hover`,
  ];
}

function ensureSourceAndLayers(map, level, data) {
  if (registeredLevels.has(level)) return;

  registerHatchPatterns(map);

  map.addSource(level, {
    type: 'geojson',
    data,
    promoteId: 'GEOID',
  });

  // Fill — colored by current variable. The drop shadow lives in a separate
  // global custom WebGL layer (`./shadowLayer.js`); we just make sure it
  // remains below this fill via `map.moveLayer` after registration.
  map.addLayer({
    id: `${level}-fill`,
    type: 'fill',
    source: level,
    layout: { visibility: 'none' },
    paint: {
      'fill-color': '#cccccc',
      'fill-opacity': FILL_OPACITY_EXPR,
      ...TRANSITION_PAINT,
    },
  });

  // Reliability hatch overlay — sits above the colored fill, below the
  // outlines. Hidden by default; shown (and filtered to flagged features for
  // the active variable) only when the reliability checkbox is on.
  map.addLayer({
    id: `${level}-reliability`,
    type: 'fill',
    source: level,
    layout: { visibility: 'none' },
    paint: {
      'fill-pattern': RELIABILITY_PATTERN_CAUTION,
      'fill-opacity': 0.9,
    },
    filter: ['==', ['get', 'GEOID'], ' '], // matches nothing until applied
  });

  // Default outline
  map.addLayer({
    id: `${level}-line`,
    type: 'line',
    source: level,
    layout: { visibility: 'none' },
    paint: {
      'line-color': '#aaaaaa',
      'line-width': 1,
      'line-opacity': 1,
      ...LINE_TRANSITION_PAINT,
    },
  });

  // Selected: thin, soft inner outline. Kept subtle so the drop shadow
  // does the heavy visual lifting and the polygon "lifts off" the map
  // without a heavy black border competing for attention.
  map.addLayer({
    id: `${level}-selected`,
    type: 'line',
    source: level,
    layout: { visibility: 'none' },
    paint: {
      'line-color': '#333333',
      'line-width': [
        'case',
        ['boolean', ['feature-state', 'selected'], false], 1.25,
        0,
      ],
      'line-opacity': 0.5,
      ...LINE_TRANSITION_PAINT,
    },
  });

  // Hover: thin, light inner ring + opacity bump on the fill (see
  // FILL_OPACITY_EXPR). Suppressed when selected so the selection
  // outline doesn't fight a hover ring.
  map.addLayer({
    id: `${level}-hover`,
    type: 'line',
    source: level,
    layout: { visibility: 'none' },
    paint: {
      'line-color': '#1a1a1a',
      'line-width': [
        'case',
        ['all',
          ['boolean', ['feature-state', 'hover'], false],
          ['!', ['boolean', ['feature-state', 'selected'], false]],
        ], 1.25,
        0,
      ],
      'line-opacity': 0.45,
      ...LINE_TRANSITION_PAINT,
    },
  });

  if (!FLAGS.noHover) bindLayerInteraction(map, level);
  registeredLevels.add(level);
}

function restoreTargetOpacities(map, level) {
  if (map.getLayer(`${level}-fill`))
    map.setPaintProperty(`${level}-fill`, 'fill-opacity', FILL_OPACITY_EXPR);
  if (map.getLayer(`${level}-line`))
    map.setPaintProperty(`${level}-line`, 'line-opacity', 1);
  if (map.getLayer(`${level}-selected`))
    map.setPaintProperty(`${level}-selected`, 'line-opacity', 0.5);
  if (map.getLayer(`${level}-hover`))
    map.setPaintProperty(`${level}-hover`, 'line-opacity', 0.45);
}

function fadeInLevel(map, level) {
  // Cancel any in-flight hide for this level
  if (pendingHide.has(level)) {
    clearTimeout(pendingHide.get(level));
    pendingHide.delete(level);
  }

  const ids = fillLayerIds(level);
  for (const id of ids) {
    if (!map.getLayer(id)) continue;
    const layerType = map.getLayer(id).type;
    if (layerType === 'fill') map.setPaintProperty(id, 'fill-opacity', 0);
    else map.setPaintProperty(id, 'line-opacity', 0);
    map.setLayoutProperty(id, 'visibility', 'visible');
  }

  // Restore target opacities on the next frame so MapLibre animates from 0.
  requestAnimationFrame(() => restoreTargetOpacities(map, level));
}

function fadeOutLevel(map, level) {
  const ids = fillLayerIds(level);
  for (const id of ids) {
    if (!map.getLayer(id)) continue;
    const layerType = map.getLayer(id).type;
    if (layerType === 'fill') map.setPaintProperty(id, 'fill-opacity', 0);
    else map.setPaintProperty(id, 'line-opacity', 0);
  }
  const tid = setTimeout(() => {
    pendingHide.delete(level);
    for (const id of ids) {
      if (map.getLayer(id)) map.setLayoutProperty(id, 'visibility', 'none');
    }
  }, FADE_MS + 50);
  pendingHide.set(level, tid);
}

function applyColorExpression(map, level) {
  if (!map.getLayer(`${level}-fill`)) return;
  // In points mode, the choropleth becomes a muted sage backdrop so the
  // circle markers carry all the data signal. Otherwise paint by variable.
  if (pointsLayerActive) {
    map.setPaintProperty(`${level}-fill`, 'fill-color', POINTS_MODE_MUTED_FILL);
    if (map.getLayer(`${level}-line`)) {
      map.setPaintProperty(`${level}-line`, 'line-color', POINTS_MODE_MUTED_LINE);
    }
  } else {
    map.setPaintProperty(`${level}-fill`, 'fill-color', colorExpression(currentVariable, currentScheme));
    if (map.getLayer(`${level}-line`)) {
      map.setPaintProperty(`${level}-line`, 'line-color', '#aaaaaa');
    }
  }
}

// Apply the reliability overlay for one level: visible only when the toggle is
// on, the active variable is an ACS metric with MOE, and we're not in points
// mode. When shown, the filter + pattern are rebuilt for the current variable.
function applyReliability(map, level) {
  const layerId = `${level}-reliability`;
  if (!map.getLayer(layerId)) return;
  const on = reliabilityOn && !pointsLayerActive && variableHasMoe(currentVariable);
  if (!on) {
    map.setLayoutProperty(layerId, 'visibility', 'none');
    return;
  }
  map.setFilter(layerId, reliabilityFilter(currentVariable));
  map.setPaintProperty(layerId, 'fill-pattern', reliabilityPatternExpr(currentVariable));
  map.setLayoutProperty(layerId, 'visibility', 'visible');
}

// Re-apply across all levels: show the active level's overlay, hide the rest.
function refreshReliability() {
  const map = getMap();
  if (!map) return;
  for (const level of registeredLevels) {
    if (level === currentLevel) applyReliability(map, level);
    else if (map.getLayer(`${level}-reliability`)) {
      map.setLayoutProperty(`${level}-reliability`, 'visibility', 'none');
    }
  }
}

export function setReliability(on) {
  reliabilityOn = on;
  refreshReliability();
}

// ---------------------------------------------------------------------------
// City-points layer (Millionaires-style) — circle markers per town
//
// Driven by variables.json entries with `render_type: "points"` and
// `points_data: "<file>.json"` (a GeoJSON FeatureCollection in
// /public/data/). Markers scale with sqrt(count) and grow with zoom via
// a MapLibre `interpolate` expression so single-count dots stay legible
// when zoomed into one island, without dwarfing islands at fit-bounds.
// ---------------------------------------------------------------------------

function buildCircleRadiusExpr(countField) {
  // base = max(5, min(20, 3 + sqrt(count) * 1.4))  — the "fit-bounds" size
  const sqrtCount = ['sqrt', ['to-number', ['coalesce', ['get', countField], 0]]];
  const base = ['max', 5, ['min', 20, ['+', 3, ['*', sqrtCount, 1.4]]]];
  return [
    'interpolate', ['linear'], ['zoom'],
    6,  base,
    11, ['min', 32, ['*', base, 1.75]],
    14, ['min', 36, ['*', base, 2.5]],
  ];
}

function buildCircleColorExpr(countField, thresholds, colors) {
  const value = ['to-number', ['coalesce', ['get', countField], 0]];
  const step = ['step', value, colors[0]];
  for (let i = 0; i < thresholds.length; i++) {
    step.push(thresholds[i], colors[Math.min(i + 1, colors.length - 1)]);
  }
  return step;
}

async function showPointsLayer(map, varKey) {
  const meta = VARIABLES?.[varKey];
  if (!meta || meta.render_type !== 'points') return;

  // If a different points variable is already up, swap it out.
  if (pointsLayerActive && pointsLayerActive.varKey !== varKey) {
    removePointsLayer(map);
  }
  // Same variable already active — just refresh paint (scheme may have changed).
  if (pointsLayerActive && pointsLayerActive.varKey === varKey) {
    updatePointsPaint(map);
    return;
  }

  const sourceId = `points-source-${varKey}`;
  const layerId = `points-${varKey}`;
  const dataPath = meta.points_data || `${varKey}.json`;
  const countField = meta.csv_column || 'value';

  let data;
  try {
    data = await fetchJson(`/data/${dataPath}`);
  } catch (err) {
    console.error(`Points layer load failed for ${varKey}:`, err);
    return;
  }

  if (!map.getSource(sourceId)) {
    map.addSource(sourceId, { type: 'geojson', data });
  }

  const colors = getSchemeColors(currentScheme);
  const thresholds = getThresholds(varKey);

  map.addLayer({
    id: layerId,
    type: 'circle',
    source: sourceId,
    paint: {
      'circle-radius': buildCircleRadiusExpr(countField),
      'circle-color': buildCircleColorExpr(countField, thresholds, colors),
      'circle-opacity': 0.85,
      'circle-stroke-color': '#1f2d3d',
      'circle-stroke-width': 1.25,
      'circle-stroke-opacity': 0.95,
    },
  });

  pointsLayerActive = { layerId, sourceId, varKey, countField };

  // Hover tooltip on the circles — city + count, no PII.
  bindPointsInteraction(map, layerId);

  // Mute the underlying choropleth now that points are carrying the signal.
  if (currentLevel) applyColorExpression(map, currentLevel);
}

function updatePointsPaint(map) {
  if (!pointsLayerActive) return;
  const { layerId, varKey, countField } = pointsLayerActive;
  if (!map.getLayer(layerId)) return;
  const colors = getSchemeColors(currentScheme);
  const thresholds = getThresholds(varKey);
  map.setPaintProperty(layerId, 'circle-color', buildCircleColorExpr(countField, thresholds, colors));
}

function removePointsLayer(map) {
  if (!pointsLayerActive) return;
  const { layerId, sourceId } = pointsLayerActive;
  if (map.getLayer(layerId)) map.removeLayer(layerId);
  if (map.getSource(sourceId)) map.removeSource(sourceId);
  pointsLayerActive = null;
  // Restore data-driven choropleth fill on the active level.
  if (currentLevel) applyColorExpression(getMap(), currentLevel);
}

export function isPointsModeActive() {
  return !!pointsLayerActive;
}

export async function setLayer(level) {
  if (level === currentLevel) return;
  if (!cachedGeoJson.has(level)) {
    const data = await loadLayer(level);
    preprocessFeatures(data);
    cachedGeoJson.set(level, data);
  }
  const map = getMap();
  if (!map) return;

  const apply = () => {
    ensureSourceAndLayers(map, level, cachedGeoJson.get(level));

    // Register the global shadow layer (idempotent) and pre-warm it so the
    // first click has no shader-compile / FBO-create delay. Keep it strictly
    // below the active level's colored fill so the shadow renders under
    // the polygon body.
    registerShadowLayer(map);
    prewarmShadowLayer(`${level}-fill`);
    if (map.getLayer(SHADOW_LAYER_ID) && map.getLayer(`${level}-fill`)) {
      map.moveLayer(SHADOW_LAYER_ID, `${level}-fill`);
    }

    if (currentLevel && currentLevel !== level) {
      fadeOutLevel(map, currentLevel);
    }

    fadeInLevel(map, level);
    applyColorExpression(map, level);

    clearSelectedLayer();
    setShadowFeature(level, null); // clear any prior selection's shadow
    currentLevel = level;
    refreshReliability();
  };

  if (map.isStyleLoaded()) {
    apply();
  } else {
    map.once('load', apply);
  }
}

// Preload and register all level GeoJSON in the background so layer switches
// are instant (no network wait) after initial load.
export async function preloadAll() {
  const map = getMap();
  for (const level of LEVELS) {
    if (cachedGeoJson.has(level)) continue;
    try {
      const data = await loadLayer(level);
      preprocessFeatures(data);
      cachedGeoJson.set(level, data);
      if (map && map.isStyleLoaded()) {
        ensureSourceAndLayers(map, level, data);
      }
    } catch (e) {
      console.warn(`preloadAll: failed to load ${level}`, e);
    }
  }
}

export function setVariable(varKey) {
  currentVariable = varKey;
  const map = getMap();
  if (!map) return;

  const apply = () => {
    if (!currentLevel) return;
    if (isPointsVariable(varKey)) {
      showPointsLayer(map, varKey);
    } else {
      if (pointsLayerActive) removePointsLayer(map);
      applyColorExpression(map, currentLevel);
    }
    refreshReliability();
  };

  // Initial-load race: setVariable may fire before setLayer's deferred
  // map.once('load', ...) callback runs, leaving currentLevel = null.
  // Defer too so the order ends up: style-loads → setLayer apply →
  // setVariable apply (points-layer added on top of choropleth).
  if (map.isStyleLoaded() && currentLevel) {
    apply();
  } else {
    map.once('load', apply);
  }
}

export function setColorScheme(scheme) {
  currentScheme = scheme;
  const map = getMap();
  if (!map || !currentLevel) return;
  applyColorExpression(map, currentLevel);
  if (pointsLayerActive) updatePointsPaint(map);
}

export function getCurrentVariable() {
  return currentVariable;
}

export function getCurrentScheme() {
  return currentScheme;
}

export function getCurrentLevel() {
  return currentLevel;
}

export function getCachedGeoJson(level) {
  return cachedGeoJson.get(level);
}

export function getFeatureProperties(featureId) {
  if (!currentLevel) return null;
  const data = cachedGeoJson.get(currentLevel);
  if (!data || !data.features) return null;
  const target = String(featureId);
  for (const feat of data.features) {
    const id = String(feat.properties?.GEOID ?? feat.id ?? '');
    if (id === target) return feat.properties;
  }
  return null;
}

export function getFeatureById(level, featureId) {
  const data = cachedGeoJson.get(level);
  if (!data || !data.features) return null;
  const target = String(featureId);
  for (const feat of data.features) {
    const id = String(feat.properties?.GEOID ?? feat.id ?? '');
    if (id === target) return feat;
  }
  return null;
}

export const KNOWN_LEVELS = LEVELS;
