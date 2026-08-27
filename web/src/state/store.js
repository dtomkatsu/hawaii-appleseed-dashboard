const state = {
  activeLayer: 'county',
  selectedVariable: 'alice_rate',
  colorScheme: 'blue',
  showReliability: false,
  // Millionaires circle overlay — independent of selectedVariable so it can
  // sit on top of any choropleth instead of replacing it. legacyMuted is set
  // only via the old `?var=millionaires` deep link (see urlSync.js) and
  // preserves that link's original muted-choropleth look.
  showMillionaires: false,
  millionairesLegacyMuted: false,
  displayOptions: { showLabels: false, showLegend: true },
  selectedFeatureId: null,
};

const subs = new Set();

export function getState() {
  return state;
}

export function setState(patch) {
  const before = { ...state };
  Object.assign(state, patch);
  const changed = {};
  for (const k of Object.keys(patch)) {
    if (before[k] !== state[k]) changed[k] = state[k];
  }
  if (Object.keys(changed).length === 0) return;
  subs.forEach((fn) => fn(state, changed));
}

export function subscribe(fn) {
  subs.add(fn);
  return () => subs.delete(fn);
}
