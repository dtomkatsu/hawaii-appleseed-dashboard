"""
Centralized variable registry for the Hawaii Appleseed Dashboard.

All variable definitions live in variables.json. This module loads that file
once and provides accessor functions used by the UI and data layers.
"""

import json
import os
from functools import lru_cache
from typing import Dict, List, Optional, Any


_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "variables.json")


@lru_cache(maxsize=1)
def _load_config() -> dict:
    with open(_CONFIG_PATH, "r") as f:
        return json.load(f)


def get_all_variables() -> Dict[str, dict]:
    """Return the full variables dict from config."""
    return _load_config()["variables"]


# ---------------------------------------------------------------------------
# Valid variable keys
# ---------------------------------------------------------------------------

def get_valid_variable_keys() -> List[str]:
    """All variable keys known to the dashboard (replaces valid_variables list)."""
    return list(get_all_variables().keys())


def get_special_variable_keys() -> List[str]:
    """Variables that are merged from separate data sources."""
    return [k for k, v in get_all_variables().items() if v.get("is_special_variable")]


# ---------------------------------------------------------------------------
# DEFAULT_METRICS — ordered list of {key, label, type} for the info panel
# ---------------------------------------------------------------------------

def get_default_metrics() -> List[dict]:
    """Return the DEFAULT_METRICS list (replaces the hardcoded list in leaflet_component.py)."""
    variables = get_all_variables()
    metrics = []
    for key, v in variables.items():
        if v.get("show_in_default_metrics"):
            metrics.append({
                "key": key,
                "label": v["display_name"],
                "type": v["data_type"],
            })
    return metrics


# ---------------------------------------------------------------------------
# Display-name mappings
# ---------------------------------------------------------------------------

def get_display_names(long: bool = False) -> Dict[str, str]:
    """
    Map of variable_key -> display name.
    If long=True, uses display_name_long (includes units).
    Replaces both variable_display_names dicts in leaflet_map_view.py.
    """
    field = "display_name_long" if long else "display_name"
    return {k: v[field] for k, v in get_all_variables().items()}


def get_display_name(key: str, long: bool = False) -> str:
    """Display name for a single variable, with fallback."""
    names = get_display_names(long=long)
    return names.get(key, key.replace("_", " ").title())


# ---------------------------------------------------------------------------
# Dropdown helpers
# ---------------------------------------------------------------------------

def get_dropdown_groups() -> Dict[str, dict]:
    """Return dropdown group definitions, sorted by order."""
    groups = _load_config()["dropdown_groups"]
    return dict(sorted(groups.items(), key=lambda x: x[1]["order"]))


def get_variables_for_dropdown(group: str) -> List[dict]:
    """
    Return sorted list of {key, label} for a given dropdown group.
    Replaces the hardcoded st.selectbox option lists in leaflet_map_view.py.
    """
    variables = get_all_variables()
    items = []
    for key, v in variables.items():
        if v.get("show_in_dropdown") and v.get("dropdown_group") == group:
            items.append({
                "key": key,
                "label": v["dropdown_label"],
                "order": v.get("dropdown_order", 999),
            })
    items.sort(key=lambda x: x["order"])
    return [{"key": i["key"], "label": i["label"]} for i in items]


# ---------------------------------------------------------------------------
# Info-panel categories (injected as JSON into JS iframe template)
# ---------------------------------------------------------------------------

def get_info_panel_categories() -> Dict[str, List[dict]]:
    """
    Return info-panel categories as {category_name: [{key, label, type}, ...]}.
    Sorted by category order, then by variable info_panel_order within each.
    """
    cat_order = _load_config()["info_panel_categories"]
    variables = get_all_variables()

    categories: Dict[str, List[dict]] = {}
    for key, v in variables.items():
        cat = v.get("info_panel_category")
        if not cat or not v.get("show_in_info_panel"):
            continue
        categories.setdefault(cat, []).append({
            "key": key,
            "label": v["info_panel_label"],
            "type": v["data_type"],
            "_order": v.get("info_panel_order", 999),
        })

    # Sort variables within each category
    for cat in categories:
        categories[cat].sort(key=lambda x: x["_order"])
        for item in categories[cat]:
            del item["_order"]

    # Sort categories by their defined order
    sorted_cats = {}
    for cat_name in sorted(categories.keys(), key=lambda c: cat_order.get(c, {}).get("order", 999)):
        sorted_cats[cat_name] = categories[cat_name]
    return sorted_cats


def get_info_panel_categories_json() -> str:
    """JSON string ready for injection into JS template (no f-string brace escaping needed)."""
    return json.dumps(get_info_panel_categories())


# ---------------------------------------------------------------------------
# Color thresholds (injected as JSON into JS iframe template)
# ---------------------------------------------------------------------------

def get_color_thresholds() -> Dict[str, List]:
    """Map of variable_key -> threshold array for getColorForValue()."""
    variables = get_all_variables()
    return {k: v["color_thresholds"] for k, v in variables.items() if v.get("color_thresholds")}


def get_color_thresholds_json() -> str:
    """JSON string ready for injection into JS template."""
    return json.dumps(get_color_thresholds())


def get_default_color_thresholds() -> List:
    """Fallback thresholds when a variable has no explicit thresholds."""
    return _load_config()["default_color_thresholds"]


def get_default_color_thresholds_json() -> str:
    return json.dumps(get_default_color_thresholds())


# ---------------------------------------------------------------------------
# Legend direction + display names (injected into JS for legend indicator)
# ---------------------------------------------------------------------------

def get_legend_meta() -> Dict[str, dict]:
    """Map of variable_key -> {direction, display_name_long} for JS legend."""
    variables = get_all_variables()
    return {
        k: {
            "direction": v.get("legend_direction", "neutral"),
            "label": v.get("display_name_long", v.get("display_name", k)),
        }
        for k, v in variables.items()
    }


def get_legend_meta_json() -> str:
    """JSON string ready for injection into JS template."""
    return json.dumps(get_legend_meta())


# ---------------------------------------------------------------------------
# Data source (for tooltip display)
# ---------------------------------------------------------------------------

def get_variable_source(key: str) -> str:
    """Return the data source string for a variable, or empty string."""
    return get_all_variables().get(key, {}).get("source", "")


# ---------------------------------------------------------------------------
# Fact-sheet helpers
# ---------------------------------------------------------------------------

def get_fact_sheet_categories() -> Dict[str, dict]:
    """Return fact-sheet tab definitions sorted by order."""
    cats = _load_config()["fact_sheet_categories"]
    return dict(sorted(cats.items(), key=lambda x: x[1]["order"]))


def get_fact_sheet_variables(category_key: str) -> List[dict]:
    """Variables shown in a given fact-sheet tab, sorted by fact_sheet_label."""
    variables = get_all_variables()
    items = []
    for key, v in variables.items():
        if v.get("show_in_fact_sheet") and v.get("fact_sheet_category") == category_key:
            items.append({
                "key": key,
                "label": v["fact_sheet_label"],
                "data_type": v["data_type"],
            })
    return items


# ---------------------------------------------------------------------------
# Available-variables dict (replaces _get_available_variables in data_loader)
# ---------------------------------------------------------------------------

def get_available_variables() -> Dict[str, str]:
    """Map of variable_key -> long display name (replaces data_loader._get_available_variables)."""
    return get_display_names(long=True)
