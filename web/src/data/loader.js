const cache = new Map();

export async function fetchJson(path) {
  if (cache.has(path)) return cache.get(path);
  const promise = fetch(path).then((r) => {
    if (!r.ok) throw new Error(`Failed to fetch ${path}: ${r.status}`);
    return r.json();
  });
  cache.set(path, promise);
  return promise;
}

export function loadConfig() {
  return Promise.all([
    fetchJson('/src/config/variables.json'),
    fetchJson('/src/config/theme.json'),
    fetchJson('/src/config/ui_strings.json'),
  ]).then(([variables, theme, uiStrings]) => ({ variables, theme, uiStrings }));
}

export function loadLayer(level) {
  return fetchJson(`/data/${level}.geojson`);
}

export function loadStateSummary() {
  return fetchJson('/data/state_summary.json');
}

export function loadRepData() {
  return fetchJson('/data/rep_data.json').catch(() => ({}));
}
