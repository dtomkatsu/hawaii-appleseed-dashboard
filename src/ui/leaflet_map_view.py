"""Leaflet Map View for Hawaii Appleseed Dashboard."""
import streamlit as st
import pandas as pd
import copy
import json
import logging
from pathlib import Path
import sys
from urllib.parse import quote
import plotly.express as px

# Import local modules
from data.data_loader import DataLoader
from .leaflet_component import create_leaflet_map
from config.variable_registry import (
    get_valid_variable_keys,
    get_variables_for_dropdown,
    get_display_names,
    get_display_name,
    get_variable_source,
    get_all_variables,
)

# Set up logging
logger = logging.getLogger(__name__)

@st.cache_resource
def load_geojson(layer_name):
    """Load GeoJSON data for the specified layer.

    Uses @st.cache_resource to avoid pickle/unpickle overhead on every call.
    The returned dict is shared across sessions (read-only). Callers that
    need to mutate the data must deep-copy it first.
    """
    import gzip
    
    # Map layer names to file paths
    layer_files = {
        'State Boundary': 'hawaii_state_boundary.geojson',
        'Counties': 'hawaii_county_boundaries.geojson',
        'House Districts': 'Hawaii_State_House_Districts_2022.geojson',
        'Senate Districts': 'Hawaii_State_Senate_Districts_2022.geojson'
    }
    
    if layer_name not in layer_files:
        logger.error(f"Unknown layer: {layer_name}")
        return None
    
    # Construct the file paths (try compressed first)
    base_path = Path(__file__).parent.parent.parent / 'data' / 'Processed GeoJsons'
    compressed_path = base_path / f"{layer_files[layer_name]}.gz"
    original_path = base_path / layer_files[layer_name]
    
    try:
        # Try compressed file first
        if compressed_path.exists():
            with gzip.open(compressed_path, 'rt') as f:
                geojson_data = json.load(f)
                logger.info(f"Successfully loaded compressed GeoJSON for {layer_name}")
                return geojson_data
        
        # Fallback to original file
        elif original_path.exists():
            with open(original_path, 'r') as f:
                geojson_data = json.load(f)
                logger.info(f"Successfully loaded GeoJSON for {layer_name} from {original_path}")
                return geojson_data
        
        else:
            logger.error(f"Neither compressed nor original GeoJSON file found for {layer_name}")
            return None
            
    except Exception as e:
        logger.error(f"Error loading GeoJSON for {layer_name}: {str(e)}")
        return None

@st.cache_resource(ttl=None, show_spinner=False, hash_funcs={})
def get_data_loader(_cache_version="v7"):
    """Get a cached DataLoader instance."""
    # _cache_version parameter forces cache invalidation when changed
    return DataLoader()

# Bump this to bust _get_merged_geojson cache when the data pipeline changes.
# The cache has no other invalidation key, so stale merged GeoJSON persists until bumped.
_MERGED_GEOJSON_VERSION = "2026-04-25-v5"


@st.cache_data(show_spinner=False)
def _get_merged_geojson(layer_name, geo_level, _version=_MERGED_GEOJSON_VERSION):
    """Load GeoJSON and merge with statistical data, cached.

    Combines load_geojson + merge into one cached call so repeated
    renders skip both the deep-copy and the merge computation.
    """
    geojson_data = copy.deepcopy(load_geojson(layer_name))
    if geojson_data is None:
        return None
    data_loader = get_data_loader()
    return data_loader.merge_geojson_with_data(geojson_data, geo_level)


# ---------------------------------------------------------------------------
# Cascade menu helpers
#
# Replaces the Economic Security and Food Security selectboxes with
# hover-reveal cascade menus. Long families of related variables
# (Tax Credits = CTC + EITC, SNAP, CEP) collapse under a single
# submenu, reducing the number of visible options at top level.
#
# Click round-trip: leaf items are plain <a href="?sel=<key>"> anchors.
# Streamlit reruns when the URL changes; _route_cascade_click_from_url
# reads the param, routes it to the right session-state key, clears
# the URL so a refresh doesn't re-fire, and lets the rest of the view
# render as usual.
#
# All four dropdowns (Geography, Econ, Food, H&T) use the same cascade
# component so they open on hover rather than click, have no blinking
# text cursor, and share identical styling. Geography and H&T happen
# to be flat (no submenus) while Econ and Food collapse related
# variables under Tax Credits / SNAP / CEP parent items.
# ---------------------------------------------------------------------------

# Variables that get grouped under the "Tax Credits" submenu in
# the Economic Security cascade.
_TAX_CREDIT_KEYS = {
    "ctc_avg_amount",
    "ctc_participation_rate",
    "federal_eitc_avg_amount",
    "eitc_participation_rate",
    "state_eitc_avg_amount",
}

# Variables grouped under "SNAP" in the Food Security cascade.
_SNAP_KEYS = {
    "snap_household_rate",
    "snap_benefit_annual_per_household",
    "snap_benefits_annual_total",
}

# Variables grouped under "CEP" in the Food Security cascade.
_CEP_KEYS = {
    "cep_percentage",
    "cep_display",
}


def _build_econ_cascade_items() -> list:
    """Top-level items for the Economic Security cascade.

    Single-variable options stay flat; CTC + EITC collapse into a
    "Tax Credits" submenu.
    """
    items = get_variables_for_dropdown("economic_security")
    main = [v for v in items if v["key"] not in _TAX_CREDIT_KEYS]
    tax = [v for v in items if v["key"] in _TAX_CREDIT_KEYS]

    out = [{"key": v["key"], "label": v["label"]} for v in main]
    if tax:
        out.append({
            "label": "Tax Credits",
            "children": [{"key": v["key"], "label": v["label"]} for v in tax],
        })
    return out


def _build_food_cascade_items() -> list:
    """Top-level items for the Food Security cascade.

    SNAP and CEP variables each collapse into their own submenu.
    Anything else (if added later) stays flat.
    """
    items = get_variables_for_dropdown("food_security")
    snap = [v for v in items if v["key"] in _SNAP_KEYS]
    cep = [v for v in items if v["key"] in _CEP_KEYS]
    other = [v for v in items if v["key"] not in _SNAP_KEYS and v["key"] not in _CEP_KEYS]

    out = [{"key": v["key"], "label": v["label"]} for v in other]
    if snap:
        out.append({
            "label": "SNAP",
            "children": [{"key": v["key"], "label": v["label"]} for v in snap],
        })
    if cep:
        out.append({
            "label": "CEP",
            "children": [{"key": v["key"], "label": v["label"]} for v in cep],
        })
    return out


# Geography layer names aren't in the variable registry (they aren't
# variables — they toggle the map's boundary GeoJSON). We prefix their
# keys with "layer:" in the URL so the router can distinguish them
# from variable keys (which are always plain snake_case).
_GEOGRAPHY_LAYER_OPTIONS = ["State Boundary", "Counties", "House Districts", "Senate Districts"]


def _build_geography_cascade_items() -> list:
    """Top-level items for the Geography cascade. Flat — no submenus."""
    return [
        {"key": f"layer:{name}", "label": name}
        for name in _GEOGRAPHY_LAYER_OPTIONS
    ]


