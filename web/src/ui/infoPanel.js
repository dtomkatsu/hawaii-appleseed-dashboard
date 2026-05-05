import { getState } from '../state/store.js';
import { lookupRep } from '../map/popup.js';

let VARIABLES = null;
let CATEGORIES = null;
let floatingTip = null;

export function initInfoPanel(variablesConfig) {
  VARIABLES = variablesConfig.variables;
  CATEGORIES = variablesConfig.info_panel_categories;
}

function extractYear(source) {
  if (!source) return '';
  const m = String(source).match(/(19|20)\d{2}/);
  return m ? m[0] : '';
}

function ensureFloatingTip() {
  if (floatingTip) return floatingTip;
  floatingTip = document.createElement('div');
  floatingTip.className = 'ip-floating-tip';
  floatingTip.setAttribute('role', 'tooltip');
  document.body.appendChild(floatingTip);
  return floatingTip;
}

function positionTip(target) {
  const tip = ensureFloatingTip();
  const r = target.getBoundingClientRect();
  tip.classList.remove('below');
  // Measure off-screen without touching visibility/opacity
  const savedPos = tip.style.cssText;
  tip.style.position = 'fixed';
  tip.style.left = '-9999px';
  tip.style.top = '-9999px';
  const tipRect = tip.getBoundingClientRect();
  const wantTop = r.top - tipRect.height - 10;
  const placeBelow = wantTop < 8;
  let left = r.left + r.width / 2 - tipRect.width / 2;
  const margin = 8;
  if (left < margin) left = margin;
  if (left + tipRect.width > window.innerWidth - margin)
    left = window.innerWidth - margin - tipRect.width;
  const top = placeBelow ? r.bottom + 10 : wantTop;
  tip.classList.toggle('below', placeBelow);
  const arrowX = r.left + r.width / 2 - left;
  tip.style.setProperty('--tip-arrow-x', `${arrowX}px`);
  tip.style.left = `${Math.round(left)}px`;
  tip.style.top = `${Math.round(top)}px`;
}

