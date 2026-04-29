import { getState } from '../state/store.js';

let VARIABLES = null;
let CATEGORIES = null;

export function initInfoPanel(variablesConfig) {
  VARIABLES = variablesConfig.variables;
  CATEGORIES = variablesConfig.info_panel_categories;
}

function formatValue(value, dataType) {
  if (value === undefined || value === null || value === '') return 'N/A';
  if (dataType === 'text') return String(value);
  const num = parseFloat(value);
  if (isNaN(num)) return String(value);
  if (
    dataType === 'percentage' ||
    /rate|pct|percent/.test(dataType || '')
  )
    return num.toFixed(1) + '%';
  if (dataType === 'currency' || /income|value|benefit|amount/.test(dataType || ''))
    return '$' + Math.round(num).toLocaleString();
  if (dataType === 'minutes') return num.toFixed(1) + ' min';
  if (dataType === 'count') return num.toLocaleString();
  return num.toLocaleString();
}

function variablesByCategory() {
  const map = {};
  for (const [key, v] of Object.entries(VARIABLES || {})) {
    if (!v.show_in_info_panel) continue;
    const cat = v.info_panel_category;
    if (!cat) continue;
    if (!map[cat]) map[cat] = [];
    map[cat].push({ key, ...v });
  }
  for (const cat of Object.keys(map)) {
    map[cat].sort((a, b) => (a.info_panel_order || 999) - (b.info_panel_order || 999));
  }
  return map;
}

export function showInfoPanel(properties) {
  const panel = document.getElementById('info-panel');
  if (!panel) return;

  const s = getState();
  const geoid = properties.GEOID || properties.geoid || '';
  const name = properties.NAME || properties.name || `Geography ${geoid}`;
  const factsheetUrl = `/factsheet.html?geo_id=${encodeURIComponent(geoid)}&level=${encodeURIComponent(s.activeLayer)}`;

  const grouped = variablesByCategory();
  const cats = Object.entries(CATEGORIES || {})
    .sort((a, b) => (a[1].order || 0) - (b[1].order || 0))
    .map(([k]) => k);

  let body = '';
  for (const cat of cats) {
    const items = (grouped[cat] || []).filter(
      (m) => properties[m.key] !== undefined && properties[m.key] !== null,
    );
    if (!items.length) continue;
    body += `<div class="ip-category"><h4>${cat}</h4><div class="ip-metrics">`;
    for (const m of items) {
      const isSelected = m.key === s.selectedVariable;
      body += `
        <div class="ip-metric ${isSelected ? 'selected' : ''}">
          <div class="ip-metric-value">${formatValue(properties[m.key], m.data_type)}</div>
          <div class="ip-metric-label">${m.info_panel_label || m.display_name}</div>
        </div>`;
    }
    body += '</div></div>';
  }

  panel.innerHTML = `
    <div class="ip-header">
      <button class="ip-close" aria-label="Close">×</button>
      <h2>${name}</h2>
    </div>
    ${body}
    <div class="ip-actions">
      <a class="ip-btn" href="${factsheetUrl}" target="_blank" rel="noopener">View / Print Fact Sheet</a>
    </div>
  `;
  panel.classList.add('visible');

  panel.querySelector('.ip-close')?.addEventListener('click', hideInfoPanel);
}

export function hideInfoPanel() {
  const panel = document.getElementById('info-panel');
  if (panel) panel.classList.remove('visible');
}