def _build_housing_cascade_items() -> list:
    """Top-level items for the Housing & Transportation cascade.

    Flat list pulled straight from the variable registry — no natural
    sub-grouping like Econ (Tax Credits) or Food (SNAP/CEP).
    """
    items = get_variables_for_dropdown("housing_transportation")
    return [{"key": v["key"], "label": v["label"]} for v in items]


def _cascade_css() -> str:
    """Shared CSS for every cascade on the page.

    Mirrors the H&T selectbox resting styling (colors / radius / height),
    then layers on:
      * A staggered fade-in per menu item (cascadeItemIn keyframe + :nth-child delay).
      * A gradient hover wash (left-to-right translucent green).
      * A rotating parent caret (▸ → ▾) when a submenu opens.
      * A soft, multi-layer popover shadow with a subtle top rim-light.
      * A small green dot next to the currently-selected leaf.

    Emitted inline per call; browsers dedupe identical style blocks.
    """
    return """
    <style>
      /* Staggered entry animation for each menu item */
      @keyframes cascadeItemIn {
        from { opacity: 0; transform: translateY(-4px); }
        to   { opacity: 1; transform: translateY(0); }
      }

      .cascade-root {
        /* Inherit Streamlit's Source Sans Pro body font for a native feel. */
        font-family: inherit;
        font-size: 0.875rem;
        line-height: 1.5;
        position: relative;
        width: 100%;
      }
      /* Trigger — matches .stSelectbox > div[data-baseweb="select"] > div */
      .cascade-trigger {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.5rem 0.75rem;
        min-height: 40px;
        background-color: #f0f7e9;
        border: 1px solid rgba(94, 82, 64, 0.2);
        border-radius: 0.5rem;
        color: rgba(19, 52, 59, 1);
        cursor: pointer;
        user-select: none;
        box-sizing: border-box;
        transition: all 250ms cubic-bezier(0.4, 0, 0.2, 1);
      }
      /* Hover state — matches .stSelectbox > div[data-baseweb="select"] > div:hover */
      .cascade-root:hover > .cascade-trigger {
        background-color: #e8f3df;
        border-color: #3a7710;
      }
      .cascade-current {
        flex: 1;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        font-size: 0.875rem;
        line-height: 1.5;
      }
      .cascade-current.is-placeholder,
      .cascade-current.is-selected { color: rgba(19, 52, 59, 1); }
      .cascade-trigger-caret {
        margin-left: 8px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        transition: transform 0.3s ease;
        color: rgba(19, 52, 59, 1);
      }
      .cascade-root:hover > .cascade-trigger .cascade-trigger-caret {
        transform: rotate(180deg);
      }

      /* Popover surface — softer multi-layer shadow + a 1px top rim-light
         using an inset highlight. Gives it a subtle "lifted card" feel
         instead of one flat drop-shadow. */
      .cascade-menu {
        list-style: none;
        padding: 6px 0;
        margin: 0;
        background-color: rgba(255, 255, 253, 1);
        border: 1px solid rgba(94, 82, 64, 0.15);
        border-radius: 0.625rem;
        box-shadow:
          inset 0 1px 0 rgba(255, 255, 255, 0.9),
          0 1px 2px rgba(0, 0, 0, 0.04),
          0 8px 20px rgba(20, 45, 15, 0.10),
          0 18px 40px rgba(20, 45, 15, 0.08);
        min-width: 100%;
        width: max-content;
        max-width: 360px;
      }
      .cascade-root > .cascade-menu {
        display: none;
        position: absolute;
        top: 100%;
        left: 0;
        z-index: 9999;
        margin-top: 4px;
        animation: dropdownOpen 0.3s cubic-bezier(0.34, 1.56, 0.64, 1) forwards;
        transform-origin: top center;
      }
      .cascade-root > .cascade-menu::before {
        content: '';
        position: absolute;
        left: 0;
        right: 0;
        top: -6px;
        height: 6px;
        background: transparent;
      }
      .cascade-root:hover > .cascade-menu { display: block; }

      .cascade-menu li {
        padding: 0;
        position: relative;
        color: rgba(19, 52, 59, 1);
      }
      /* Stagger each menu item so they sweep in sequentially when the
         menu opens. Works because each menu-open triggers the animation
         (the parent's display flips from none to block). */
      .cascade-menu > li {
        opacity: 0;
        animation: cascadeItemIn 0.22s cubic-bezier(0.2, 0.8, 0.3, 1) forwards;
      }
      .cascade-menu > li:nth-child(1) { animation-delay: 0.04s; }
      .cascade-menu > li:nth-child(2) { animation-delay: 0.07s; }
      .cascade-menu > li:nth-child(3) { animation-delay: 0.10s; }
      .cascade-menu > li:nth-child(4) { animation-delay: 0.13s; }
      .cascade-menu > li:nth-child(5) { animation-delay: 0.16s; }
      .cascade-menu > li:nth-child(6) { animation-delay: 0.19s; }
      .cascade-menu > li:nth-child(7) { animation-delay: 0.22s; }
      .cascade-menu > li:nth-child(n+8) { animation-delay: 0.25s; }

      /* Leaf + parent row layout. Tighter left padding than before;
         the green accent on hover is delivered by the ::before pseudo
         below (absolutely positioned, no layout cost) instead of a
         reserved transparent border. The slide-on-hover animation and
         gradient wash are preserved exactly. */
      .cascade-leaf > a,
      .cascade-parent > .cascade-label {
        position: relative;
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 10px 14px;
        color: rgba(19, 52, 59, 1);
        text-decoration: none;
        transition: background 0.22s ease, padding-left 0.22s ease, color 0.22s ease;
        white-space: nowrap;
        font-weight: 500;
      }
      .cascade-parent > .cascade-label { cursor: default; }

      /* Hover accent stripe — replaces the old border-left:4px transparent.
         Sits absolutely at the very left edge of each row so it never
         pushes content sideways. Transparent by default; turns green on
         hover (matched to the row's color transition). */
      .cascade-leaf > a::before,
      .cascade-parent > .cascade-label::before {
        content: '';
        position: absolute;
        left: 0;
        top: 0;
        bottom: 0;
        width: 3px;
        background: transparent;
        transition: background 0.22s ease;
        pointer-events: none;
      }
      .cascade-leaf:hover > a::before,
      .cascade-parent:hover > .cascade-label::before {
        background: #3a7710;
      }

      /* Hover background — gradient wash + a +6px slide-right. Kept
         (slightly tightened) so hover still has the bold "light sweeping
         in from the left" feel instead of just a subtle tint. */
      .cascade-leaf:hover > a,
      .cascade-parent:hover > .cascade-label {
        background: linear-gradient(90deg, rgba(58, 119, 16, 0.18) 0%, rgba(58, 119, 16, 0.04) 60%, rgba(58, 119, 16, 0) 100%);
        padding-left: 20px;
        color: #1f3d10;
      }

      /* Selected leaf — moved to ::after (so ::before stays free for the
         accent stripe). Kept at full 6×6 size to preserve the prior
         visual weight; just nudged 2px inward to fit the tighter padding. */
      .cascade-leaf--selected > a {
        color: #2a5a0c;
        font-weight: 600;
      }
      .cascade-leaf--selected > a::after {
        content: '';
        position: absolute;
        left: 4px;
        top: 50%;
        transform: translateY(-50%);
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background: #3a7710;
        box-shadow: 0 0 0 2px rgba(58, 119, 16, 0.15);
        pointer-events: none;
      }

      /* Parent caret — small chevron that rotates from ▸ (pointing right)
         to ▾ (pointing down) when the submenu opens on hover. */
      .cascade-parent > .cascade-label .cascade-caret {
        margin-left: 12px;
        color: #3a7710;
        display: inline-block;
        transition: transform 0.22s cubic-bezier(0.34, 1.56, 0.64, 1);
        transform-origin: center;
      }
      .cascade-parent:hover > .cascade-label .cascade-caret {
        transform: rotate(90deg);
      }

      /* Submenu — same visual treatment + same pop animation */
      .cascade-parent > .cascade-menu {
        display: none;
        position: absolute;
        left: 100%;
        top: -5px;
        margin-left: 2px;
      }
      .cascade-parent > .cascade-menu::before {
        content: '';
        position: absolute;
        top: 0;
        bottom: 0;
        left: -6px;
        width: 6px;
        background: transparent;
      }
      .cascade-parent:hover > .cascade-menu {
        display: block;
        animation: dropdownOpen 0.3s cubic-bezier(0.34, 1.56, 0.64, 1) forwards;
        transform-origin: top left;
      }
    </style>
    """


