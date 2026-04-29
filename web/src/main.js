import { loadConfig, loadRepData } from './data/loader.js';
import { initAnalysis } from './analysis-main.js';
import { initColors } from './map/colors.js';
import { createMap, getMap } from './map/mapInstance.js';
import { setLayer, setVariable, setColorScheme } from './map/layerManager.js';
import { initPopup } from './map/popup.js';
import { initLegend, renderLegend } from './ui/legend.js';
import { initSidebar, renderSidebar } from './ui/sidebar.js';
import { initInfoPanel } from './ui/infoPanel.js';
import { getState, subscribe } from './state/store.js';
import { readFromUrl, writeToUrl } from './state/urlSync.js';

async function main() {
  const [config, repData] = await Promise.all([loadConfig(), loadRepData()]);
  initColors(config.theme, config.variables);
  initLegend(config.variables);
  initSidebar(config.variables);
  initInfoPanel(config.variables);
  initPopup(config.variables, repData);

  createMap('main-map', config.theme);

  readFromUrl();
  const s0 = getState();

  subscribe(async (state, changed) => {
    if ('activeLayer' in changed) {
      await setLayer(state.activeLayer);
      setVariable(state.selectedVariable);
      setColorScheme(state.colorScheme);
      renderLegend(state.selectedVariable, state.colorScheme);
    }
    if ('selectedVariable' in changed) {
      setVariable(state.selectedVariable);
      renderLegend(state.selectedVariable, state.colorScheme);
    }
    if ('colorScheme' in changed) {
      setColorScheme(state.colorScheme);
      renderLegend(state.selectedVariable, state.colorScheme);
    }
    writeToUrl();
    renderSidebar();
  });

  await setLayer(s0.activeLayer);
  setVariable(s0.selectedVariable);
  setColorScheme(s0.colorScheme);
  renderLegend(s0.selectedVariable, s0.colorScheme);
  renderSidebar();
  writeToUrl();

  // Tab switching
  document.querySelectorAll('.main-tab').forEach((btn) => {
    btn.addEventListener('click', async () => {
      const tab = btn.dataset.tab;
      document.querySelectorAll('.main-tab').forEach((b) => {
        b.classList.toggle('active', b === btn);
        b.setAttribute('aria-selected', b === btn ? 'true' : 'false');
      });
      document.getElementById('tab-map').hidden = tab !== 'map';
      document.getElementById('tab-data').hidden = tab !== 'data';
      if (tab === 'map') {
        const map = getMap();
        if (map) map.invalidateSize();
      }
      if (tab === 'data') {
        await initAnalysis(config);
      }
    });
  });
}

main().catch((err) => {
  console.error('Dashboard init failed:', err);
  const root = document.querySelector('.map-wrap');
  if (root) {
    root.innerHTML = `<div class="error-banner">Failed to load dashboard: ${err.message}<br><small>Make sure the data pipeline has run: <code>bash ../scripts/build_static/run_all.sh</code></small></div>`;
  }
});
