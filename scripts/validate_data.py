#!/usr/bin/env python3
"""Validate pre-merged GeoJSON data files for completeness and correctness.

Run after any data pipeline update to gate deployments.
Exit code 0 = all checks pass, 1 = validation failure.
"""
import json
import sys
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "static" / "data" / "premerged"

EXPECTED_FEATURES = {
    "state_boundary.json": 1,
    "counties.json": 4,
    "house_districts.json": 51,
    "senate_districts.json": 25,
}

REQUIRED_VARIABLES = [
    "poverty_rate",
    "median_income",
    "alice_rate",
    "rent_burden_rate",
]

RANGE_CHECKS = {
    "poverty_rate": (0, 100),
    "median_income": (0, 500_000),
    "alice_rate": (0, 100),
    "rent_burden_rate": (0, 100),
    "snap_household_rate": (0, 100),
    "college_educated_pct": (0, 100),
}

errors: list[str] = []


def check_file(name: str, expected_count: int) -> None:
    path = DATA_DIR / name
    if not path.exists():
        errors.append(f"MISSING: {name}")
        return

    data = json.loads(path.read_text())

    if data.get("type") != "FeatureCollection":
        errors.append(f"{name}: not a FeatureCollection")
        return

    features = data.get("features", [])
    actual = len(features)
    if actual != expected_count:
        errors.append(f"{name}: expected {expected_count} features, got {actual}")

    for i, feat in enumerate(features):
        props = feat.get("properties", {})
        feat_name = props.get("NAME", props.get("name", f"feature[{i}]"))

        # Check required variables exist
        for var in REQUIRED_VARIABLES:
            if var not in props:
                errors.append(f"{name}/{feat_name}: missing required variable '{var}'")

        # Range checks
        for var, (lo, hi) in RANGE_CHECKS.items():
            val = props.get(var)
            if val is None:
                continue
            try:
                val = float(val)
            except (TypeError, ValueError):
                errors.append(f"{name}/{feat_name}: '{var}' is not numeric: {val!r}")
                continue
            if val < lo or val > hi:
                errors.append(f"{name}/{feat_name}: '{var}' = {val} outside [{lo}, {hi}]")

        # Geometry check
        geom = feat.get("geometry")
        if not geom or "coordinates" not in geom:
            errors.append(f"{name}/{feat_name}: missing or empty geometry")


def main() -> int:
    print("Validating pre-merged data files...")
    print(f"  Data directory: {DATA_DIR}")

    for name, expected in EXPECTED_FEATURES.items():
        check_file(name, expected)

    if errors:
        print(f"\nVALIDATION FAILED — {len(errors)} error(s):")
        for e in errors:
            print(f"  - {e}")
        return 1

    print("\nAll checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
