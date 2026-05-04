# Hawaii Appleseed Dashboard — Code Review & Improvement Recommendations

**Scope:** functionality, aesthetics, efficiency
**Date:** 2026-05-04
**Branch:** `claude/great-goodall-5DL5L`

---

## Executive summary

The codebase works, but it is carrying significant weight in three areas:

1. **Three "god files"** — `src/data/data_loader.py` (1684 lines), `src/ui/leaflet_component.py` (1357 lines), and `src/ui/leaflet_map_view.py` (1530 lines) — together account for ~55% of the Python code and bundle data, presentation, and behavior concerns into single modules.
2. **Massive style/markup duplication** — `app_style.css` (593) + `enhanced_style.css` (577) + `full_width_layout.py` (76) + `full_width_utils.py` (104) + ~250 lines of inline CSS in `leaflet_component.py` redefine the same selectors (sidebar hide, `.stMap`, dropdowns) with conflicting values. Color tokens (`#3a7710`, `#2a5a0c`, `#1a73e8`, etc.) are hardcoded in 14+ places in JavaScript even though `:root` CSS variables exist.
3. **Repo hygiene leaks** — a 5.2 MB PDF, several `.bak` and `.new` files, an exposed Census API key, two competing logging modules, and ~9 legacy `test_*.py` scripts loose in `scripts/`.

What follows is a prioritized punch list. Items are flagged **[H]** (high), **[M]** (medium), or **[L]** (low) by severity/value.

---

## 1. Security & repo hygiene

### 1.1 [H] Exposed Census API key
- `src/data/acs_data.py:60` — hardcoded fallback key:
  `self.api_key = api_key or "2104852dd7bfd83fbc9e320d650eb57decc11817"`
- **Fix:** remove the literal default; require `CENSUS_API_KEY` env var or explicit constructor argument; rotate the key (it is in git history).

### 1.2 [H] 5.2 MB PDF committed to root
- `state-of-alice-report-hawaii-2025.pdf` bloats every clone.
- **Fix:** `git rm` it, add to `.gitignore`, host externally, link from `README.md`.

### 1.3 [M] Stale and backup files in git
- `src/data/acs_data.py.new` — superseded older version of `acs_data.py`.
- `data/processed/hawaii_house_districts_2025_complete.csv.bak`
- `data/processed/snap_benefits/hawaii_county_snap_2023.csv.bak`
- `test_map.html` (root), `census_api_response.json` (root), `geoid_test_results.json` (root) — test scratch.
- `Activate.ps1` (Windows venv activation) — should not be in source control.
- **Fix:** delete; add `*.bak`, `*.new`, `Activate.ps1`, `*_test_results.json`, `census_api_response.json`, `test_map.html` to `.gitignore`.

### 1.4 [L] Three requirements files with overlapping content
- `requirements.txt` excludes geopandas/folium "for cloud build" (see comments lines 6–10).
- `requirements-cloud.txt` lists those heavy deps.
- `requirements-scripts.txt` does `-r requirements.txt` then re-lists geopandas/fiona/pyproj.
- **Fix:** consolidate to `requirements.txt` (runtime), `requirements-dev.txt` (testing), `requirements-pipeline.txt` (data scripts). Document each in `README.md`. Pin versions consistently.

### 1.5 [L] Loose legacy scripts
- `scripts/test_*.py` — 9 files (test_acs_2023.py, test_census_api.py, test_geoid_*.py, etc.) are one-off data-fetch experiments, not unit tests. They are not picked up by `run_tests.py` or `pytest.ini`.
- **Fix:** move to `scripts/archive/` with a README, or delete if obsolete. Real unit tests already live in `tests/` — keep that boundary clear.

---

## 2. Data layer (`src/data/`)

