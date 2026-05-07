import { getSchemeColors, getThresholds, listSchemes } from '../map/colors.js';
import { getState, setState } from '../state/store.js';

let VARIABLES = null;
let schemeBound = false;

export function initLegend(variablesConfig) {
  VARIABLES = variablesConfig.variables;
}

// Choose enough decimals that EVERY consecutive pair of thresholds renders
// distinctly at the chosen divisor (k or M). E.g. thresholds 8500/8650/8700
// all round to "9k" at 0 decimals — bump to 1 decimal so they read 8.5k/8.7k.
function pickDecimalsForGrades(grades, divisor) {
  for (let d = 0; d <= 2; d++) {
    let ok = true;
    for (let i = 0; i < grades.length - 1; i++) {
      if ((grades[i] / divisor).toFixed(d) === (grades[i + 1] / divisor).toFixed(d)) {
        ok = false;
        break;
      }
    }
    if (ok) return d;
  }
  return 2;
}

function formatRange(from, next, dataType, decimals) {
  const isPct = dataType === 'percentage' || /rate|pct|percent/.test(dataType || '');
  const isCurrency = dataType === 'currency' || /income|value|benefit|amount/.test(dataType || '');
  const isCount = dataType === 'count';

  if (next === undefined) {
    if (isPct) return `${from}%+`;
    if (isCurrency) {
      // 2-decimal k/M reads worse than full numbers — fall back to comma form.
      if (from >= 1_000_000 && decimals < 2) return `$${(from / 1_000_000).toFixed(Math.max(1, decimals))}M+`;
      if (from >= 1000 && decimals < 2) return `$${(from / 1000).toFixed(decimals)}k+`;
      return `$${from.toLocaleString()}+`;
    }
    if (isCount) return `${from.toLocaleString()}+`;
    return `${from}+`;
  }

  if (isPct) return `${from}-${next}%`;
  if (isCurrency) {
    if (from >= 1_000_000 && decimals < 2) {
      const d = Math.max(1, decimals);
      return `$${(from / 1_000_000).toFixed(d)}M-${(next / 1_000_000).toFixed(d)}M`;
    }
    if (from >= 1000 && decimals < 2) {
      return `$${(from / 1000).toFixed(decimals)}k-${(next / 1000).toFixed(decimals)}k`;
    }
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
  const isCurrency = dataType === 'currency' || /income|value|benefit|amount/.test(dataType || '');
  const divisor =
    isCurrency && grades[0] >= 1_000_000 ? 1_000_000 :
    isCurrency && grades[0] >= 1000 ? 1000 : 1;
  const decimals = divisor > 1 ? pickDecimalsForGrades(grades, divisor) : 0;

  let html = '';
  for (let i = 0; i < grades.length; i++) {
    const range = formatRange(grades[i], grades[i + 1], dataType, decimals);
    const c = colors[Math.min(i, colors.length - 1)];
    html += `<div class="legend-item"><i style="background:${c}"></i><span>${range}</span></div>`;
  }

  itemsEl.innerHTML = html;
}

function capitalize(s) {
  return s ? s[0].toUpperCase() + s.slice(1) : s;
}
