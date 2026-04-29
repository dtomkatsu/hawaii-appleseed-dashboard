import { getState, setState } from '../state/store.js';
import { listSchemes } from '../map/colors.js';

const LAYERS = [
  { key: 'state', label: 'State' },
  { key: 'county', label: 'Counties' },
  { key: 'house', label: 'House Districts' },
  { key: 'senate', label: 'Senate Districts' },
];

let VARIABLES = null;
let GROUPS = null;

export function initSidebar(variablesConfig) {
  VARIABLES = variablesConfig.variables;
  GROUPS = variablesConfig.dropdown_groups;
}

export function renderSidebar() {
  const root = document.getElementById('sidebar');
  if (!root) return;
  const s = getState();

  const layerHtml = `
    <section class="sb-section">
      <h3>Geography</h3>
      <div class="layer-buttons">
        ${LAYERS.map(
          (l) =>
            `<button class="layer-btn ${s.activeLayer === l.key ? 'active' : ''}" data-layer="${l.key}">${l.label}</button>`,
        ).join('')}
      </div>
    </section>`;

  const groupOrder = Object.entries(GROUPS || {})
    .sort((a, b) => (a[1].order || 0) - (b[1].order || 0))
    .map(([k, v]) => ({ key: k, label: v.label }));

  const varsByGroup = {};
  for (const [vk, v] of Object.entries(VARIABLES || {})) {
    if (!v.show_in_dropdown) continue;
    const g = v.dropdown_group;
    if (!g) continue;
    if (!varsByGroup[g]) varsByGroup[g] = [];
    varsByGroup[g].push({ key: vk, ...v });
  }
  for (const g of Object.keys(varsByGroup)) {
    varsByGroup[g].sort((a, b) => (a.dropdown_order || 999) - (b.dropdown_order || 999));
  }

  const groupHtml = groupOrder
    .map((g) => {
      const items = varsByGroup[g.key] || [];
      if (!items.length) return '';
      return `
      <details class="sb-group" ${items.some((i) => i.key === s.selectedVariable) ? 'open' : ''}>
        <summary>${g.label}</summary>
        <ul class="var-list">
          ${items
            .map(
              (i) =>
                `<li><button class="var-btn ${s.selectedVariable === i.key ? 'active' : ''}" data-var="${i.key}">${i.dropdown_label || i.display_name}</button></li>`,
            )
            .join('')}
        </ul>
      </details>`;
    })
    .join('');

  const schemeHtml = `
    <section class="sb-section">
      <h3>Color Scheme</h3>
      <select id="color-scheme-select">
        ${listSchemes()
          .map((sk) => `<option value="${sk}" ${s.colorScheme === sk ? 'selected' : ''}>${capitalize(sk)}</option>`)
          .join('')}
      </select>
    </section>`;

  root.innerHTML = layerHtml + `<section class="sb-section"><h3>Variable</h3>${groupHtml}</section>` + schemeHtml;

  root.querySelectorAll('.layer-btn').forEach((btn) =>
    btn.addEventListener('click', () => setState({ activeLayer: btn.dataset.layer })),
  );
  root.querySelectorAll('.var-btn').forEach((btn) =>
    btn.addEventListener('click', () => setState({ selectedVariable: btn.dataset.var })),
  );
  const sel = root.querySelector('#color-scheme-select');
  if (sel) sel.addEventListener('change', (e) => setState({ colorScheme: e.target.value }));
}

export function reflectSidebar() {
  renderSidebar();
}

function capitalize(s) {
  return s ? s[0].toUpperCase() + s.slice(1) : s;
}
