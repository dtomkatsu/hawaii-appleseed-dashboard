"""
Centralized theme registry for the Hawaii Appleseed Dashboard.

All theme values (colors, fonts, layout, map config, color schemes) live in
theme.json. This module loads that file once and provides accessor functions.
"""

import json
import os
from functools import lru_cache
from typing import Dict, List, Any


_THEME_PATH = os.path.join(os.path.dirname(__file__), "theme.json")


@lru_cache(maxsize=1)
def _load_theme() -> dict:
    with open(_THEME_PATH, "r") as f:
        return json.load(f)


def get_theme() -> dict:
    """Return the full theme config."""
    return _load_theme()


# ---------------------------------------------------------------------------
# Colors
# ---------------------------------------------------------------------------

def get_colors() -> Dict[str, str]:
    """Return the colors dict."""
    return _load_theme()["colors"]


def get_color(key: str, fallback: str = "#000000") -> str:
    """Get a single color value by key."""
    return get_colors().get(key, fallback)


# ---------------------------------------------------------------------------
# Typography
# ---------------------------------------------------------------------------

def get_typography() -> Dict[str, str]:
    """Return typography config (font_family, font_url)."""
    return _load_theme()["typography"]


# ---------------------------------------------------------------------------
# Map
# ---------------------------------------------------------------------------

def get_map_config() -> Dict[str, Any]:
    """Return map configuration (center, zoom, dimensions)."""
    return _load_theme()["map"]


# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------

def get_layout() -> Dict[str, str]:
    """Return layout config (sidebar_width, info_panel_width, etc.)."""
    return _load_theme()["layout"]


# ---------------------------------------------------------------------------
# Color schemes
# ---------------------------------------------------------------------------

def get_color_schemes() -> Dict[str, dict]:
    """Return all color schemes with labels and color arrays."""
    return _load_theme()["color_schemes"]


def get_color_scheme_colors() -> Dict[str, List[str]]:
    """Return color schemes as {name: [colors...]} for JS injection."""
    schemes = get_color_schemes()
    return {k: v["colors"] for k, v in schemes.items()}


def get_color_scheme_labels() -> Dict[str, str]:
    """Return color schemes as {name: label} for sidebar dropdown."""
    schemes = get_color_schemes()
    return {k: v["label"] for k, v in schemes.items()}


def get_color_scheme_colors_json() -> str:
    """JSON string for injection into JS template."""
    return json.dumps(get_color_scheme_colors())


def get_map_config_json() -> str:
    """JSON string for injection into JS template."""
    return json.dumps(get_map_config())