_VALID_COLOR_SCHEMES = {"blue", "green", "red", "purple"}


def _current_active_var() -> str | None:
    """The currently-selected variable across all three mutually-exclusive
    dropdown groups (Econ / Food / H&T), or None if nothing is selected."""
    return (
        st.session_state.get("selected_variable")
        or st.session_state.get("selected_food_security_variable")
        or st.session_state.get("selected_housing_transportation_variable")
    )


def _build_state_query_string() -> str:
    """Build a "&k=v&k=v..." suffix that round-trips current session
    state through cascade-link URLs.

    Why: the cascade renders <a href="?sel=..."> links. Clicking one
    triggers a real browser navigation, which Streamlit treats as a
    refresh — session state is cleared on the new connection. Without
    this preservation, every cascade click resets active_layer to its
    init default ('Counties' from run_leaflet.py), even if the user
    had selected House/Senate Districts. Same for the active variable
    when the user clicks a Geography option.

    Each click URL therefore carries a snapshot of layer + var + color,
    which the router (_route_cascade_click_from_url) re-applies BEFORE
    handling the click, so the new click's effect is the only thing
    that overrides the snapshot.
    """
    parts = []
    layer = st.session_state.get("active_layer")
    if layer:
        parts.append(f"layer={quote(layer, safe='')}")
    var = _current_active_var()
    if var:
        parts.append(f"var={quote(var, safe='')}")
    color = st.session_state.get("color_scheme")
    if color:
        parts.append(f"color={quote(color, safe='')}")
    return ("&" + "&".join(parts)) if parts else ""


def _render_cascade_menu(
    items: list,
    current_key: str | None = None,
    placeholder: str = "Select",
    current_label: str | None = None,
) -> None:
    """Render a single cascade dropdown as an st.html block.

    Args:
        items: top-level menu structure (see _build_*_cascade_items).
        current_key: currently selected variable key for this group
            (or None). Used to look up a label via the variable registry.
        placeholder: text shown on the trigger when nothing is selected.
        current_label: explicit trigger text (takes priority over the
            registry lookup). Needed for Geography since layer names
            aren't in the variable registry.
    """
    if current_label:
        trigger_label = current_label
        trigger_class = "cascade-current is-selected"
    elif current_key:
        all_vars = get_all_variables()
        if current_key in all_vars:
            trigger_label = (
                all_vars[current_key].get("dropdown_label")
                or all_vars[current_key].get("display_name", current_key)
            )
            trigger_class = "cascade-current is-selected"
        else:
            trigger_label = placeholder
            trigger_class = "cascade-current is-placeholder"
    else:
        trigger_label = placeholder
        trigger_class = "cascade-current is-placeholder"

    # Determine which leaf key counts as "currently selected" so we can
    # mark it with a persistent green dot. For Geography (current_label
    # only), the key we match is "layer:<active_layer>".
    if current_key:
        selected_match_key = current_key
    elif current_label:
        selected_match_key = f"layer:{current_label}"
    else:
        selected_match_key = None

    # Build the state-preservation suffix that every link carries. The
    # cascade uses <a href="?sel=..."> which triggers a full browser
    # navigation; Streamlit treats that as a refresh and clears session
    # state. So we must round-trip every piece of state we want kept
    # through the URL itself, not session state.
    preserved = _build_state_query_string()

    def render_items(items):
        parts = ['<ul class="cascade-menu">']
        for item in items:
            if "children" in item:
                parts.append(
                    '<li class="cascade-parent">'
                    f'<span class="cascade-label">{item["label"]}<span class="cascade-caret">▸</span></span>'
                    f'{render_items(item["children"])}'
                    '</li>'
                )
            else:
                # Plain anchor — st.html keeps href but strips onclick.
                # URL-encode the key so layer names like "State Boundary"
                # (with a space) and the "layer:" prefix's colon round-trip
                # cleanly through st.query_params.
                encoded = quote(item["key"], safe="")
                extra_cls = " cascade-leaf--selected" if item["key"] == selected_match_key else ""
                parts.append(
                    f'<li class="cascade-leaf{extra_cls}">'
                    f'<a href="?sel={encoded}{preserved}" target="_self">{item["label"]}</a>'
                    '</li>'
                )
        parts.append('</ul>')
        return ''.join(parts)

    html = f"""
    {_cascade_css()}
    <div class="cascade-root">
      <div class="cascade-trigger">
        <span class="{trigger_class}">{trigger_label}</span>
        <span class="cascade-trigger-caret">▾</span>
      </div>
      {render_items(items)}
    </div>
    """
    st.html(html)


def _apply_var_to_session_state(key: str) -> None:
    """Set the variable session-state slot for a given variable key,
    clearing the other two groups so mutual exclusivity holds. No-op if
    key isn't a known variable."""
    all_vars = get_all_variables()
    if key not in all_vars:
        return
    st.session_state["selected_variable"] = None
    st.session_state["selected_food_security_variable"] = None
    st.session_state["selected_housing_transportation_variable"] = None
    group = all_vars[key].get("dropdown_group")
    if group == "economic_security":
        st.session_state["selected_variable"] = key
    elif group == "food_security":
        st.session_state["selected_food_security_variable"] = key
    elif group == "housing_transportation":
        st.session_state["selected_housing_transportation_variable"] = key


