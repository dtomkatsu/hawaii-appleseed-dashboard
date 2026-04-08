"""
Centralized data source registry for the Hawaii Appleseed Dashboard.

All data source definitions (years, file patterns, fetch methods) live in
src/config/data_sources.json. This module loads that file and provides
accessor functions used by data_loader.py and scripts/update_data.py.
"""

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

_CONFIG_PATH = Path(__file__).parent.parent / "config" / "data_sources.json"
_BASE_DIR = Path(__file__).parent.parent.parent  # project root


def _load_config() -> dict:
    """Load data_sources.json (not cached — callers may mutate and reload)."""
    with open(_CONFIG_PATH, "r") as f:
        return json.load(f)


def _save_config(config: dict) -> None:
    """Write updated config back to data_sources.json."""
    with open(_CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)


# ---------------------------------------------------------------------------
# Year accessors
# ---------------------------------------------------------------------------

def get_year(source: str) -> int:
    """Return the configured data year for a source (e.g. 'acs', 'snap')."""
    return _load_config()["sources"][source]["year"]


def get_all_years() -> Dict[str, int]:
    """Return a mapping of source_key -> year for all sources."""
    config = _load_config()
    return {key: cfg["year"] for key, cfg in config["sources"].items()}


def set_year(source: str, year: int) -> None:
    """Update the year for a source and persist to data_sources.json."""
    config = _load_config()
    config["sources"][source]["year"] = year
    _save_config(config)
    logger.info(f"Updated {source} year to {year} in data_sources.json")


# ---------------------------------------------------------------------------
# File path resolution
# ---------------------------------------------------------------------------

def get_file_path(source: str, level: str) -> Path:
    """
    Resolve the full path for a given source + geographic level.

    Args:
        source: 'acs', 'snap', 'cep', or 'tax_credits'
        level: 'state', 'county', 'house', or 'senate'

    Returns:
        Absolute Path to the expected CSV file.
    """
    config = _load_config()
    src = config["sources"][source]
    year = src["year"]
    pattern = src["file_patterns"][level]
    filename = pattern.format(year=year)
    subdir = src.get("subdirectory", "")
    base = _BASE_DIR / "data" / "processed"
    return (base / subdir / filename) if subdir else (base / filename)


def get_all_file_paths(source: str) -> Dict[str, Path]:
    """Return {level: path} for all geo levels of a source."""
    config = _load_config()
    levels = list(config["sources"][source].get("file_patterns", {}).keys())
    return {level: get_file_path(source, level) for level in levels}


def get_alice_excel_path() -> Path:
    """Return the expected path to the ALICE Excel workbook."""
    config = _load_config()
    src = config["sources"]["alice"]
    year = src["year"]
    filename = src["excel_filename"].format(year=year)
    return _BASE_DIR / src["excel_directory"] / filename


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def check_files(source: str) -> Dict[str, bool]:
    """
    Check which files for a source exist on disk.

    Returns:
        {level: True/False} dict.
    """
    if source == "alice":
        path = get_alice_excel_path()
        return {"excel": path.exists()}

    return {level: path.exists() for level, path in get_all_file_paths(source).items()}


def get_missing_files(source: str) -> List[Tuple[str, Path]]:
    """Return list of (level, path) pairs for files that don't exist."""
    if source == "alice":
        path = get_alice_excel_path()
        return [] if path.exists() else [("excel", path)]
    return [
        (level, path)
        for level, path in get_all_file_paths(source).items()
        if not path.exists()
    ]


def validate_all_sources() -> Dict[str, Dict]:
    """
    Check every source and return a status report.

    Returns:
        {source: {
            "label": str,
            "year": int,
            "fetch_method": str,
            "status": "ok" | "partial" | "missing",
            "missing": [(level, path), ...]
        }}
    """
    config = _load_config()
    report = {}
    for key, src in config["sources"].items():
        missing = get_missing_files(key)
        if not missing:
            status = "ok"
        elif src.get("fetch_method") == "manual":
            all_levels = list(src.get("file_patterns", {}).keys() or ["excel"])
            status = "partial" if len(missing) < len(all_levels) else "missing"
        else:
            status = "missing"
        report[key] = {
            "label": src["label"],
            "year": src["year"],
            "fetch_method": src["fetch_method"],
            "status": status,
            "missing": missing,
        }
    return report


# ---------------------------------------------------------------------------
# Source metadata
# ---------------------------------------------------------------------------

def get_source_info(source: str) -> dict:
    """Return the full source config dict for a given source key."""
    return _load_config()["sources"][source]


def get_fetch_method(source: str) -> str:
    """Return 'api' or 'manual' for a source."""
    return _load_config()["sources"][source]["fetch_method"]


def get_instructions(source: str) -> str:
    """Return the human-readable update instructions for a manual source."""
    return _load_config()["sources"][source].get("instructions", "")


def get_census_variables(source: str = "acs") -> Dict[str, str]:
    """Return the Census API variable codes for an API-fetched source."""
    return _load_config()["sources"][source].get("census_variables", {})
