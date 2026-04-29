let COLOR_SCHEMES = null;
let VARIABLES = null;
let DEFAULT_THRESHOLDS = [5, 10, 15, 20, 25, 30, 35, 40, 45];

export function initColors(theme, variablesConfig) {
  COLOR_SCHEMES = {};
  for (const [key, def] of Object.entries(theme.color_schemes || {})) {
    COLOR_SCHEMES[key] = def.colors;
  }
  VARIABLES = variablesConfig.variables;
}

export function getSchemeColors(scheme) {
  return (COLOR_SCHEMES && COLOR_SCHEMES[scheme]) || COLOR_SCHEMES?.blue || [];
}

export function getThresholds(varKey) {
  const v = VARIABLES?.[varKey];
  return (v && v.color_thresholds) || DEFAULT_THRESHOLDS;
}

export function getColorForValue(value, varKey, scheme) {
  const colors = getSchemeColors(scheme);
  const thresholds = getThresholds(varKey);
  const num = parseFloat(value);
  if (isNaN(num)) return '#cccccc';
  for (let i = thresholds.length - 1; i >= 0; i--) {
    if (num >= thresholds[i]) return colors[Math.min(i, colors.length - 1)];
  }
  return colors[0];
}

export function listSchemes() {
  if (!COLOR_SCHEMES) return [];
  return Object.keys(COLOR_SCHEMES);
}