function bindMetricTooltips(panel) {
  const tip = ensureFloatingTip();
  let hideTimer = null;

  const cancelHide = () => { clearTimeout(hideTimer); hideTimer = null; };
  const scheduleHide = () => {
    cancelHide();
    hideTimer = setTimeout(() => tip.classList.remove('visible'), 200);
  };

  const showFor = (el) => {
    cancelHide();
    const desc = el.getAttribute('data-desc') || '';
    const year = el.getAttribute('data-year') || '';
    const label = el.getAttribute('data-label') || '';
    if (!desc && !year) return;
    tip.innerHTML = `
      ${label ? `<div class="ip-tip-title">${label}</div>` : ''}
      ${desc ? `<div class="ip-tip-desc">${desc}</div>` : ''}
      ${year ? `<div class="ip-tip-year"><span class="ip-tip-year-dot"></span>Data Year ${year}</div>` : ''}
    `;
    tip.classList.add('visible');
    positionTip(el);
  };

  panel.querySelectorAll('.ip-metric').forEach((el) => {
    el.addEventListener('mouseenter', () => showFor(el));
    el.addEventListener('mouseleave', scheduleHide);
    el.addEventListener('focus', () => showFor(el));
    el.addEventListener('blur', scheduleHide);
  });
  panel.addEventListener('scroll', () => { cancelHide(); tip.classList.remove('visible'); }, { passive: true });
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
  const factsheetUrl = `${import.meta.env.BASE_URL}factsheet.html?geo_id=${encodeURIComponent(geoid)}&level=${encodeURIComponent(s.activeLayer)}`;

  const selectedVar = VARIABLES?.[s.selectedVariable];
  const selectedDisplayName =
    selectedVar?.info_panel_label || selectedVar?.display_name || (s.selectedVariable || '').replace(/_/g, ' ');
  const selectedValue = formatValue(properties[s.selectedVariable], selectedVar?.data_type);
  const selectedDesc = selectedVar?.description || '';
  const selectedYear = extractYear(selectedVar?.source);

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
      const desc = m.description || '';
      const year = extractYear(m.source);
      const label = m.info_panel_label || m.display_name || '';
      body += `
        <div class="ip-metric ${isSelected ? 'selected' : ''}"
             tabindex="0"
             data-desc="${escapeHtml(desc)}"
             data-year="${escapeHtml(year)}"
             data-label="${escapeHtml(label)}">
          <div class="ip-metric-value">${escapeHtml(displayValue)}</div>
          <div class="ip-metric-label">${escapeHtml(label)}</div>
        </div>`;
    }
    if (items.length % 2 === 1) {
      body += `<div style="visibility: hidden;"></div>`;
    }
    body += '</div></div>';
  }

  const rep = lookupRep(properties, s.activeLayer);
  const repHtml = rep
    ? `<div class="ip-rep">
         <div class="ip-rep-label">Representative</div>
         <div class="ip-rep-name">${escapeHtml(rep.name)} <span class="ip-rep-party">(${escapeHtml(rep.party)})</span></div>
         <div class="ip-rep-areas">${escapeHtml((rep.areas || '').trim())}</div>
       </div>`
    : '';

  panel.innerHTML = `
    <div class="ip-header">
      <button class="ip-close" aria-label="Close">×</button>
      <h2>${escapeHtml(name)}</h2>
    </div>
    <div class="ip-headline"
         tabindex="0"
         data-desc="${escapeHtml(selectedDesc)}"
         data-year="${escapeHtml(selectedYear)}"
         data-label="${escapeHtml(selectedDisplayName)}">
      <div class="ip-headline-band">
        <span class="ip-headline-name">${escapeHtml(selectedDisplayName)}</span>
      </div>
      <div class="ip-headline-body">
        <span class="ip-headline-value">${escapeHtml(selectedValue)}</span>
        ${selectedYear ? `<span class="ip-headline-year">${escapeHtml(selectedYear)}</span>` : ''}
      </div>
    </div>
    ${repHtml}
    <div class="ip-actions">
      <a class="ip-btn" href="${factsheetUrl}" target="_blank" rel="noopener">
        <span>View / Print Fact Sheet</span>
        <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14"/><path d="M13 5l7 7-7 7"/></svg>
      </a>
    </div>
    ${body}
  `;
  panel.classList.add('visible');

  panel.querySelector('.ip-close')?.addEventListener('click', hideInfoPanel);

  // Bind tooltips for headline + each metric
  const headline = panel.querySelector('.ip-headline');
  if (headline) bindHeadlineTooltip(headline);
  bindMetricTooltips(panel);
}

function bindHeadlineTooltip(el) {
  const tip = ensureFloatingTip();
  const showFor = () => {
    const desc = el.getAttribute('data-desc') || '';
    const year = el.getAttribute('data-year') || '';
    const label = el.getAttribute('data-label') || '';
    if (!desc && !year) return;
    tip.innerHTML = `
      ${label ? `<div class="ip-tip-title">${label}</div>` : ''}
      ${desc ? `<div class="ip-tip-desc">${desc}</div>` : ''}
      ${year ? `<div class="ip-tip-year"><span class="ip-tip-year-dot"></span>Data Year ${year}</div>` : ''}
    `;
    tip.classList.add('visible');
    positionTip(el);
  };
  const hide = () => tip.classList.remove('visible');
  el.addEventListener('mouseenter', showFor);
  el.addEventListener('mouseleave', hide);
  el.addEventListener('focus', showFor);
  el.addEventListener('blur', hide);
}

export function hideInfoPanel() {
  const panel = document.getElementById('info-panel');
  if (panel) panel.classList.remove('visible');
  if (floatingTip) floatingTip.classList.remove('visible');
}
