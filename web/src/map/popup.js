import { getState, setState } from '../state/store.js';
import { showInfoPanel } from '../ui/infoPanel.js';

let VARIABLES = null;
let REP_DATA = {};

export function initPopup(variablesConfig, repData) {
  VARIABLES = variablesConfig.variables;
  REP_DATA = repData || {};
}

function cleanName(rawName) {
  let name = rawName || 'Unknown';
  name = name.replace(/[,;]\s*Hawaii/g, '').trim();
  name = name.replace(/\s*\(\d{4}\)\s*/g, '').trim();
  return name;
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

function lookupRep(properties, activeLayer) {
  if (activeLayer !== 'house' && activeLayer !== 'senate') return null;

  let key = null;
  if (properties.house_id) key = `house_${parseInt(properties.house_id, 10)}`;
  else if (properties.senate_id) key = `senate_${parseInt(properties.senate_id, 10)}`;
  else {
    const raw = properties.GEOID || properties.geoid || properties.id;
    if (raw != null) {
      let num;
      const str = String(raw);
      if (str.startsWith('150') && str.length === 5) {
        num = parseInt(str.slice(3), 10);
      } else {
        num = parseInt(str, 10);
      }
      if (!Number.isNaN(num)) key = `${activeLayer}_${num}`;
    }
  }
  if (key && REP_DATA[key]) return REP_DATA[key];
  return null;
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

function buildTooltipContent(properties) {
  const s = getState();
  const name = cleanName(properties.display_name || properties.NAME || properties.name);
  const varKey = s.selectedVariable;
  const meta = VARIABLES?.[varKey];
  const displayName = meta?.display_name_long || meta?.display_name || varKey || '';
  const value = formatValue(properties[varKey], meta?.data_type);

  let html = `<div class="tt-name">${escapeHtml(name)}</div>` +
             `<div class="tt-stat">${escapeHtml(displayName)}: ${escapeHtml(value)}</div>`;

  const rep = lookupRep(properties, s.activeLayer);
  if (rep) {
    let areas = (rep.areas || '').trim();
    if (areas.length > 80) {
      const list = areas.split(', ');
      areas = list.slice(0, 2).join(', ');
      if (list.length > 2) areas += `, +${list.length - 2} more`;
    }
    const repName = `${rep.name} (${rep.party})`;
    html += `<div class="tt-divider"></div>` +
            `<div class="tt-rep">${escapeHtml(repName)}</div>` +
            `<div class="tt-areas">${escapeHtml(areas)}</div>`;
  }

  html += `<div class="tt-hint">Click to explore</div>`;
  return html;
}

export function bindFeature(feature, layer) {
  layer.on({
    mouseover: (e) => {
      e.target.setStyle({ weight: 2.5, color: '#222', fillOpacity: 0.85 });
      e.target.bringToFront();
    },
    mouseout: (e) => {
      e.target.setStyle({ weight: 1, color: '#aaa', fillOpacity: 0.75 });
    },
    click: (e) => {
      const props = e.target.feature.properties;
      const id = props.GEOID || feature.id;
      setState({ selectedFeatureId: id });
      showInfoPanel(props);
    },
  });

  layer.bindTooltip(() => buildTooltipContent(feature.properties), {
    className: 'custom-tooltip',
    direction: 'top',
    offset: [0, -10],
    sticky: true,
  });
}