def _route_cascade_click_from_url() -> None:
    """Process the URL params from a cascade click and write them to
    session state.

    Param shape (set by _render_cascade_menu's <a href> generation):
      * sel=<key>           — the clicked target. Either "layer:<Name>"
                              or a plain variable key.
      * layer=<Name>        — preserved Geography layer (state survival).
      * var=<key>           — preserved active variable (state survival).
      * color=<scheme>      — preserved color scheme (state survival).

    Apply order matters: first restore the preserved snapshot (layer/var/
    color), THEN apply the clicked sel — so the click overrides the
    snapshot but unrelated state stays put. Without the preservation
    pass, a navigation-driven session-state reset on Cloud Run would
    silently drop the user's geography or variable on every click.
    """
    qp = st.query_params
    if not any(k in qp for k in ("sel", "layer", "var", "color")):
        return

    # ── 1. Restore preserved state (snapshot from prior click) ────────
    if "layer" in qp:
        layer_name = qp["layer"]
        if layer_name in _GEOGRAPHY_LAYER_OPTIONS:
            st.session_state["active_layer"] = layer_name

    if "var" in qp:
        _apply_var_to_session_state(qp["var"])

    if "color" in qp:
        color = qp["color"]
        if color in _VALID_COLOR_SCHEMES:
            st.session_state["color_scheme"] = color

    # ── 2. Apply the actual click action (sel) ────────────────────────
    if "sel" in qp:
        raw = qp["sel"]

        if raw.startswith("layer:"):
            # Geography layer change: only set active_layer; the var
            # snapshot above already restored variable selections.
            layer_name = raw[len("layer:"):]
            if layer_name in _GEOGRAPHY_LAYER_OPTIONS:
                st.session_state["active_layer"] = layer_name
        else:
            # Variable change: replaces whatever var the snapshot restored.
            _apply_var_to_session_state(raw)

    # Drop the URL params so a refresh doesn't re-fire the click.
    st.query_params.clear()