### 2.1 [H] `DataLoader` is a god class — split it
- `data_loader.py` is 1684 lines; the `DataLoader` class alone handles ACS loading, ALICE merging, SNAP/CEP loading, GeoJSON merging, county/district FIPS conversion, and caching.
- **Specific split:**
  - `DataLoader` becomes a façade that composes `ACSLoader`, `AliceLoader`, `SnapLoader`, `CepLoader`, `GeoJoiner`.
  - The merge logic (`merge_geojson_with_data`, called from `leaflet_map_view._get_merged_geojson` at line 99) moves into a `GeoJoiner` module that takes a generic `pd.DataFrame` keyed by `geoid`.
  - Per-source column lists (currently duplicated as `_add_columns_by_type` / `_initialize_columns_by_type`, `data_loader.py:204–229`) become class-level constants on each loader.

### 2.2 [H] Nested `iterrows()` for county merging
- `data_loader.py:86–100` — nested `for base_idx, base_row in base_data.iterrows(): for merge_idx, merge_row in merge_data.iterrows():` is O(n²) over already-small frames. Inefficient and unreadable.
- **Fix:** standardize join keys (geoid as zero-padded string) once, then `pd.merge(base, other, on="geoid", how="left")`. Same pattern applies wherever you see `iterrows()` in this file.

### 2.3 [M] `merge_geojson_with_data` returns a copy that defeats caching
- `data_loader.py:1233` — `return self._merged_cache[geo_level].copy()`.
- The wrapper `_get_merged_geojson` (`leaflet_map_view.py:88`) is `@st.cache_data` and `load_geojson` (line 27) is `@st.cache_resource`, then `_get_merged_geojson` does `copy.deepcopy(load_geojson(...))` (line 95) on top. You are deep-copying twice and re-merging on cache misses.
- **Fix:** the merge result is read-only at the call site. Drop the inner `.copy()`; document immutability; rely on Streamlit's cache. If a downstream caller mutates, give it its own `.copy()` then.

### 2.4 [M] Cache invalidation tied to a hand-edited string
- `leaflet_map_view.py:85` — `_MERGED_GEOJSON_VERSION = "2026-04-25-v5"` is the only invalidation key for `_get_merged_geojson`. It will go stale silently when the data pipeline changes.
- **Fix:** key the cache by file-mtimes of the underlying GeoJSON + CSVs (compute once, hash). Or compute from `data_sources.json` content hash.

### 2.5 [M] `ACSDataFetcher.__init__` blocks on network
- `acs_data.py:54–72` — constructor logs init twice (lines 55–57 and 67–69), calls `_test_connection()` twice (lines 64 and 72), and that test makes a live HTTP request before any data is requested.
- **Fix:** remove the duplicated init block; make `_test_connection` lazy (run on first fetch) or behind `verify=True` flag.

### 2.6 [M] Over-broad `except Exception` everywhere
- `acs_data.py:127, 281, 399, 835`; `data_loader.py:1215`; `geodata.py:38`. All silently log and continue, masking real failures.
- **Fix:** catch specific exceptions (`requests.RequestException`, `json.JSONDecodeError`, `FileNotFoundError`, `ValueError`). Re-raise unexpected ones.

### 2.7 [M] ALICE percentage logic duplicated
- `acs_data.py:486–585` and `data_loader.py:553–576` both contain percentage-to-decimal conversion logic.
- **Fix:** centralize in `alice_data.py`; call from both places.

### 2.8 [L] Magic GEOID handling
- `geoid_utils.py:39–48` — `state_lower` expects 5 chars, `state_upper` expects 4; no constants or comments explaining the format.
- `data_loader.py:315–357` — district FIPS rules (`if len == 4: ... [:2] + '0' + [2:]`) are bare and untested.
- `data_loader.py:619–634` — hardcoded fallback ALICE rates (35, 38, 36, 34) with no source.
- **Fix:** define `GEOID_LENGTHS` / `GEOID_FORMATS` constants; add unit tests covering each branch; replace fallbacks with an explicit "data missing" state.

### 2.9 [L] Excessive log file I/O
- `acs_data.py:238–276` — 9+ separate `open(self.debug_log_file, 'a')` calls in one function.
- **Fix:** route through the standard `logging` module with a `FileHandler`; remove the bespoke debug-log code.

