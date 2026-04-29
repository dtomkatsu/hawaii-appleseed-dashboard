import { getSchemeColors, getThresholds, listSchemes } from '../map/colors.js';
import { getState, setState } from '../state/store.js';

let VARIABLES = null;
let schemeBound = false;

export function initLegend(variablesConfig) {
  VARIABLES = variablesConfig.variables;
}

function formatRange(from, next, dataType) {
  const isPct = dataType === 'percentage' || /rate|pct|percent/.test(dataType || '');
  const isCurrency = dataType === 'currency' || /income|value|benefit|amount/.test(dataType || '');
  const isCount = dataType === 'count';

  if (next === undefined) {
    if (isPct) return `${from}%+`;
    if (isCurrency) {
      if (from >= 1_000_000) return `$${(from / 1_000_000).toFixed(1)}M+`;
      if (from >= 1000) return `$${(from / 1000).toFixed(0)}k+`;
      return `$${from.toLocaleString()}+`;
    }
    if (isCount) return `${from.toLocaleString()}+`;
    return `${from}+`;
  }

  if (isPct) return `${from}-${next}%`;
  if (isCurrency) {
    if (from >= 1_000_000)
      return `$${(from / 1_000_000).toFixed(1)}M-${(next / 1_000_000).toFixed(1)}M`;
    if (from >= 1000) return `$${(from / 1000).toFixed(0)}k-${(next / 1000).toFixed(0)}k`;
    return `$${from.toLocaleString()}-${next.toLocaleString()}`;
  }
  if (isCount) return `${from.toLocaleString()}-${next.toLocaleString()}`;
  return `${from}-${next}`;
}

function ensureColorSchemeOptions() {
  const select = document.getElementById('color-scheme-select');
  if (!select) return;
  const s = getState();
  if (!select.options.length) {
    select.innerHTML = listSchemes()
      .map((sk) => `<option value="${sk}">${capitalize(sk)}</option>`)
      .join('');
  }
  if (select.value !== s.colorScheme) {
    select.value = s.colorScheme;
  }
  if (!schemeBound) {
    select.addEventListener('change', (e) => setState({ colorScheme: e.target.value }));
    schemeBound = true;
  }
}

export function renderLegend(varKey, scheme) {
  ensureColorSchemeOptions();

  const titleEl = document.querySelector('#main-map-legend .legend-title');
  const itemsEl = document.getElementById('main-map-legend-items');
  if (!titleEl || !itemsEl) return;

  const meta = VARIABLES?.[varKey];
  const title = meta?.display_name_long || meta?.display_name || varKey;
  titleEl.textContent = title;

  const colors = getSchemeColors(scheme);
  const grades = getThresholds(varKey);
  const dataType = meta?.data_type;

  let html = '';
  for (let i = 0; i < grades.length; i++) {
    const range = formatRange(grades[i], grades[i + 1], dataType);
    const c = colors[Math.min(i, colors.length - 1)];
    html += `<div class="legend-item"><i style="background:${c}"></i><span>${range}</span></div>`;
  }

  const direction = meta?.legend_direction;
  if (direction === 'up') {
    html += '<div class="legend-direction up">↑ Higher is better</div>';
  } else if (direction === 'down') {
    html += '<div class="legend-direction down">↓ Lower is better</div>';
  }

  itemsEl.innerHTML = html;
}

function capitalize(s) {
  return s ? s[0].toUpperCase() + s.slice(1) : s;
}
