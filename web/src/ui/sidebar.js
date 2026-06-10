import { getState, setState } from '../state/store.js';

const LAYERS = [
  { key: 'state', label: 'State Boundary' },
  { key: 'county', label: 'Counties' },
  { key: 'house', label: 'House Districts' },
  { key: 'senate', label: 'Senate Districts' },
];

const TAX_CREDIT_KEYS = new Set([
  'ctc_avg_amount',
  'ctc_participation_rate',
  'federal_eitc_avg_amount',
  'eitc_participation_rate',
  'state_eitc_avg_amount',
]);
const EDUCATION_KEYS = new Set([
  'high_school_or_higher_pct',
  'college_educated_pct',
]);
const RACE_ETHNICITY_KEYS = new Set([
  'nhpi_pct',
  'asian_pct',
  'white_pct',
  'black_pct',
  'hispanic_pct',
]);
const SNAP_KEYS = new Set([
  'snap_household_rate',
  'snap_benefit_annual_per_household',
  'snap_benefits_annual_total',
]);
const CEP_KEYS = new Set(['cep_percentage', 'cep_display']);
const TRANSPORTATION_KEYS = new Set([
  'travel_time_to_work_minutes',
  'public_transportation_pct',
  'avg_vehicles_per_household',
  'zero_vehicle_household_pct',
  'vehicles_per_capita',
]);

const GROUP_DESCRIPTIONS = {
  'Tax Credits': 'Refundable tax credits — like the **Child Tax Credit** and **Earned Income Tax Credit** — that put money back in **working families’** pockets at tax time.',
  'Educational Attainment': 'The **highest level of school or degree** completed by adult residents.',
  'Race & Ethnicity': 'Self-reported race and Hispanic origin from the Census. Race uses **alone or in combination**, so multi-racial residents are counted in every group they identify with — categories overlap and don’t sum to 100%.',
  'SNAP': 'Supplemental Nutrition Assistance Program — **federal food benefits** (formerly food stamps) that help **low-income households** afford groceries.',
  'CEP': 'Community Eligibility Provision — lets schools in high-poverty areas serve **free breakfast and lunch** to **every student** without individual applications.',
  'Housing': 'Cost, ownership, **affordability**, and availability of housing.',
  'Transportation': 'How long, and by what means, residents **commute to work**.',
};

let VARIABLES = null;
let GROUPS = null;

export function initSidebar(variablesConfig) {
  VARIABLES = variablesConfig.variables;
  GROUPS = variablesConfig.dropdown_groups;
}

function variablesForGroup(groupKey) {
  const items = [];
  for (const [key, v] of Object.entries(VARIABLES || {})) {
    if (!v.show_in_dropdown) continue;
    if (v.dropdown_group !== groupKey) continue;
    items.push({ key, ...v });
  }
  items.sort((a, b) => (a.dropdown_order || 999) - (b.dropdown_order || 999));
  return items;
}

function extractYear(source) {
  if (!source) return '';
  const m = String(source).match(/(19|20)\d{2}/);
  return m ? m[0] : '';
}

function leaf(v) {
  return {
    key: v.key,
    label: v.dropdown_label || v.display_name,
    tooltip: v.description || '',
    year: extractYear(v.source),
    category: v.info_panel_category || null,
  };
}

function buildEconCascadeItems() {
  const items = variablesForGroup('economic_security');
  const main = items.filter((v) =>
    !TAX_CREDIT_KEYS.has(v.key) &&
    !EDUCATION_KEYS.has(v.key) &&
    !RACE_ETHNICITY_KEYS.has(v.key));
  const tax = items.filter((v) => TAX_CREDIT_KEYS.has(v.key));
  const edu = items.filter((v) => EDUCATION_KEYS.has(v.key));
  const race = items.filter((v) => RACE_ETHNICITY_KEYS.has(v.key));
  const out = main.map(leaf);
  if (tax.length) {
    out.push({ label: 'Tax Credits', tooltip: GROUP_DESCRIPTIONS['Tax Credits'], children: tax.map(leaf) });
  }
  if (edu.length) {
    out.push({ label: 'Educational Attainment', tooltip: GROUP_DESCRIPTIONS['Educational Attainment'], children: edu.map(leaf) });
  }
  if (race.length) {
    out.push({ label: 'Race & Ethnicity', tooltip: GROUP_DESCRIPTIONS['Race & Ethnicity'], children: race.map(leaf) });
  }
  return out;
}

function buildFoodCascadeItems() {
  const items = variablesForGroup('food_security');
  const snap = items.filter((v) => SNAP_KEYS.has(v.key));
  const cep = items.filter((v) => CEP_KEYS.has(v.key));
  const other = items.filter((v) => !SNAP_KEYS.has(v.key) && !CEP_KEYS.has(v.key));
  const out = other.map(leaf);
  if (snap.length) {
    out.push({ label: 'SNAP', tooltip: GROUP_DESCRIPTIONS['SNAP'], children: snap.map(leaf) });
  }
  if (cep.length) {
    out.push({ label: 'CEP', tooltip: GROUP_DESCRIPTIONS['CEP'], children: cep.map(leaf) });
  }
  return out;
}