### 2.10 [L] Dead code
- `acs_data.py:481–527` — S0802 transportation mapping dict defined but consumer is commented out.
- `data_loader.py:986–999` — `_convert_county_to_fips()` is never called; direct string mappings used instead.
- **Fix:** delete.

---

## 3. UI layer — Python (`src/ui/`, `pages/`)

### 3.1 [H] `leaflet_component.py` mixes 4 languages in one file
- 1357 lines = ~300 Python + ~250 lines of inline CSS in `_get_css_styles()` (lines 74–326) + ~800 lines of JavaScript embedded as f-string template (lines 362–1152).
- The JS regenerates Leaflet handlers, scroll indicators, popup HTML, and metric cards as Python string concatenation. Every function (`createCategorizedMetricsHtml`, `createSnapHtml`, `getRepresentativeInfo`) re-emits similar styled blocks.
- **Fix (concrete):**
  - Move the JavaScript to `src/components/leaflet_custom_map/frontend/src/leafletMap.ts` (the directory already exists). Pass props (geojson, color scheme, variable) via `streamlit.components.v1.declare_component`.
  - Move CSS to `src/ui/leaflet_map.css`.
  - Python file then drops to ~200 lines: build-config + render call.

### 3.2 [H] `leaflet_map_view.create_leaflet_map_view` is doing too much
- `leaflet_map_view.py:665–960` is 295 lines that:
  - Routes URL params (`_route_cascade_click_from_url`).
  - Validates and seeds 5 session-state keys.
  - Resets dropdown widget keys.
  - Loads + merges GeoJSON.
  - Injects 100+ lines of dropdown-fix JavaScript inline (lines 752–860).
  - Renders 4 cascade columns with copy-pasted header HTML.
  - Decides which variable to map.
  - Renders the map and a source line.
- **Fix:** split into `_init_session_state()`, `_handle_dropdown_resets()`, `_render_variable_selectors()`, `_resolve_active_variable()`, `_render_map()`. Move the 4 cascade column blocks into a single helper `_render_cascade_column(group, label_html, items, ...)` that takes the group config.

### 3.3 [H] Cascade router uses URL navigation as state
- `leaflet_map_view.py:473–662` — clicking a cascade item triggers a real browser navigation (`<a href="?sel=...">`), and `_build_state_query_string()` (line 473) round-trips `layer`, `var`, `color` through the URL because Streamlit Cloud Run wipes session state on navigation.
- This breaks browser back/forward, hides selection state from `st.session_state` listeners, and forces every new dropdown to participate in the URL contract.
- **Fix (options, in order of effort):**
  1. **Low effort:** convert each cascade leaf to an `st.button` styled to look like a menu item (no navigation, session_state stays); use `st.popover` (Streamlit 1.32+) for the menu surface.
  2. **High effort but cleanest:** make the cascade a custom Streamlit component with a typed return value, the same pattern used for `leaflet_custom_map`.

### 3.4 [H] 100+ lines of inline JS to "fix" Streamlit's dropdown scroll
- `leaflet_map_view.py:752–860` — a `MutationObserver` + `setInterval(fixDropdownScrolling, 2000)` poll runs forever, mutating BaseWeb DOM that the cascade menus *don't actually use* (the cascades are pure HTML now, not `st.selectbox`). This is dead code that still pays a runtime cost on every rerun.
- **Fix:** delete the entire script block. The rules it sets (`max-height`, `overflow-y`) belong in `app_style.css` if they apply at all.

### 3.5 [M] Sidebar config duplicates the registry
- `src/ui/sidebar.py:18–44` hardcodes 13 variable options that already exist in `src/config/variables.json` and are exposed by `variable_registry.get_variables_for_dropdown()`.
- **Fix:** read from the registry (already used in `leaflet_map_view.py`); delete the local dict. The registry becomes the single source of truth.

