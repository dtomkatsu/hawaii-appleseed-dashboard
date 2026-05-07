import { getState, setState } from './store.js';

// selectedVariable is intentionally NOT synced to the URL — the page should
// always open with the in-store default (ALICE). Only geography and color
// scheme persist across reloads.
const KEYS = ['activeLayer', 'colorScheme'];

export function readFromUrl() {
  if (!window.location.hash) return;
  const hash = window.location.hash.slice(1);
  const params = new URLSearchParams(hash);
  const patch = {};
  for (const k of KEYS) {
    const v = params.get(shortKey(k));
    if (v) patch[k] = v;
  }
  if (Object.keys(patch).length) setState(patch);
}

export function writeToUrl() {
  const s = getState();
  const params = new URLSearchParams();
  for (const k of KEYS) params.set(shortKey(k), s[k]);
  const newHash = '#' + params.toString();
  if (window.location.hash !== newHash) {
    history.replaceState(null, '', newHash);
  }
}

function shortKey(k) {
  return { activeLayer: 'layer', selectedVariable: 'var', colorScheme: 'scheme' }[k] || k;
}
