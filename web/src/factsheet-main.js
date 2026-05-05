import { fetchJson } from './data/loader.js';
import { buildGeoData } from './factsheet/formatters.js';
import { generateFactSheetHTML } from './factsheet/template.js';

async function main() {
  const params = new URLSearchParams(window.location.search);
  const geoId = params.get('geo_id');
  const level = params.get('level') || 'county';

  const root = document.getElementById('factsheet-root');

  if (!geoId) {
    root.innerHTML = '<p class="fs-error">No geography selected. Open this page from the map by clicking a region.</p>';
    return;
  }

  try {
    const [geojson, stateSummary] = await Promise.all([
      fetchJson(`${import.meta.env.BASE_URL}data/${level}.geojson`),
      fetchJson(`${import.meta.env.BASE_URL}data/state_summary.json`).catch(() => ({})),
    ]);

    const feature = geojson.features.find(
      (f) => String(f.properties.GEOID) === String(geoId) || String(f.properties.geoid) === String(geoId),
    );

    if (!feature) {
      root.innerHTML = `<p class="fs-error">Geography not found: ${geoId}</p>`;
      return;
    }

    const geo = buildGeoData(feature.properties, stateSummary);
    document.title = `Fact Sheet: ${geo.name}`;
    root.innerHTML = generateFactSheetHTML(geo);
  } catch (err) {
    console.error('Fact sheet error:', err);
    root.innerHTML = `<p class="fs-error">Failed to load fact sheet: ${err.message}</p>`;
  }
}

main();