### 3.6 [M] `pages/geo_detail.py` is 994 lines with inline styles & magic constants
- Lines 33–40: chart-container styling duplicates `app_style.css`/`enhanced_style.css`.
- Lines 82–88: `ECONOMIC_IMPACT_DEFAULTS` magic numbers (75%, 1.79, 150, 85) with no source.
- **Fix:** split into `pages/geo_detail.py` (page wiring, ~150 lines) + `src/ui/geo_detail/` package (sections: overview, economic, demographics, housing). Move defaults to `src/config/economic_impact.json` with a source-citation field.

### 3.7 [M] `full_width_layout.py` and `full_width_utils.py` are duplicates
- Both inject the same "max out the page width" CSS via `st.markdown('<style>...</style>')`. `run_leaflet.py:55` calls one and then `run_leaflet.py:59` loads `app_style.css` which redefines the same rules a third time.
- **Fix:** delete both Python files; move all width rules into `app_style.css`. Net change: -180 lines.

### 3.8 [M] `leaflet_map_view.create_info_panel` and `display_feature_details` (lines 962–1247) are dead code
- Both render a Streamlit-side info panel, but the live UI uses the JS-side panel inside the Leaflet component. Neither function is called.
- **Fix:** delete (saves ~285 lines of `leaflet_map_view.py`).

### 3.9 [L] `leaflet_legend.py` hardcodes per-variable thresholds
- Lines 24–108 — chained `if (SELECTED_VARIABLE.includes('poverty') || ...)` builds legend HTML inline for each variable family. The `variable_registry` already exposes `get_color_thresholds_json()`.
- **Fix:** drive the legend from registry-supplied thresholds and a single legend-row template; loop instead of branching.

### 3.10 [L] Header HTML repeated four times
- `leaflet_map_view.py:870, 884, 896, 909` — each cascade column re-emits a 200-character inline-styled `<div>` header that differs only in the label text and the hidden/visible accent border.
- **Fix:** extract `_render_cascade_header(label: str, *, accented: bool)` returning the markup.

---

## 4. CSS / aesthetics

### 4.1 [H] Two large CSS files have ~50% overlap
- `src/ui/app_style.css` (593 lines) and `src/ui/enhanced_style.css` (577 lines) define the same selectors with different values:
  - `.stMap` / `.map-container` / `.leaflet-container` defined in both files **and** in `full_width_layout.py:22–30`.
  - Sidebar hide rules exist in both files (`section[data-testid="stSidebar"]`) plus inline in `run_leaflet.py:43–49`.
  - Dropdown styling: `app_style.css:305–412` ≈ `enhanced_style.css:258–566`, with conflicting animation delays.
- **Fix:** consolidate into a single `src/ui/styles/` directory with three files split by responsibility: `tokens.css` (variables), `layout.css` (page width, sidebar hide), `components.css` (dropdowns, legend, map). Estimated total: ~500 lines vs. the current ~1170.

### 4.2 [H] Color tokens hardcoded in JS instead of using CSS variables
- `enhanced_style.css:4–63` defines `:root` variables (`--color-primary: #3a7710`, etc.).
- But `leaflet_component.py:74–326`, `leaflet_legend.py`, and the inline headers in `leaflet_map_view.py` all hardcode `'#3a7710'`, `'#2a5a0c'`, `'#1a73e8'`, `'#f0f7e9'`, etc.
- The same green appears as 5 different shades across files: `#3a7710`, `#2a5a0c`, `#2d5d0c`, `#6a8a5a`, `#3a8a50`.
- **Fix:** define a Python-side palette module `src/ui/palette.py` that reads `theme.json`. Use `var(--color-primary)` in CSS; reference `palette.PRIMARY` in any Python that emits HTML/JS. One source, four consumers.

### 4.3 [M] No typography or spacing scale
- Font sizes used in CSS: 9px, 10px, 11px, 12px, 13px, 14px, 15px, 0.7rem, 0.72rem, 0.75rem, 0.78rem, 0.875rem — no system.
- Border-radius values: 3px, 4px, 6px, 8px, 10px, 0.5rem, 0.625rem, 99px.
- **Fix:** define `--space-1..6`, `--text-xs..xl`, `--radius-sm/md/lg/full` in `tokens.css`; replace literal values.

