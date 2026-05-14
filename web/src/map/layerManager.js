import { getMap } from './mapInstance.js';
import { getThresholds, getSchemeColors } from './colors.js';
import { loadLayer } from '../data/loader.js';
import { bindLayerInteraction, clearSelectedLayer } from './popup.js';
import { registerShadowLayer, prewarmShadowLayer, setShadowFeature, SHADOW_LAYER_ID } from './shadowLayer.js';
import { FLAGS } from './perfFlags.js';

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
  const expr = colorExpression(currentVariable, currentScheme);
  map.setPaintProperty(`${level}-fill`, 'fill-color', expr);
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
  if (!map || !currentLevel) return;
  applyColorExpression(map, currentLevel);
}

export function setColorScheme(scheme) {
  currentScheme = scheme;
  const map = getMap();
  if (!map || !currentLevel) return;
  applyColorExpression(map, currentLevel);
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
