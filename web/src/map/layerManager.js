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
    `${level}-selected-halo`,
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

  // Fill — colored by current variable. Slight extra opacity boost when selected.
  map.addLayer({
    id: `${level}-fill`,
    type: 'fill',
    source: level,
    layout: { visibility: 'none' },
    paint: {
      'fill-color': '#cccccc',
      'fill-opacity': [
        'case',
        ['boolean', ['feature-state', 'selected'], false], 1.0,
        0.75,
      ],
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
    },
  });

  // Selected halo: a wide, soft outline below the strong outline. Feature-state driven.
  map.addLayer({
    id: `${level}-selected-halo`,
    type: 'line',
    source: level,
    layout: { visibility: 'none' },
    paint: {
      'line-color': '#000000',
      'line-blur': 6,
      'line-width': [
        'case',
        ['boolean', ['feature-state', 'selected'], false], 12,
        0,
      ],
      'line-opacity': [
        'case',
        ['boolean', ['feature-state', 'selected'], false], 0.22,
        0,
      ],
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
    },
  });

  bindLayerInteraction(map, level);
  registeredLevels.add(level);
}

function setLevelVisibility(map, level, visible) {
  const ids = fillLayerIds(level);
  for (const id of ids) {
    if (map.getLayer(id)) {
      map.setLayoutProperty(id, 'visibility', visible ? 'visible' : 'none');
    }
  }
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

    // Hide previous level
    if (currentLevel && currentLevel !== level) {
      setLevelVisibility(map, currentLevel, false);
    }

    setLevelVisibility(map, level, true);
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
