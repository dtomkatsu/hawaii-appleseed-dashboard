import { getMap } from './mapInstance.js';
import { getThresholds, getSchemeColors } from './colors.js';
import { loadLayer } from '../data/loader.js';
import { bindLayerInteraction, clearSelectedLayer } from './popup.js';

const LEVELS = ['state', 'county', 'house', 'senate'];
const cachedGeoJson = new Map();
const registeredLevels = new Set();
let currentLevel = null;
let currentVariable = null;
let currentScheme = null;

const FADE_MS = 300;
const pendingHide = new Map(); // level → setTimeout id

// Opacity expressions as constants so fade-in can restore them after zeroing out.
const FILL_OPACITY_EXPR = [
  'case',
  ['boolean', ['feature-state', 'selected'], false], 1.0,
  0.75,
];

// Feature-state gated value: returns `whenSelected` if the feature has selected
// state, else `whenNot` (0). Used for opacity, width, etc.
const selectedCase = (whenSelected, whenNot = 0) => [
  'case',
  ['boolean', ['feature-state', 'selected'], false], whenSelected,
  whenNot,
];

// Shadow stack: 3 fill duplicates of the polygon, each offset progressively
// further down/right with decreasing opacity. Stacked, they integrate into a
// smooth directional drop shadow. Pure fills (not lines) avoid the spike/star
// artifacts that line-translate produces along detailed coastline geometry
// where many small vertices make wide offset lines overshoot at every kink.
// All gated on feature-state 'selected' via opacity.
// Array order = render order (bottom of stack first → ends up below the fill).
const SHADOW_SPECS = [
  { suffix: 'shadow-3', translate: [9, 13], opacity: 0.06 },
  { suffix: 'shadow-2', translate: [5,  7], opacity: 0.14 },
  { suffix: 'shadow-1', translate: [2,  3], opacity: 0.26 },
];

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
    ...SHADOW_SPECS.map((s) => `${level}-${s.suffix}`),
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

  // Soft drop shadow as a stack of offset fill duplicates (see SHADOW_SPECS).
  // Each is the polygon translated down/right with decreasing opacity; the
  // colored fill above covers the inner part so only the offset rim shows,
  // and the stack integrates into a smooth directional shadow.
  for (const spec of SHADOW_SPECS) {
    map.addLayer({
      id: `${level}-${spec.suffix}`,
      type: 'fill',
      source: level,
      layout: { visibility: 'none' },
      paint: {
        'fill-color': '#000000',
        'fill-translate': spec.translate,
        'fill-translate-anchor': 'viewport',
        'fill-opacity': selectedCase(spec.opacity),
        'fill-opacity-transition': { duration: FADE_MS, delay: 0 },
      },
    });
  }

  // Fill — colored by current variable. Selected gets full opacity so the
  // shadow layers below stay hidden under the polygon body.
  map.addLayer({
    id: `${level}-fill`,
    type: 'fill',
    source: level,
    layout: { visibility: 'none' },
    paint: {
      'fill-color': '#cccccc',
      'fill-opacity': FILL_OPACITY_EXPR,
      'fill-opacity-transition': { duration: FADE_MS, delay: 0 },
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
      'line-opacity-transition': { duration: FADE_MS, delay: 0 },
    },
  });

  // Selected: strong inner outline.
  map.addLayer({
    id: `${level}-selected`,
    type: 'line',
    source: level,
    layout: { visibility: 'none' },
    paint: {
      'line-color': '#222222',
      'line-width': [
        'case',
        ['boolean', ['feature-state', 'selected'], false], 2.5,
        0,
      ],
      'line-opacity': 0.9,
      'line-opacity-transition': { duration: FADE_MS, delay: 0 },
    },
  });

  // Hover: thin dark inner ring on hover, suppressed when selected.
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
        ], 2,
        0,
      ],
      'line-opacity': 0.6,
      'line-opacity-transition': { duration: FADE_MS, delay: 0 },
    },
  });

  bindLayerInteraction(map, level);
  registeredLevels.add(level);
}

function restoreTargetOpacities(map, level) {
  for (const spec of SHADOW_SPECS) {
    const id = `${level}-${spec.suffix}`;
    if (!map.getLayer(id)) continue;
    map.setPaintProperty(id, 'fill-opacity', selectedCase(spec.opacity));
  }
  if (map.getLayer(`${level}-fill`))
    map.setPaintProperty(`${level}-fill`, 'fill-opacity', FILL_OPACITY_EXPR);
  if (map.getLayer(`${level}-line`))
    map.setPaintProperty(`${level}-line`, 'line-opacity', 1);
  if (map.getLayer(`${level}-selected`))
    map.setPaintProperty(`${level}-selected`, 'line-opacity', 0.9);
  if (map.getLayer(`${level}-hover`))
    map.setPaintProperty(`${level}-hover`, 'line-opacity', 0.6);
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

    if (currentLevel && currentLevel !== level) {
      fadeOutLevel(map, currentLevel);
    }

    fadeInLevel(map, level);
    applyColorExpression(map, level);

    clearSelectedLayer();
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
