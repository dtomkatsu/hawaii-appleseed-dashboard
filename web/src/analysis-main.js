import { loadConfig, loadLayer } from './data/loader.js';
import { renderChart, renderFullTable } from './analysis/charts.js';

const LAYERS = [
  { key: 'state', label: 'State Boundary' },
  { key: 'county', label: 'Counties' },
  { key: 'house', label: 'House Districts' },
  { key: 'senate', label: 'Senate Districts' },
];

let config = null;
let activeLayer = 'county';
let activeVar = 'poverty_rate';
let initialized = false;

export async function initAnalysis(sharedConfig) {
  if (initialized) return;
  initialized = true;
  config = sharedConfig || await loadConfig();
  buildControls();
  await refreshChart();
}

async function main() {
  config = await loadConfig();
  const params = new URLSearchParams(window.location.search);
  if (params.get('layer')) activeLayer = params.get('layer');
  if (params.get('var')) activeVar = params.get('var');

  buildControls();
  await refreshChart();
}

function buildControls() {
  const root = document.getElementById('da-controls');
  if (!root) return;

  const vars = config.variables?.variables || {};
  const groups = config.variables?.dropdown_groups || {};

  // Layer selector
  const layerSel = document.createElement('select');
  layerSel.className = 'da-select';
  layerSel.innerHTML = LAYERS.map((l) => `<option value="${l.key}" ${l.key === activeLayer ? 'selected' : ''}>${l.label}</option>`).join('');
  layerSel.addEventListener('change', async () => { activeLayer = layerSel.value; await refreshChart(); });

  // Variable selector — grouped optgroups
  const varSel = document.createElement('select');
  varSel.className = 'da-select da-select-wide';
  const byGroup = {};
  for (const [key, v] of Object.entries(vars)) {
    if (!v.show_in_dropdown) continue;
    // Points variables (Millionaires) are town-level markers, not a value per
    // county/district — there is nothing to rank or tabulate by geography, so
    // they'd render an all-empty chart and table. Map-only by design.
    if (v.render_type === 'points') continue;
    if (!byGroup[v.dropdown_group]) byGroup[v.dropdown_group] = [];
    byGroup[v.dropdown_group].push({ key, ...v });
  }
  for (const [grpKey, items] of Object.entries(byGroup)) {
    const label = groups[grpKey]?.label || grpKey;
    const og = document.createElement('optgroup');
    og.label = label;
    items.sort((a, b) => (a.dropdown_order || 999) - (b.dropdown_order || 999));
    for (const v of items) {
      const opt = document.createElement('option');
      opt.value = v.key;
      opt.textContent = v.dropdown_label || v.display_name;
      if (v.key === activeVar) opt.selected = true;
      og.appendChild(opt);
    }
    varSel.appendChild(og);
  }
  varSel.addEventListener('change', async () => { activeVar = varSel.value; await refreshChart(); });

  root.innerHTML = '';
  const layerWrap = document.createElement('label');
  layerWrap.className = 'da-label';
  layerWrap.textContent = 'Geography: ';
  layerWrap.appendChild(layerSel);

  const varWrap = document.createElement('label');
  varWrap.className = 'da-label';
  varWrap.textContent = 'Variable: ';
  varWrap.appendChild(varSel);

  root.appendChild(layerWrap);
  root.appendChild(varWrap);
}

async function refreshChart() {
  const chartEl = document.getElementById('da-chart');
  const tableEl = document.getElementById('da-side-table');
  const fullTableEl = document.getElementById('da-full-table');
  if (chartEl) chartEl.innerHTML = '<p class="da-loading">Loading…</p>';
  if (tableEl) tableEl.innerHTML = '';
  if (fullTableEl) fullTableEl.innerHTML = '';

  try {
    const [geojson, stateGeojson] = await Promise.all([
      loadLayer(activeLayer),
      activeLayer !== 'state' ? loadLayer('state') : Promise.resolve(null),
    ]);

    const varMeta = config.variables?.variables?.[activeVar];
    const layerLabel = LAYERS.find((l) => l.key === activeLayer)?.label || activeLayer;

    if (chartEl) chartEl.innerHTML = '';

    const chartCaption = document.getElementById('da-chart-caption');
    if (chartCaption) chartCaption.remove();

    renderChart(
      'da-chart',
      'da-side-table',
      geojson.features,
      activeVar,
      varMeta,
      layerLabel,
      stateGeojson?.features || null,
    );

    renderFullTable('da-full-table', geojson.features, config.variables, activeLayer);
  } catch (err) {
    console.error('Analysis error:', err);
    if (chartEl) chartEl.innerHTML = `<p style="color:#c0392b;padding:20px">Error: ${err.message}</p>`;
  }
}

// Only auto-run on the standalone data-analysis.html page
if (document.getElementById('da-standalone')) {
  main().catch(console.error);
}
