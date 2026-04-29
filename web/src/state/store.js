const state = {
  activeLayer: 'county',
  selectedVariable: 'poverty_rate',
  colorScheme: 'blue',
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
