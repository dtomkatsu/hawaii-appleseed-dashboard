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
  if (dataType === 'percentage' || /rate|pct|percent/.test(dataType || '')) {
    return num.toFixed(1) + '%';
  }
  if (dataType === 'currency' || /income|value|benefit|amount/.test(dataType || '')) {
    return '$' + Math.round(num).toLocaleString();
  }
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

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

function cleanName(rawName) {
  let name = rawName || 'Unknown';
  name = name.replace(/[,;]\s*Hawaii/g, '').trim();
  name = name.replace(/\s*\(\d{4}\)\s*/g, '').trim();
  return name;
}

export function showInfoPanel(properties) {
  const panel = document.getElementById('info-panel');
  if (!panel) return;

  const s = getState();
  const geoid = properties.GEOID || properties.geoid || '';
  const name = cleanName(properties.display_name || properties.NAME || properties.name || `Geography ${geoid}`);
  const factsheetUrl = `/factsheet.html?geo_id=${encodeURIComponent(geoid)}&level=${encodeURIComponent(s.activeLayer)}`;

  const selectedVar = VARIABLES?.[s.selectedVariable];
  const selectedDisplayName =
    selectedVar?.info_panel_label || selectedVar?.display_name || (s.selectedVariable || '').replace(/_/g, ' ');
  const selectedValue = formatValue(properties[s.selectedVariable], selectedVar?.data_type);

  const grouped = variablesByCategory();
  const cats = Object.entries(CATEGORIES || {})
    .sort((a, b) => (a[1].order || 0) - (b[1].order || 0))
    .map(([k]) => k);

  let body = '';
  for (const cat of cats) {
    const items = (grouped[cat] || []).filter((m) => properties[m.key] !== undefined && properties[m.key] !== null);
    if (!items.length) continue;
    body += `<div class="ip-category"><h4>${escapeHtml(cat)}</h4><div class="ip-metrics">`;
    for (const m of items) {
      const isSelected = m.key === s.selectedVariable;
      let displayValue = formatValue(properties[m.key], m.data_type);
      if (m.key === 'cep_display') {
        displayValue = String(properties[m.key]).replace(/\s*CEP\s*schools?/i, '').trim();
      }
      body += `
        <div class="ip-metric ${isSelected ? 'selected' : ''}">
          <div class="ip-metric-value">${escapeHtml(displayValue)}</div>
          <div class="ip-metric-label">${escapeHtml(m.info_panel_label || m.display_name)}</div>
        </div>`;
    }
    if (items.length % 2 === 1) {
      body += `<div style="visibility: hidden;"></div>`;
    }
    body += '</div></div>';
  }

  panel.innerHTML = `
    <div class="ip-header">
      <button class="ip-close" aria-label="Close">×</button>
      <h2>${escapeHtml(name)}</h2>
    </div>
    <div class="ip-headline">
      <div class="ip-headline-band"><span>${escapeHtml(selectedDisplayName)}</span></div>
      <div class="ip-headline-body"><span>${escapeHtml(selectedValue)}</span></div>
    </div>
    <div class="ip-actions">
      <a class="ip-btn" href="${factsheetUrl}" target="_blank" rel="noopener">View / Print Fact Sheet</a>
    </div>
    ${body}
  `;
  panel.classList.add('visible');

  panel.querySelector('.ip-close')?.addEventListener('click', hideInfoPanel);
}

export function hideInfoPanel() {
  const panel = document.getElementById('info-panel');
  if (panel) panel.classList.remove('visible');
}
