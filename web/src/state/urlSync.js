import { getState, setState } from './store.js';

// selectedVariable is intentionally NOT *written* to the URL — within a
// normal session it should reset to ALICE on each load. But it IS read
// one-way on initial load (?var=<key>) so an embed/iframe URL can deep-
// link to a specific variable like Millionaires. Geography + color
// scheme persist round-trip as before.
const KEYS = ['activeLayer', 'colorScheme'];
const READ_ONLY_KEYS = ['selectedVariable']; // read from URL, never written

export function readFromUrl() {
  // Accept both hash (#layer=...) and search (?var=...) so embed URLs work
  // even without the # — query strings are more iframe-friendly.
  const sources = [];
  if (window.location.hash) sources.push(window.location.hash.slice(1));
  if (window.location.search) sources.push(window.location.search.slice(1));
  if (!sources.length) return;
  const params = new URLSearchParams(sources.join('&'));
  const patch = {};
  for (const k of [...KEYS, ...READ_ONLY_KEYS]) {
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