### 4.4 [M] Accessibility gaps
- **Hover-only menus:** the cascade dropdowns (`leaflet_map_view.py:_cascade_css`, line 326: `.cascade-root:hover > .cascade-menu { display: block; }`) have no `:focus-within` / keyboard / touch fallback. Keyboard users cannot open them; mobile users cannot hover.
- **Focus outline removed** without replacement (`leaflet_component.py:282–291`).
- **Color contrast:** body green `#3a7710` on light backgrounds is borderline at 14px. Run Lighthouse / axe-core.
- **No ARIA:** map popups (`leaflet_component.py:827–850`) and the cascade trigger lack `role`, `aria-expanded`, `aria-controls`.
- **Fix:**
  - Add `:focus-within` mirror of every `:hover` rule in `_cascade_css`.
  - Make the cascade trigger a `<button>` with `aria-haspopup="menu"`, `aria-expanded`, and arrow-key navigation.
  - Restore visible focus rings (`outline: 2px solid var(--color-primary); outline-offset: 2px`).

### 4.5 [L] Brittle CSS selectors
- `app_style.css:79–88` targets obfuscated Emotion class names: `svg.e10vaf9m1.st-emotion-cache-1f3w014.ex0cdmw0`. These break on every Streamlit upgrade.
- **Fix:** replace with `[data-testid="..."]` selectors only. If no testid exists, file an upstream issue.

### 4.6 [L] Unused CSS variables
- `enhanced_style.css:56–62` — `--shadow-xl`, `--transition-slow`, `--z-index-modal-backdrop`, `--z-index-tooltip` declared, never referenced.
- **Fix:** delete or use.

### 4.7 [L] Animation delays scaled past visible budget
- `enhanced_style.css:436–453` and `_cascade_css` lines 340–347 stagger 9 menu items at 0.04–0.25s. The total animation runs longer than the time a user takes to look at the menu. Feels laggy.
- **Fix:** cap at 3 stagger steps (0.04s, 0.08s, 0.12s) or drop the stagger entirely.

---

## 5. Configuration layer

### 5.1 [M] `data_source_registry._load_config()` is uncached
- `src/data/data_source_registry.py:21–24` — comment says "not cached — callers may mutate and reload" but 13 accessor functions (`get_year`, `get_file_path`, `get_alice_excel_path`, etc.) each re-parse `data_sources.json` on every call. During a single Streamlit run this happens dozens of times.
- The other registries (`theme_registry`, `ui_strings_registry`, `variable_registry`) all use `@lru_cache(maxsize=1)`.
- **Fix:** add `@lru_cache(maxsize=1)` to `_load_config`; provide an explicit `reload_config()` for callers that need it.

### 5.2 [M] No JSON schema validation
- `variables.json`, `theme.json`, `ui_strings.json`, `data_sources.json` have no schemas.
- `variable_registry.py:79` does `v[field]` — a missing field crashes at render time.
- **Fix:** add `pydantic` (already lightweight) models for each config file. Validate at import. Surface schema errors as a clear startup failure rather than silent UI degradation.

### 5.3 [L] Two competing logging modules
- `src/utils/debug.py` (67 lines) and `src/utils/logging_utils.py` (54 lines) both define `setup_*_logging()` and `log_error()` with overlapping behavior.
- `run_leaflet.py:11` imports `setup_logging` from `logging_utils` but **never calls it** — logging only works because the root logger is auto-initialized.
- **Fix:** keep `logging_utils`, delete `debug.py`, actually call `setup_logging()` in `main()`.

### 5.4 [L] `ui_strings_registry.get_string` returns silent fallbacks
- Hard to detect missing keys. Recommend: log a `DEBUG` line on miss; expose a `--strict-strings` mode for CI.

---

## 6. Frontend behavior & functionality