def create_leaflet_map_view(debug_info: bool = False) -> None:
    """Create the Leaflet map view."""
    logger.debug("Building Leaflet map view")

    # Handle ?sel=<key> clicks from the Econ/Food cascade menus.
    # Must run BEFORE the reset-flag block so URL-driven selections
    # aren't clobbered by the reset mechanism.
    _route_cascade_click_from_url()

    # Initialize session state with comprehensive error handling
    try:
        # Ensure active_layer is set
        if 'active_layer' not in st.session_state:
            st.session_state['active_layer'] = 'State Boundary'
        
        # Valid variables loaded from centralized registry
        valid_variables = get_valid_variable_keys()
        
        # Ensure selected_variable is valid (None is allowed for mutual exclusivity)
        current_var = st.session_state.get('selected_variable', 'alice_rate')
        if current_var is not None and current_var not in valid_variables:
            logger.warning(f"Invalid variable '{current_var}' in session state, resetting to alice_rate")
            st.session_state['selected_variable'] = 'alice_rate'
        elif 'selected_variable' not in st.session_state:
            st.session_state['selected_variable'] = 'alice_rate'
            
        # Ensure color_scheme is set
        if 'color_scheme' not in st.session_state:
            st.session_state['color_scheme'] = 'blue'
            
        # Initialize food security variable (starts as None - no selection)
        if 'selected_food_security_variable' not in st.session_state:
            st.session_state['selected_food_security_variable'] = None
            
        # Initialize housing/transportation variable (starts as None - no selection)
        if 'selected_housing_transportation_variable' not in st.session_state:
            st.session_state['selected_housing_transportation_variable'] = None
            
    except Exception as e:
        logger.error(f"Error initializing session state: {e}")
        # Force reset to safe defaults
        st.session_state['active_layer'] = 'State Boundary'
        st.session_state['selected_variable'] = 'alice_rate'
        st.session_state['color_scheme'] = 'blue'
        
    # Apply pending dropdown resets BEFORE widgets are created.
    # Mapping from group name -> (widget key, state key for selected variable)
    _DROPDOWN_GROUPS = {
        'econ': ('variable_selector', 'selected_variable'),
        'food': ('food_security_selector', 'selected_food_security_variable'),
        'housing': ('housing_transportation_selector', 'selected_housing_transportation_variable'),
    }

    reset_flag = st.session_state.pop('_reset_other_dropdowns', None)
    if reset_flag in _DROPDOWN_GROUPS:
        # Clear all widget keys except the active group
        for name, (widget_key, _state_key) in _DROPDOWN_GROUPS.items():
            if name != reset_flag:
                st.session_state[widget_key] = None
    elif reset_flag == 'restore_econ':
        st.session_state['variable_selector'] = 'alice_rate'

    active_layer = st.session_state['active_layer']
    selected_variable = st.session_state['selected_variable']
    color_scheme = st.session_state['color_scheme']
    
    logger.info(f"Selected variable: {selected_variable}")
    logger.info(f"Active layer: {active_layer}")
    logger.info(f"Color scheme: {color_scheme}")
    
    # Map geo levels to their data loader equivalents
    geo_level_map = {
        'State Boundary': 'state',
        'Counties': 'county',
        'House Districts': 'house',
        'Senate Districts': 'senate'
    }
    geo_level = geo_level_map.get(active_layer, 'state')

    # Load GeoJSON and merge with statistical data (cached)
    geojson_data = _get_merged_geojson(active_layer, geo_level)

    if geojson_data is None:
        st.error(f"Failed to load GeoJSON data for {active_layer}")
        return
        
    # Dropdown scrolling fix (CSS styles are in app_style.css)
    st.markdown("""
    <script>
    // Enhanced fix for dropdown scrolling issues
    function fixDropdownScrolling() {
        // Find all dropdown containers
        const dropdowns = document.querySelectorAll('[data-baseweb="popover"] [role="listbox"]');
        
        dropdowns.forEach(dropdown => {
            // Force proper scrolling behavior
            dropdown.style.maxHeight = '350px';
            dropdown.style.overflowY = 'auto';
            dropdown.style.overflowX = 'hidden';
            dropdown.style.scrollBehavior = 'smooth';
            
            // Ensure proper container setup
            const container = dropdown.parentElement;
            if (container) {
                container.style.maxHeight = '350px';
                container.style.overflow = 'hidden';
            }
            
            // Fix individual options
            const options = dropdown.querySelectorAll('[role="option"]');
            options.forEach((option, index) => {
                option.style.minHeight = '42px';
                option.style.maxHeight = '42px';
                option.style.display = 'flex';
                option.style.alignItems = 'center';
                option.style.padding = '8px 12px';
                option.style.boxSizing = 'border-box';
                option.style.whiteSpace = 'nowrap';
                option.style.overflow = 'hidden';
                option.style.textOverflow = 'ellipsis';
                
                // Add hover scroll behavior
                option.addEventListener('mouseenter', function() {
                    this.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                });
            });
            
            // Add keyboard scroll support
            dropdown.addEventListener('keydown', function(e) {
                if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
                    setTimeout(() => {
                        const selected = dropdown.querySelector('[aria-selected="true"]');
                        if (selected) {
                            selected.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                        }
                    }, 10);
                }
            });
        });
    }
    
    // Enhanced observer for better detection
    let observer;
    
    function startObserver() {
        if (observer) observer.disconnect();
        
        observer = new MutationObserver(function(mutations) {
            let shouldFix = false;
            
            mutations.forEach(function(mutation) {
                if (mutation.addedNodes.length > 0) {
                    mutation.addedNodes.forEach(function(node) {
                        if (node.nodeType === 1) { // Element node
                            if (node.matches && node.matches('[data-baseweb="popover"]')) {
                                shouldFix = true;
                            } else if (node.querySelector && node.querySelector('[data-baseweb="popover"]')) {
                                shouldFix = true;
                            }
                        }
                    });
                }
            });
            
            if (shouldFix) {
                setTimeout(fixDropdownScrolling, 50);
                setTimeout(fixDropdownScrolling, 200);
            }
        });
        
        observer.observe(document.body, {
            childList: true,
            subtree: true,
            attributes: false
        });
    }
    
    // Initialize
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
            startObserver();
            setTimeout(fixDropdownScrolling, 100);
        });
    } else {
        startObserver();
        setTimeout(fixDropdownScrolling, 100);
    }
    
    // Also fix on window events
    window.addEventListener('resize', function() {
        setTimeout(fixDropdownScrolling, 100);
    });
    
    // Periodic check for stubborn cases
    setInterval(fixDropdownScrolling, 2000);
    </script>
    """, unsafe_allow_html=True)
    
    # Create dropdown controls in main content area
    col1, col2, col3, col4 = st.columns([1, 1, 1, 1])

    with col1:
        # Geography cascade — flat list of layer names. Keys carry a
        # "layer:" prefix so _route_cascade_click_from_url can distinguish
        # them from variable keys. See _build_geography_cascade_items.
        st.markdown('<div style="color: #2a5a0c; font-family: Inter, sans-serif; font-size: 0.7em; font-weight: 600; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 12px; padding-bottom: 6px; border-bottom: 2px solid transparent; visibility: hidden;">CHOOSE YOUR VARIABLE</div>'
                   '<div style="padding-bottom: 18px;"><span style="display: inline-block; background: #6a9a50; color: white; font-family: Inter, sans-serif; font-weight: 600; font-size: 0.78em; padding: 3px 10px; border-radius: 4px; letter-spacing: 0.03em;">Geography</span></div>', unsafe_allow_html=True)

        _render_cascade_menu(
            items=_build_geography_cascade_items(),
            current_label=active_layer if active_layer in _GEOGRAPHY_LAYER_OPTIONS else None,
            placeholder="Select Geography",
        )
    
    with col2:
        # Economic Security cascade menu — CTC + EITC collapsed under
        # "Tax Credits" submenu. See _build_econ_cascade_items for the
        # grouping rule and _route_cascade_click_from_url for the
        # click round-trip.
        st.markdown('<div style="color: #2a5a0c; font-family: Inter, sans-serif; font-size: 0.7em; font-weight: 600; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 12px; padding-bottom: 6px; border-bottom: 2px solid #c8e6b0;">Choose your variable</div>'
                   '<div style="padding-bottom: 18px;"><span style="display: inline-block; background: transparent; color: #2a5a0c; font-family: Inter, sans-serif; font-weight: 600; font-size: 0.78em; padding: 3px 10px; border-radius: 4px; border: 1.5px solid #b8d4a0; letter-spacing: 0.03em;">Economic Security</span></div>', unsafe_allow_html=True)

        _render_cascade_menu(
            items=_build_econ_cascade_items(),
            current_key=st.session_state.get('selected_variable'),
            placeholder="Select Variable",
        )
    
    with col3:
        # Food Security cascade menu — SNAP and CEP each collapse into
        # their own submenu. See _build_food_cascade_items.
        st.markdown('<div style="color: #2a5a0c; font-family: Inter, sans-serif; font-size: 0.7em; font-weight: 600; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 12px; padding-bottom: 6px; border-bottom: 2px solid transparent; visibility: hidden;">CHOOSE YOUR VARIABLE</div>'
                   '<div style="padding-bottom: 18px;"><span style="display: inline-block; background: transparent; color: #2a5a0c; font-family: Inter, sans-serif; font-weight: 600; font-size: 0.78em; padding: 3px 10px; border-radius: 4px; border: 1.5px solid #b8d4a0; letter-spacing: 0.03em;">Food Security</span></div>', unsafe_allow_html=True)

        _render_cascade_menu(
            items=_build_food_cascade_items(),
            current_key=st.session_state.get('selected_food_security_variable'),
            placeholder="Select Variable",
        )
    
    with col4:
        # Housing & Transportation cascade — flat list (no submenus
        # since there's no natural sub-grouping). Router handles
        # mutual exclusivity with Econ/Food the same way as before.
        st.markdown('<div style="color: #2a5a0c; font-family: Inter, sans-serif; font-size: 0.7em; font-weight: 600; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 12px; padding-bottom: 6px; border-bottom: 2px solid transparent; visibility: hidden;">CHOOSE YOUR VARIABLE</div>'
                   '<div style="padding-bottom: 18px;"><span style="display: inline-block; background: transparent; color: #2a5a0c; font-family: Inter, sans-serif; font-weight: 600; font-size: 0.78em; padding: 3px 10px; border-radius: 4px; border: 1.5px solid #b8d4a0; letter-spacing: 0.03em;">Housing &amp; Transportation</span></div>', unsafe_allow_html=True)

        _render_cascade_menu(
            items=_build_housing_cascade_items(),
            current_key=st.session_state.get('selected_housing_transportation_variable'),
            placeholder="Select Variable",
        )
    
    # Display names from centralized registry
    variable_display_names = get_display_names(long=True)
    
    # Determine which variable to use for the map
    food_security_var = st.session_state.get('selected_food_security_variable')
    housing_transportation_var = st.session_state.get('selected_housing_transportation_variable')
    data_var = st.session_state.get('selected_variable')
    
    # Use food security variable if selected, otherwise housing/transportation, otherwise data variable
    if food_security_var is not None:
        map_variable = food_security_var
    elif housing_transportation_var is not None:
        map_variable = housing_transportation_var
    elif data_var is not None:
        map_variable = data_var
    else:
        # Default to alice_rate if nothing is selected, but don't update session state to avoid loops
        map_variable = 'alice_rate'
    
    # Create the map with built-in JavaScript info panel
    create_leaflet_map(
        geojson_data=geojson_data,
        selected_variable=map_variable,
        variable_display_name=variable_display_names.get(map_variable, map_variable.replace('_', ' ').title()),
        color_scheme=color_scheme,
        active_layer=active_layer,
        map_height=500,
        key=f"map-{active_layer}-{map_variable}-{color_scheme}",
        show_side_panel=True  # Enable the JavaScript panel as a popup-style panel
    )

    # Source attribution for the currently-selected variable. Auto-updates
    # when the variable or the data year in data_sources.json changes, so
    # users always see the right vintage for the number they're looking at.
    source_label = get_variable_source(map_variable)
    if source_label:
        st.markdown(
            '<div style="font-size: 0.75rem; color: #6b8f71; margin-top: -4px; '
            'padding: 4px 2px 12px; font-family: Inter, sans-serif; letter-spacing: 0.01em;">'
            f'<span style="font-weight: 600; color: #4a7a54;">Source:</span> {source_label}'
            '</div>',
            unsafe_allow_html=True,
        )

