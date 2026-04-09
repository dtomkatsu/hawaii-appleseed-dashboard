"""
Centralized UI strings registry for the Hawaii Appleseed Dashboard.

All user-facing text lives in ui_strings.json. This module loads that file
once and provides accessor functions so non-developers can edit labels
without touching code.
"""

import json
import os
from functools import lru_cache
from typing import Dict, Any


_STRINGS_PATH = os.path.join(os.path.dirname(__file__), "ui_strings.json")


@lru_cache(maxsize=1)
def _load_strings() -> dict:
    with open(_STRINGS_PATH, "r") as f:
        return json.load(f)


def get_ui_strings() -> dict:
    """Return the full UI strings config."""
    return _load_strings()


def get_string(path: str, fallback: str = "") -> str:
    """Get a nested string by dot-separated path.

    Example: get_string("sidebar.title") -> "Hawaii Appleseed Dashboard"
    """
    obj = _load_strings()
    for key in path.split("."):
        if isinstance(obj, dict):
            obj = obj.get(key, fallback)
        else:
            return fallback
    return obj if isinstance(obj, str) else fallback


def get_strings_section(section: str) -> Dict[str, Any]:
    """Return a top-level section of the strings config."""
    return _load_strings().get(section, {})
