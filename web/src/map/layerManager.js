import L from 'leaflet';
import { getMap } from './mapInstance.js';
import { getColorForValue } from './colors.js';
import { loadLayer } from '../data/loader.js';
import { bindFeature, clearSelectedLayer } from './popup.js';

const cachedGeoJson = new Map();
let currentLayer = null;
let currentLevel = null;
let currentVariable = null;
let currentScheme = null;

function styleFor(properties) {
  const value = properties[currentVariable];
  return {
    fillColor: getColorForValue(value, currentVariable, currentScheme),
    weight: 1,
    color: '#aaa',
    fillOpacity: 0.75,
  };
}

export async function setLayer(level) {
  if (level === currentLevel && currentLayer) return;
  if (!cachedGeoJson.has(level)) {
    const data = await loadLayer(level);
    cachedGeoJson.set(level, data);
  }
  const map = getMap();
  if (!map) return;

  if (currentLayer) {
    map.removeLayer(currentLayer);
    currentLayer = null;
  }
  clearSelectedLayer();

  const data = cachedGeoJson.get(level);
  currentLayer = L.geoJSON(data, {
    style: (feature) => styleFor(feature.properties),
    onEachFeature: bindFeature,
  }).addTo(map);

  currentLevel = level;
  // Stay at the user's current view when switching layers — don't auto-fit.
}

export function setVariable(varKey) {
  currentVariable = varKey;
  if (!currentLayer) return;
  currentLayer.eachLayer((l) => {
    if (!l.feature) return;
    l.setStyle({ fillColor: getColorForValue(l.feature.properties[varKey], varKey, currentScheme) });
  });
}

export function setColorScheme(scheme) {
  currentScheme = scheme;
  if (!currentLayer) return;
  currentLayer.eachLayer((l) => {
    if (!l.feature) return;
    l.setStyle({
      fillColor: getColorForValue(l.feature.properties[currentVariable], currentVariable, scheme),
    });
  });
}

export function getCurrentVariable() {
  return currentVariable;
}

export function getCurrentScheme() {
  return currentScheme;
}

export function getFeatureProperties(featureId) {
  if (!currentLayer) return null;
  let result = null;
  currentLayer.eachLayer((l) => {
    if (!l.feature) return;
    const id = l.feature.properties.GEOID || l.feature.id;
    if (id === featureId) result = l.feature.properties;
  });
  return result;
}