def create_info_panel(selected_variable, geojson_data):
    """Create the static info panel that shows selected geography details."""
    st.markdown("### Geographic Info")
    
    # Initialize session state for selected geography if not exists
    if 'selected_geography' not in st.session_state:
        st.session_state.selected_geography = None
    
    # No need for additional JavaScript communication since we're using proper component return values
    
    # Display names from centralized registry
    variable_display_names = get_display_names(long=True)
    
    # Display selected variable
    if selected_variable:
        var_name = variable_display_names.get(selected_variable, selected_variable.replace('_', ' ').title())
        st.markdown(f"**Selected Variable:** {var_name}")
    else:
        st.markdown("**Selected Variable:** No variable selected")
    
    st.markdown("---")
    
    # Display selected geography info
    if st.session_state.selected_geography:
        geo_info = st.session_state.selected_geography
        st.markdown(f"**{geo_info.get('name', 'Unknown')}**")
        
        # Show selected variable prominently
        if selected_variable and selected_variable in geo_info:
            value = geo_info[selected_variable]
            var_name = variable_display_names.get(selected_variable, selected_variable.replace('_', ' ').title())
            
            if isinstance(value, (int, float)):
                if selected_variable.endswith('_pct') or selected_variable.endswith('_rate'):
                    formatted_value = f"{value:.1f}%"
                elif 'income' in selected_variable or 'amount' in selected_variable:
                    formatted_value = f"${value:,.0f}"
                elif 'minutes' in selected_variable:
                    formatted_value = f"{value:.1f} minutes"
                else:
                    formatted_value = f"{value:,.0f}"
            else:
                formatted_value = str(value)
            
            st.markdown(f"<div style='background: #1a73e8; color: white; padding: 8px; border-radius: 4px; text-align: center; margin: 10px 0;'><strong>{var_name}: {formatted_value}</strong></div>", unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Key Metrics Section
        st.markdown("**Key Metrics**")
        key_metrics = [
            ('poverty_rate', 'Poverty Rate', 'percentage'),
            ('median_income', 'Median Income', 'currency'),
            ('unemployment_rate', 'Unemployment Rate', 'percentage'),
            ('population', 'Population', 'number')
        ]
        
        for metric_key, metric_label, metric_type in key_metrics:
            if metric_key in geo_info:
                value = geo_info[metric_key]
                if isinstance(value, (int, float)):
                    is_selected = metric_key == selected_variable
                    style = "background: #e8f0fe; border: 1px solid #1a73e8; font-weight: bold;" if is_selected else "background: #f8f9fa; border: 1px solid #e0e0e0;"
                    
                    if metric_type == 'percentage':
                        formatted = f"{value:.1f}%"
                    elif metric_type == 'currency':
                        formatted = f"${value:,.0f}"
                    else:
                        formatted = f"{value:,.0f}"
                    
                    st.markdown(f"<div style='{style} padding: 4px 6px; margin: 2px 0; border-radius: 3px; line-height: 1.2;'><div style='font-size: 10px; color: #666;'>{metric_label}</div><div style='font-size: 12px; color: #333;'>{formatted}</div></div>", unsafe_allow_html=True)
        
        st.markdown("---")
        
        # SNAP Section
        st.markdown("**SNAP**")
        snap_metrics = [
            ('snap_household_rate', 'SNAP Households', 'percentage'),
            ('snap_benefit_annual_per_household', 'Avg Annual Benefit', 'currency'),
            ('snap_benefits_annual_total', 'Total Annual Benefits', 'currency')
        ]
        
        for metric_key, metric_label, metric_type in snap_metrics:
            if metric_key in geo_info:
                value = geo_info[metric_key]
                if isinstance(value, (int, float)):
                    is_selected = metric_key == selected_variable
                    style = "background: #e8f0fe; border: 1px solid #1a73e8; font-weight: bold;" if is_selected else "background: #f8f9fa; border: 1px solid #e0e0e0;"
                    
                    if metric_type == 'percentage':
                        formatted = f"{value:.1f}%"
                    elif metric_type == 'currency':
                        formatted = f"${value:,.0f}"
                    else:
                        formatted = f"{value:,.0f}"
                    
                    st.markdown(f"<div style='{style} padding: 4px 6px; margin: 2px 0; border-radius: 3px; line-height: 1.2;'><div style='font-size: 10px; color: #666;'>{metric_label}</div><div style='font-size: 12px; color: #333;'>{formatted}</div></div>", unsafe_allow_html=True)
        
        # CEP Section
        st.markdown("**CEP Schools**")
        cep_metrics = [
            ('cep_percentage', 'Schools with CEP', 'percentage'),
            ('cep_display', 'CEP Schools', 'text')
        ]
        
        for metric_key, metric_label, metric_type in cep_metrics:
            if metric_key in geo_info:
                value = geo_info[metric_key]
                # Handle both numeric and text values
                if isinstance(value, (int, float)) or (isinstance(value, str) and value):
                    is_selected = metric_key == selected_variable
                    style = "background: #e8f0fe; border: 1px solid #1a73e8; font-weight: bold;" if is_selected else "background: #f8f9fa; border: 1px solid #e0e0e0;"
                    
                    if metric_type == 'percentage' and isinstance(value, (int, float)):
                        formatted = f"{value:.1f}%"
                    elif metric_type == 'currency' and isinstance(value, (int, float)):
                        formatted = f"${value:,.0f}"
                    elif metric_type == 'text':
                        formatted = str(value)
                    else:
                        formatted = f"{value:,.0f}" if isinstance(value, (int, float)) else str(value)
                    
                    st.markdown(f"<div style='{style} padding: 4px 6px; margin: 2px 0; border-radius: 3px; line-height: 1.2;'><div style='font-size: 10px; color: #666;'>{metric_label}</div><div style='font-size: 12px; color: #333;'>{formatted}</div></div>", unsafe_allow_html=True)
        
        st.markdown("---")
        
        # View Detailed Data Button
        if 'unique_id' in geo_info and geo_info['unique_id']:
            geo_id = geo_info['unique_id']
            detail_url = f"/geo_detail?geo_id={geo_id}"
            st.markdown(f"<div style='text-align: center; margin-top: 12px;'><a href='{detail_url}' target='_blank' style='display: inline-block; background-color: #3a7710; color: white; padding: 8px 16px; border-radius: 4px; text-decoration: none; font-weight: bold;'>View Detailed Data</a></div>", unsafe_allow_html=True)
        else:
            st.markdown("<div style='text-align: center; margin-top: 12px;'><span style='display: inline-block; background-color: #ccc; color: #666; padding: 8px 16px; border-radius: 4px; font-style: italic;'>Detailed data unavailable</span></div>", unsafe_allow_html=True)
    else:
        st.markdown("**Location:** Click on the map to select a location")
        st.markdown("**Value:** No location selected")

def prepare_feature_details(feature_id, geojson_data):
    """Prepare the feature details data for display.
    
    Args:
        feature_id: The ID of the feature to display details for.
        geojson_data: The GeoJSON data containing the feature.
        
    Returns:
        A dictionary containing the formatted feature details or None if the feature is not found.
    """
    # Find the feature in the GeoJSON data
    selected_feature = None
    for feature in geojson_data['features']:
        if feature['properties'].get('id') == feature_id:
            selected_feature = feature
            break
    
    if not selected_feature:
        return None
    
    # Get properties
    properties = selected_feature['properties']
    
    # Format display values
    feature_name = properties.get('name', properties.get('NAME', feature_id))
    
    # Format numeric values
    def format_number(value, prefix='', suffix=''):
        if isinstance(value, (int, float)):
            return f"{prefix}{value:,}{suffix}"
        return f"{prefix}{value}{suffix}"
    
    # Prepare data for each tab
    demographics = {
        "Population": format_number(properties.get('population', 'N/A')),
        "White Alone (%)": format_number(properties.get('white_alone_pct', 'N/A'), suffix='%'),
        "Asian Alone (%)": format_number(properties.get('asian_alone_pct', 'N/A'), suffix='%'),
        "Native Hawaiian/PI (%)": format_number(properties.get('native_hawaiian_pi_pct', 'N/A'), suffix='%')
    }
    
    economic = {
        "Poverty Rate": format_number(properties.get('poverty_rate', 'N/A'), suffix='%'),
        "Median Income": format_number(properties.get('median_income', 'N/A'), prefix='$'),
        "Unemployment Rate": format_number(properties.get('unemployment_rate', 'N/A'), suffix='%'),
        "ALICE Households": format_number(properties.get('alice_rate', 'N/A'), suffix='%')
    }
    
    # SNAP and CEP data section
    snap_data = {
        "SNAP Households": format_number(properties.get('snap_household_rate', 'N/A'), suffix='%'),
        "Avg Annual SNAP Benefit": format_number(properties.get('snap_benefit_annual_per_household', 'N/A'), prefix='$'),
        "Total Annual SNAP Benefits": format_number(properties.get('snap_benefits_annual_total', 'N/A'), prefix='$'),
        "Schools with CEP": format_number(properties.get('cep_percentage', 'N/A'), suffix='%'),
        "Number of CEP Schools": properties.get('cep_display', 'N/A')
    }
    
    housing = {
        "Median Home Value": format_number(properties.get('median_home_value', 'N/A'), prefix='$'),
        "Homeownership Rate": format_number(properties.get('homeownership_rate', 'N/A'), suffix='%'),
        "Rent Burden (%)": format_number(properties.get('rent_burden_pct', 'N/A'), suffix='%'),
        "Median Rent": format_number(properties.get('median_rent', 'N/A'), prefix='$')
    }
    
    education_health = {
        "College Educated (%)": format_number(properties.get('college_educated_pct', 'N/A'), suffix='%'),
        "High School Graduate (%)": format_number(properties.get('high_school_grad_pct', 'N/A'), suffix='%'),
        "Health Insurance Coverage (%)": format_number(properties.get('health_insurance_pct', 'N/A'), suffix='%'),
        "Disability (%)": format_number(properties.get('disability_pct', 'N/A'), suffix='%')
    }
    
    return {
        "name": feature_name,
        "demographics": demographics,
        "economic": economic,
        "snap": snap_data,
        "housing": housing,
        "education_health": education_health
    }


def display_feature_details(feature_id, geojson_data, selected_variable):
    """Display detailed information for the selected feature."""
    # Prepare the data
    details = prepare_feature_details(feature_id, geojson_data)
    
    if not details:
        return
    
    # Create a feature detail card
    st.markdown("### Feature Details")
    
    with st.container():
        st.markdown(f"#### {details['name']}")
        
        # Create tabs for different categories of data
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["Key Metrics", "SNAP", "Demographics", "Housing", "Education & Health"])
        
        with tab1:
            # Key Metrics tab (Economic data)
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Poverty Rate", details['economic']['Poverty Rate'])
                st.metric("Median Income", details['economic']['Median Income'])
            with col2:
                st.metric("Unemployment Rate", details['economic']['Unemployment Rate'])
                st.metric("ALICE Households", details['economic']['ALICE Households'])
        
        with tab2:
            # SNAP and CEP tab
            col1, col2 = st.columns(2)
            with col1:
                st.metric("SNAP Households", details['snap']['SNAP Households'])
                st.metric("Avg Annual SNAP Benefit", details['snap']['Avg Annual SNAP Benefit'])
                st.metric("Schools with CEP", details['snap']['Schools with CEP'])
            with col2:
                st.metric("Total Annual SNAP Benefits", details['snap']['Total Annual SNAP Benefits'])
                st.metric("Number of CEP Schools", details['snap']['Number of CEP Schools'])
                st.markdown("<div style='height: 38px;'></div>", unsafe_allow_html=True)  # Spacer for alignment
        
        with tab3:
            # Demographics tab
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Population", details['demographics']['Population'])
                st.metric("White Alone (%)", details['demographics']['White Alone (%)'])
            with col2:
                st.metric("Asian Alone (%)", details['demographics']['Asian Alone (%)'])
                st.metric("Native Hawaiian/PI (%)", details['demographics']['Native Hawaiian/PI (%)'])
        
        with tab4:
            # Housing tab
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Median Home Value", details['housing']['Median Home Value'])
                st.metric("Homeownership Rate", details['housing']['Homeownership Rate'])
            with col2:
                st.metric("Rent Burden (%)", details['housing']['Rent Burden (%)'])
                st.metric("Median Rent", details['housing']['Median Rent'])
        
        with tab5:
            # Education & Health tab
            col1, col2 = st.columns(2)
            with col1:
                st.metric("College Educated (%)", details['education_health']['College Educated (%)'])
                st.metric("High School Graduate (%)", details['education_health']['High School Graduate (%)'])
            with col2:
                st.metric("Health Insurance Coverage (%)", details['education_health']['Health Insurance Coverage (%)'])
                st.metric("Disability (%)", details['education_health']['Disability (%)'])