### 6.1 [M] No loading/error states for the map
- `leaflet_map_view.py:744–749` — if `_get_merged_geojson` returns `None`, only a one-line `st.error` shows. If it succeeds slowly, the user sees a blank tab.
- **Fix:** wrap the map render in `with st.spinner("Loading map..."):` and show a skeleton placeholder for the chart card.

### 6.2 [M] Map state stored inconsistently
- Geography selection lives in `st.session_state.active_layer`.
- Variable selection lives in *three* mutually exclusive keys (`selected_variable`, `selected_food_security_variable`, `selected_housing_transportation_variable`) — `_apply_var_to_session_state` (`leaflet_map_view.py:593`) zeroes the others.
- Selected map feature lives in browser `localStorage` (`leaflet_component.py:741`) with no Python-side mirror.
- **Fix:** collapse the three variable keys into a single `st.session_state.selected_variable` plus a derived `dropdown_group` lookup. Mirror selected feature into `st.session_state.selected_geography` via `streamlit.components.v1` return value (already partially wired in `create_info_panel`).

### 6.3 [L] Brittle representative-data file paths
- `leaflet_component.py:1198–1227` references `hawaii_house_districts_2025_complete.csv` by literal name. Any rename breaks the popup.
- **Fix:** route through `data_source_registry.get_file_path("representatives", "house")`.

### 6.4 [L] Cascade routing has no browser-back support
- Because `_route_cascade_click_from_url` clears `st.query_params` (`leaflet_map_view.py:662`), back/forward will not retrace selections.
- **Fix:** keep params after routing if you intend deep-linkable selection state; otherwise document that the URL is intentionally transient.

---

## 7. Suggested execution order

| Phase | Items | Approx. effort | Risk |
|---|---|---|---|
| **1. Hygiene** | 1.1 (rotate key), 1.2 (PDF), 1.3 (.bak/.new), 1.4–1.5 | ½ day | Low |
| **2. CSS consolidation** | 4.1, 4.2, 4.6, 3.7 (delete `full_width_*.py`) | 1 day | Low — pure refactor |
| **3. Dead-code removal** | 3.4 (dropdown JS), 3.8 (info panel), 2.10 | ½ day | Low |
| **4. Data layer split** | 2.1, 2.2, 2.3, 2.7 | 2–3 days | Medium |
| **5. Cascade rebuild** | 3.3 (st.popover or custom component), 3.10 (header helper), 4.4 (a11y) | 2 days | Medium — UX-visible |
| **6. JS extraction** | 3.1 (custom component), 3.9 (legend from registry) | 2–3 days | Medium |
| **7. Config validation** | 5.1, 5.2, 5.3 | 1 day | Low |
| **8. Page split + tokens** | 3.6, 4.3, 6.2 | 2 days | Low |

**Total:** ~11–14 person-days for the full set; phase 1 + 2 + 3 alone (~2 days) removes >2,000 lines and most of the maintenance pain.

---

## 8. Quick wins (under 1 hour each)

1. Delete `src/data/acs_data.py.new`.
2. Delete the two `.bak` CSVs and add `*.bak` to `.gitignore`.
3. Delete `Activate.ps1`, `test_map.html`, `census_api_response.json`, `geoid_test_results.json`.
4. Delete `leaflet_map_view.create_info_panel` and `display_feature_details` (~285 lines, dead code).
5. Delete the 100-line dropdown-fix JS at `leaflet_map_view.py:752–860`.
6. Add `@lru_cache(maxsize=1)` to `data_source_registry._load_config`.
7. Replace duplicated init in `acs_data.py:54–72` with a single block.
8. Move the Census API key to `os.environ["CENSUS_API_KEY"]` and rotate.
9. Replace the nested `iterrows` in `data_loader.py:86–100` with a `pd.merge`.
10. Delete `src/utils/debug.py` and call `setup_logging()` from `run_leaflet.main`.

These ten changes alone delete on the order of 600–800 lines, close the security exposure, and remove the worst single perf hotspot.