function buildHousingCascadeItems() {
  const items = variablesForGroup('housing_transportation');
  const housing = items.filter((v) => !TRANSPORTATION_KEYS.has(v.key));
  const transport = items.filter((v) => TRANSPORTATION_KEYS.has(v.key));
  const out = [];
  if (housing.length) {
    out.push({ label: 'Housing', tooltip: GROUP_DESCRIPTIONS['Housing'], children: housing.map(leaf) });
  }
  if (transport.length) {
    out.push({ label: 'Transportation', tooltip: GROUP_DESCRIPTIONS['Transportation'], children: transport.map(leaf) });
  }
  return out;
}

function buildHealthCascadeItems() {
  return variablesForGroup('health').map(leaf);
}

function buildGeographyCascadeItems() {
  return LAYERS.map((l) => ({ key: `layer:${l.key}`, label: l.label }));
}

function findLabelByKey(items, targetKey) {
  for (const it of items) {
    if (it.children) {
      const sub = findLabelByKey(it.children, targetKey);
      if (sub) return sub;
    } else if (it.key === targetKey) {
      return it.label;
    }
  }
  return null;
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

function tipAttrs(tip, pos, year) {
  if (!tip) return '';
  const parts = [`data-tip="${escapeHtml(tip)}"`];
  if (pos) parts.push(`data-tip-pos="${escapeHtml(pos)}"`);
  if (year) parts.push(`data-tip-year="${escapeHtml(year)}"`);
  return ' ' + parts.join(' ');
}

function renderCascade(rootKey, items, currentKey, placeholder) {
  const currentLabel = currentKey ? findLabelByKey(items, currentKey) : null;
  const triggerText = currentLabel || placeholder;
  const isSelected = !!currentLabel;

  function renderItems(list) {
    return list
      .map((it) => {
        if (it.children) {
          // Tooltip lives on the text span only — hovering the caret or
          // empty row area shouldn't fire it. Position "above" so it
          // doesn't cover the submenu that opens to the right on hover.
          return `
            <li class="cascade-parent">
              <div class="cascade-label"><span class="cascade-label-text"${tipAttrs(it.tooltip, 'above')}>${escapeHtml(it.label)}</span><span class="cascade-caret" aria-hidden="true">›</span></div>
              <ul class="cascade-menu">${renderItems(it.children)}</ul>
            </li>`;
        }
        const sel = it.key === currentKey ? 'cascade-leaf--selected' : '';
        return `<li class="cascade-leaf ${sel}"><a href="#" data-cascade-key="${escapeHtml(it.key)}"><span class="cascade-leaf-text"${tipAttrs(it.tooltip, 'right', it.year)}>${escapeHtml(it.label)}</span></a></li>`;
      })
      .join('');
  }

  return `
    <div class="cascade-root" data-cascade-root="${rootKey}">
      <div class="cascade-trigger">
        <span class="cascade-current ${isSelected ? 'is-selected' : 'is-placeholder'}">${escapeHtml(triggerText)}</span>
        <span class="cascade-trigger-caret" aria-hidden="true"><svg viewBox="0 0 12 8" width="11" height="8" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M1 1.5l5 5 5-5"/></svg></span>
      </div>
      <ul class="cascade-menu">${renderItems(items)}</ul>
    </div>`;
}

function renderColumn(rootKey, tag, tagStyle, items, currentKey, placeholder) {
  // Filled pill = this column owns the current selection; outline = idle.
  // (The passed tagStyle is a fallback; the live selection state wins.)
  const owns = !!findLabelByKey(items, currentKey);
  const stateStyle = owns ? 'tag-solid' : (tagStyle === 'tag-solid' ? 'tag-solid' : 'tag-outline');
  return `
    <div class="ctrl-col">
      <div class="ctrl-tag-wrap"><span class="ctrl-tag ${stateStyle}">${escapeHtml(tag)}</span></div>
      ${renderCascade(rootKey, items, currentKey, placeholder)}
    </div>`;
}

let TOOLTIP_EL = null;
let TOOLTIP_TIMER = null;

function ensureTooltipEl() {
  if (TOOLTIP_EL) return TOOLTIP_EL;
  const el = document.createElement('div');
  el.className = 'cascade-tooltip';
  el.setAttribute('role', 'tooltip');
  el.style.opacity = '0';
  document.body.appendChild(el);
  TOOLTIP_EL = el;
  return el;
}

// Process tooltip body text:
//   1. **phrase** is converted to <mark>phrase</mark> (manual highlight markup)
//   2. percentages and dollar amounts outside of marked phrases are auto-highlighted
// Input is HTML-escaped per segment so no user content is injected as raw HTML.
function highlightNumbers(escaped) {
  return escaped
    .replace(/(\$[\d,]+(?:\.\d+)?)/g, '<mark>$1</mark>')
    .replace(/(\d+(?:\.\d+)?%)/g, '<mark>$1</mark>');
}

function buildTooltipBody(text) {
  const re = /\*\*([^*]+)\*\*/g;
  let lastIdx = 0;
  let result = '';
  let match;
  while ((match = re.exec(text)) !== null) {
    const before = text.slice(lastIdx, match.index);
    result += highlightNumbers(escapeHtml(before));
    result += `<mark>${escapeHtml(match[1])}</mark>`;
    lastIdx = match.index + match[0].length;
  }
  result += highlightNumbers(escapeHtml(text.slice(lastIdx)));
  return result;
}

function renderTooltipContent(text, year) {
  const yearBadge = year
    ? `<div class="cascade-tooltip-year"><span class="cascade-tooltip-year-dot"></span>Data Year ${escapeHtml(year)}</div>`
    : '';
  return `<div class="cascade-tooltip-text">${buildTooltipBody(text)}</div>${yearBadge}`;
}

function positionTooltip(target, pos) {
  const el = TOOLTIP_EL;
  if (!el) return;
  const r = target.getBoundingClientRect();
  const margin = 10;
  el.style.maxWidth = '260px';
  el.style.left = '0';
  el.style.top = '0';
  // Force layout to measure size
  const tw = el.offsetWidth;
  const th = el.offsetHeight;

  if (pos === 'above') {
    // Center horizontally on the text, place above; flip below if no room.
    let left = r.left + (r.width - tw) / 2;
    left = Math.max(8, Math.min(left, window.innerWidth - tw - 8));
    let top = r.top - margin - th;
    if (top < 8) top = r.bottom + margin;
    el.style.left = `${Math.round(left)}px`;
    el.style.top = `${Math.round(top)}px`;
    return;
  }

  // Default: prefer to the right of the item; fall back to left if it would overflow.
  let left = r.right + margin;
  if (left + tw > window.innerWidth - 8) {
    left = Math.max(8, r.left - margin - tw);
  }
  let top = r.top + (r.height - th) / 2;
  top = Math.max(8, Math.min(top, window.innerHeight - th - 8));
  el.style.left = `${Math.round(left)}px`;
  el.style.top = `${Math.round(top)}px`;
}

function showTooltip(target, text, pos, year) {
  const el = ensureTooltipEl();
  el.innerHTML = renderTooltipContent(text, year);
  el.style.opacity = '0';
  el.style.display = 'block';
  // Delay so it doesn't fire on quick passes.
  clearTimeout(TOOLTIP_TIMER);
  TOOLTIP_TIMER = setTimeout(() => {
    positionTooltip(target, pos);
    el.style.opacity = '1';
  }, 220);
}

function hideTooltip() {
  clearTimeout(TOOLTIP_TIMER);
  if (!TOOLTIP_EL) return;
  TOOLTIP_EL.style.opacity = '0';
}

function attachTooltipListeners(root) {
  const tipped = root.querySelectorAll('[data-tip]');
  tipped.forEach((node) => {
    const pos = node.dataset.tipPos;
    const year = node.dataset.tipYear;
    node.addEventListener('mouseenter', () => showTooltip(node, node.dataset.tip, pos, year));
    node.addEventListener('mouseleave', hideTooltip);
    node.addEventListener('focus', () => showTooltip(node, node.dataset.tip, pos, year));
    node.addEventListener('blur', hideTooltip);
  });
}

export function renderSidebar() {
  const root = document.getElementById('controls-bar');
  if (!root) return;
  const s = getState();

  const geoItems = buildGeographyCascadeItems();
  const econItems = buildEconCascadeItems();
  const foodItems = buildFoodCascadeItems();
  const housingItems = buildHousingCascadeItems();
  const healthItems = buildHealthCascadeItems();

  const layerKey = `layer:${s.activeLayer}`;
  const variableKey = s.selectedVariable;

  const geoCol = renderColumn(
    'geography',
    'Geography',
    'tag-solid',
    geoItems,
    layerKey,
    'Select Geography',
    );
  const econCol = renderColumn(
    'economic_security',
    GROUPS?.economic_security?.label || 'Economic Security',
    'tag-outline',
    econItems,
    variableKey,
    'Select Variable',
    );
  const foodCol = renderColumn(
    'food_security',
    GROUPS?.food_security?.label || 'Food Security',
    'tag-outline',
    foodItems,
    variableKey,
    'Select Variable',
    );
  const housingCol = renderColumn(
    'housing_transportation',
    GROUPS?.housing_transportation?.label || 'Housing & Transportation',
    'tag-outline',
    housingItems,
    variableKey,
    'Select Variable',
    );
  const healthCol = renderColumn(
    'health',
    GROUPS?.health?.label || 'Health',
    'tag-outline',
    healthItems,
    variableKey,
    'Select Variable',
    );

  root.innerHTML = geoCol + econCol + foodCol + housingCol + healthCol;

  root.querySelectorAll('a[data-cascade-key]').forEach((a) => {
    a.addEventListener('click', (e) => {
      e.preventDefault();
      const key = a.dataset.cascadeKey;
      if (key.startsWith('layer:')) {
        setState({ activeLayer: key.slice('layer:'.length) });
      } else {
        setState({ selectedVariable: key });
      }
    });
  });

  attachTooltipListeners(root);
}

export function reflectSidebar() {
  renderSidebar();
}