# This function is a duplicate and has been removed

def create_data_summary():
    """Create a summary of the data with a bar chart comparison."""

    # ── Styles scoped to the data analysis section ──────────────────────────
    st.markdown("""
    <style>
        /* Hide Streamlit's fullscreen expand button on plotly charts only */
        [data-testid="stPlotlyChart"] [data-testid="StyledFullScreenButton"] {
            display: none !important;
        }
        /* Section label above chart / table panels */
        .da-section-label {
            font-size: 0.7rem;
            font-weight: 700;
            letter-spacing: 0.1em;
            text-transform: uppercase;
            color: #6b8f71;
            margin: 0 0 0.6rem 0;
            padding: 0;
        }
        /* Thin divider between chart row and full table */
        .da-divider {
            border: none;
            border-top: 1px solid #e2e8e3;
            margin: 1.5rem 0 1.25rem 0;
        }
        /* Geo context pill shown above the chart */
        .da-geo-pill {
            display: inline-block;
            background: #eef4ef;
            color: #3d6b45;
            font-size: 0.72rem;
            font-weight: 600;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            padding: 0.2rem 0.65rem;
            border-radius: 99px;
            margin-bottom: 0.5rem;
        }
        /* Download button row */
        .da-download-row {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            margin-top: 0.75rem;
        }
        .da-row-count {
            font-size: 0.75rem;
            color: #8fa899;
        }
    </style>
    """, unsafe_allow_html=True)

    # ── Resolve selected variable ────────────────────────────────────────────
    active_layer = st.session_state.get('active_layer', 'State Boundary')
    food_security_var = st.session_state.get('selected_food_security_variable')
    housing_transportation_var = st.session_state.get('selected_housing_transportation_variable')
    data_var = st.session_state.get('selected_variable')
    if food_security_var is not None:
        selected_variable = food_security_var
    elif housing_transportation_var is not None:
        selected_variable = housing_transportation_var
    elif data_var is not None:
        selected_variable = data_var
    else:
        selected_variable = 'alice_rate'

    # ── Load data ────────────────────────────────────────────────────────────
    data_loader = get_data_loader()
    geo_level_map = {
        'State Boundary': 'state',
        'Counties': 'county',
        'House Districts': 'house',
        'Senate Districts': 'senate',
    }
    geo_level = geo_level_map.get(active_layer, 'state')
    data = data_loader.get_data(geo_level)

    # Ensure name column
    if data is not None and 'name' not in data.columns:
        if 'NAME' in data.columns:
            data['name'] = data['NAME']
        elif 'geoid' in data.columns:
            data['name'] = 'Area ' + data['geoid'].astype(str)
        elif 'district' in data.columns:
            data['name'] = 'District ' + data['district'].astype(str)

    if data is None or data.empty:
        st.warning(f"No data available for {active_layer}")
        return

    # Get both short and long display names (long includes units)
    import re
    var_label_short = get_display_name(selected_variable, long=False)
    var_label_long = get_display_name(selected_variable, long=True)

    # Parse unit from long name (format: "Name (Unit)")
    unit_match = re.search(r'\(([^)]+)\)', var_label_long)
    unit = unit_match.group(1) if unit_match else ''

    # Chart title: "Percentage of X (GeoLevel)" for %, else "X (GeoLevel)"
    if unit == '%':
        chart_title = f"Percentage of {var_label_short} ({active_layer})"
    else:
        chart_title = f"{var_label_long} ({active_layer})"

    # ── Plotly chart config — remove autoscale, reset axes, and Plotly logo ─
    _chart_config = {
        'modeBarButtonsToRemove': ['autoScale2d', 'resetScale2d'],
        'displaylogo': False,
        'toImageButtonOptions': {'filename': f'hawaii_{geo_level}_{selected_variable}'},
    }

    # ── Chart + side table row ───────────────────────────────────────────────
    chart_col, table_col = st.columns([11, 5])

    with chart_col:
        st.markdown(f'<p class="da-geo-pill">{active_layer}</p>', unsafe_allow_html=True)
        source = get_variable_source(selected_variable)
        source_icon = f' <span title="Source: {source}" style="cursor:help;color:#999;font-style:normal">\u24D8</span>' if source else ''
        st.markdown(f'<p class="da-section-label">{var_label_short} — ranked comparison{source_icon}</p>', unsafe_allow_html=True)

        if selected_variable in data.columns:
            sorted_data = data.sort_values(by=selected_variable, ascending=False)
            num_items = len(sorted_data)

            bar_color = '#4a8c64'

            # Hover + bar-label formats. For currency, round to nearest
            # dollar (otherwise raw floats like 1039.2409 leak through);
            # for percent, one decimal; everything else, default.
            if unit == '$':
                hover_value_fmt = '$%{y:,.0f}'
                text_template = '$%{text:,.0f}'
            elif unit == '%':
                hover_value_fmt = '%{y:.1f}%'
                text_template = '%{text:.1f}%'
            else:
                hover_value_fmt = '%{y}'
                text_template = '%{text:.1f}'

            hover_template = (
                f"<b>%{{x}}</b><br>"
                f"{var_label_short}: {hover_value_fmt}<br>"
                f"<extra></extra>"
            )

            fig = px.bar(
                sorted_data,
                x='name',
                y=selected_variable,
                text=selected_variable,
                color_discrete_sequence=[bar_color],
                labels={'name': '', selected_variable: var_label_short},
            )
            fig.update_traces(
                texttemplate=text_template,
                textposition='outside',
                textfont=dict(size=9, color='#555'),
                cliponaxis=False,
                hovertemplate=hover_template,
                hoverlabel=dict(bgcolor='white', bordercolor='#ccc', font_size=12, font_family='Inter, Arial'),
            )
            common_layout = dict(
                title=dict(
                    text=chart_title,
                    x=0.5,
                    xanchor='center',
                    font=dict(size=13, color='#333', family='Inter, Arial'),
                ),
                height=400,
                showlegend=False,
                plot_bgcolor='white',
                paper_bgcolor='white',
                font=dict(family='Inter, Arial', size=12, color='#333'),
                yaxis=dict(
                    gridcolor='#eef0ec',
                    gridwidth=1,
                    zeroline=False,
                    title_text=var_label_long,
                    title_font=dict(size=11, color='#666'),
                    tickfont=dict(size=10),
                    # Match the rounding used by hover/text labels so the
                    # axis doesn't show fractional dollars while the bar
                    # tops show whole dollars.
                    tickformat=('$,d' if unit == '$' else (None if unit == '%' else None)),
                ),
                xaxis=dict(title_text='', showgrid=False),
                margin=dict(l=55, r=20, t=50, b=60 if num_items <= 10 else 28),
                hoverlabel=dict(bgcolor='white'),
                uniformtext=dict(minsize=7, mode='hide'),
            )
            if num_items > 10:
                fig.update_xaxes(showticklabels=False)
                common_layout['margin']['b'] = 28
            else:
                fig.update_xaxes(tickangle=-40, tickfont=dict(size=10))
            fig.update_layout(**common_layout)

            # Add state average reference line for county/district charts
            if geo_level != 'state':
                state_data = data_loader.get_data('state')
                if state_data is not None and selected_variable in state_data.columns:
                    state_val = state_data[selected_variable].iloc[0]
                    if pd.notna(state_val):
                        # Format label based on unit
                        if unit == '%':
                            avg_label = f"State: {state_val:.1f}%"
                        elif unit == '$':
                            avg_label = f"State: ${state_val:,.0f}"
                        else:
                            avg_label = f"State: {state_val:.1f}"
                        fig.add_hline(
                            y=state_val,
                            line_dash="dot",
                            line_color="#e74c3c",
                            annotation_text=avg_label,
                            annotation_position="top right",
                            annotation_font_size=10,
                            annotation_font_color="#e74c3c",
                        )

            st.plotly_chart(fig, use_container_width=True, config=_chart_config)
            if num_items > 10:
                st.caption(f"Showing all {num_items} {active_layer.lower()} ranked by {var_label_short}. Hover for details.")
        else:
            st.warning(f"Variable '{selected_variable}' is not available for this geography level.")

    with table_col:
        st.markdown('<p class="da-section-label" style="margin-top:2.3rem">Selected variable</p>', unsafe_allow_html=True)
        display_cols = [c for c in ['name', selected_variable] if c in data.columns]
        # Format matches unit: dollars get rounded ($1,039), percents one
        # decimal (12.5), everything else one decimal as before.
        if unit == '$':
            value_format = '$%d'
        elif unit == '%':
            value_format = '%.1f%%'
        else:
            value_format = '%.1f'
        st.dataframe(
            data[display_cols],
            height=400,
            use_container_width=True,
            column_config={
                'name': st.column_config.TextColumn('Area'),
                selected_variable: st.column_config.NumberColumn(var_label_long, format=value_format),
            },
        )

    # ── Full data table ──────────────────────────────────────────────────────
    st.markdown('<hr class="da-divider">', unsafe_allow_html=True)
    st.markdown('<p class="da-section-label">Full data table</p>', unsafe_allow_html=True)

    # Set medium column widths so the table overflows horizontally and shows a scrollbar
    full_col_config = {col: st.column_config.Column(width='medium') for col in data.columns}
    st.dataframe(
        data,
        height=420,
        use_container_width=True,
        column_config=full_col_config,
    )

    # ── Download ─────────────────────────────────────────────────────────────
    csv = data.to_csv(index=False)
    col_dl, col_info = st.columns([2, 8])
    with col_dl:
        st.download_button(
            label="⬇ Download CSV",
            data=csv,
            file_name=f"hawaii_{geo_level}_data.csv",
            mime="text/csv",
            key="data_summary_download_button",
            use_container_width=True,
        )
    with col_info:
        st.markdown(
            f'<p class="da-row-count" style="padding-top:0.6rem">'
            f'{len(data):,} rows · {len(data.columns):,} columns · {active_layer}</p>',
            unsafe_allow_html=True,
        )
