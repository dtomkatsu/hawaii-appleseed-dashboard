import L from 'leaflet';
import { getState, setState } from '../state/store.js';
import { showInfoPanel } from '../ui/infoPanel.js';

let VARIABLES = null;
let REP_DATA = {};
let selectedLayer = null;

const SmartTooltip = L.Tooltip.extend({
  _updatePosition() {
    if (this._map && this._container) {
      const map = this._map;
      const latlng = this._latlng || (this._source && this._source.getCenter && this._source.getCenter());
      if (latlng) {
        const layerPoint = map.latLngToLayerPoint(latlng);
        const containerPoint = map.layerPointToContainerPoint(layerPoint);
        const tooltipHeight = this._container.offsetHeight || 100;
        const tooltipWidth = this._container.offsetWidth || 200;
        const mapSize = map.getSize();
        const margin = 10;

        let dir = 'top';
        if (containerPoint.y - tooltipHeight - margin < 0) dir = 'bottom';
        if (dir === 'top' && containerPoint.y + margin > mapSize.y) dir = 'bottom';

        if (containerPoint.x - tooltipWidth / 2 < margin) dir = 'right';
        else if (containerPoint.x + tooltipWidth / 2 > mapSize.x - margin) dir = 'left';

        this.options.direction = dir;
        this.options.offset = L.point(
          dir === 'left' ? -10 : dir === 'right' ? 10 : 0,
          dir === 'top' ? -10 : dir === 'bottom' ? 10 : 0
        );
      }
    }
    L.Tooltip.prototype._updatePosition.call(this);
  },
});

export function initPopup(variablesConfig, repData) {
  VARIABLES = variablesConfig.variables;
  REP_DATA = repData || {};
}

export function clearSelectedLayer() {
  selectedLayer = null;
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

export function lookupRep(properties, activeLayer) {
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
             `<div class="tt-stat-card">` +
             `<div class="tt-stat-label">${escapeHtml(displayName)}</div>` +
             `<div class="tt-stat-value">${escapeHtml(value)}</div>` +
             `</div>`;

  const rep = lookupRep(properties, s.activeLayer);
  if (rep) {
    let areas = (rep.areas || '').trim();
    if (areas.length > 80) {
      const list = areas.split(', ');
      areas = list.slice(0, 2).join(', ');
      if (list.length > 2) areas += `, +${list.length - 2} more`;
    }
    html += `<div class="tt-rep-card">` +
            `<div class="tt-rep-label">Representative</div>` +
            `<div class="tt-rep-name">${escapeHtml(rep.name)} <span class="tt-rep-party">${escapeHtml(rep.party)}</span></div>` +
            `<div class="tt-areas">${escapeHtml(areas)}</div>` +
            `</div>`;
  }

  html += `<div class="tt-hint">Click to explore →</div>`;
  return html;
}

export function bindFeature(feature, layer) {
  layer.on({
    mouseover: (e) => {
      e.target.setStyle({ weight: 2.5, color: '#222', fillOpacity: 0.85 });
      e.target.bringToFront();
    },
    mouseout: (e) => {
      if (e.target === selectedLayer) return;
      e.target.setStyle({ weight: 1, color: '#aaa', fillOpacity: 0.75 });
    },
    click: (e) => {
      if (selectedLayer && selectedLayer !== e.target) {
        selectedLayer.setStyle({ weight: 1, color: '#aaa', fillOpacity: 0.75 });
      }
      selectedLayer = e.target;
      const props = e.target.feature.properties;
      const id = props.GEOID || feature.id;
      setState({ selectedFeatureId: id });
      showInfoPanel(props);
      try {
        const bounds = e.target.getBounds();
        if (bounds && bounds.isValid()) {
          const panel = document.getElementById('info-panel');
          const panelOpen = panel && panel.classList.contains('visible');
          const rightPad = panelOpen ? (panel.getBoundingClientRect().width || 360) + 40 : 40;
          e.target._map.flyToBounds(bounds, {
            paddingTopLeft: [40, 40],
            paddingBottomRight: [rightPad, 40],
            duration: 0.6,
            maxZoom: 10,
          });
        }
      } catch (_) {
        /* no-op */
      }
    },
  });

  const tooltip = new SmartTooltip({
    className: 'custom-tooltip',
    direction: 'top',
    offset: [0, -10],
    sticky: true,
  });
  tooltip.setContent(() => buildTooltipContent(feature.properties));
  layer.bindTooltip(tooltip);
}
