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
const SNAP_KEYS = new Set([
  'snap_household_rate',
  'snap_benefit_annual_per_household',
  'snap_benefits_annual_total',
]);
const CEP_KEYS = new Set(['cep_percentage', 'cep_display']);

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

function buildEconCascadeItems() {
  const items = variablesForGroup('economic_security');
  const main = items.filter((v) => !TAX_CREDIT_KEYS.has(v.key));
  const tax = items.filter((v) => TAX_CREDIT_KEYS.has(v.key));
  const out = main.map((v) => ({ key: v.key, label: v.dropdown_label || v.display_name }));
  if (tax.length) {
    out.push({
      label: 'Tax Credits',
      children: tax.map((v) => ({ key: v.key, label: v.dropdown_label || v.display_name })),
    });
  }
  return out;
}

function buildFoodCascadeItems() {
  const items = variablesForGroup('food_security');
  const snap = items.filter((v) => SNAP_KEYS.has(v.key));
  const cep = items.filter((v) => CEP_KEYS.has(v.key));
  const other = items.filter((v) => !SNAP_KEYS.has(v.key) && !CEP_KEYS.has(v.key));
  const out = other.map((v) => ({ key: v.key, label: v.dropdown_label || v.display_name }));
  if (snap.length) {
    out.push({
      label: 'SNAP',
      children: snap.map((v) => ({ key: v.key, label: v.dropdown_label || v.display_name })),
    });
  }
  if (cep.length) {
    out.push({
      label: 'CEP',
      children: cep.map((v) => ({ key: v.key, label: v.dropdown_label || v.display_name })),
    });
  }
  return out;
}

function buildHousingCascadeItems() {
  const items = variablesForGroup('housing_transportation');
  return items.map((v) => ({ key: v.key, label: v.dropdown_label || v.display_name }));
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

function renderCascade(rootKey, items, currentKey, placeholder) {
  const currentLabel = currentKey ? findLabelByKey(items, currentKey) : null;
  const triggerText = currentLabel || placeholder;
  const isSelected = !!currentLabel;

  function renderItems(list) {
    return list
      .map((it) => {
        if (it.children) {
          return `
            <li class="cascade-parent">
              <div class="cascade-label">${escapeHtml(it.label)}<span class="cascade-caret">▸</span></div>
              <ul class="cascade-menu">${renderItems(it.children)}</ul>
            </li>`;
        }
        const sel = it.key === currentKey ? 'cascade-leaf--selected' : '';
        return `<li class="cascade-leaf ${sel}"><a href="#" data-cascade-key="${escapeHtml(it.key)}">${escapeHtml(it.label)}</a></li>`;
      })
      .join('');
  }

  return `
    <div class="cascade-root" data-cascade-root="${rootKey}">
      <div class="cascade-trigger">
        <span class="cascade-current ${isSelected ? 'is-selected' : 'is-placeholder'}">${escapeHtml(triggerText)}</span>
        <span class="cascade-trigger-caret">▾</span>
      </div>
      <ul class="cascade-menu">${renderItems(items)}</ul>
    </div>`;
}

function renderColumn(rootKey, tag, tagStyle, items, currentKey, placeholder, showHeader) {
  const headerVisibility = showHeader ? '' : 'visibility: hidden;';
  const headerBorder = showHeader ? 'border-bottom: 2px solid #c8e6b0;' : 'border-bottom: 2px solid transparent;';
  return `
    <div class="ctrl-col">
      <div class="ctrl-header" style="${headerVisibility} ${headerBorder}">Choose your variable</div>
      <div class="ctrl-tag-wrap"><span class="ctrl-tag ${tagStyle}">${escapeHtml(tag)}</span></div>
      ${renderCascade(rootKey, items, currentKey, placeholder)}
    </div>`;
}

export function renderSidebar() {
  const root = document.getElementById('controls-bar');
  if (!root) return;
  const s = getState();

  const geoItems = buildGeographyCascadeItems();
  const econItems = buildEconCascadeItems();
  const foodItems = buildFoodCascadeItems();
  const housingItems = buildHousingCascadeItems();

  const layerKey = `layer:${s.activeLayer}`;
  const variableKey = s.selectedVariable;

  const geoCol = renderColumn(
    'geography',
    'Geography',
    'tag-solid',
    geoItems,
    layerKey,
    'Select Geography',
    false,
  );
  const econCol = renderColumn(
    'economic_security',
    GROUPS?.economic_security?.label || 'Economic Security',
    'tag-outline',
    econItems,
    variableKey,
    'Select Variable',
    true,
  );
  const foodCol = renderColumn(
    'food_security',
    GROUPS?.food_security?.label || 'Food Security',
    'tag-outline',
    foodItems,
    variableKey,
    'Select Variable',
    false,
  );
  const housingCol = renderColumn(
    'housing_transportation',
    GROUPS?.housing_transportation?.label || 'Housing & Transportation',
    'tag-outline',
    housingItems,
    variableKey,
    'Select Variable',
    false,
  );

  root.innerHTML = geoCol + econCol + foodCol + housingCol;

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
}

export function reflectSidebar() {
  renderSidebar();
}
