#!/usr/bin/env python3
"""Simplify GeoJSON files to reduce payload size for web rendering.

This script:
1. Simplifies polygon geometry using shapely (preserve_topology=True)
2. Reduces coordinate precision to 5 decimal places (~1m accuracy)
3. Writes compact JSON and regenerates .gz compressed versions

Designed to run at build time (e.g., during Docker build) so the simplified
files are baked into the image with zero runtime cost.
"""

import json
import gzip
import sys
from pathlib import Path


# Simplification tolerance in degrees (~30m at Hawaii's latitude)
SIMPLIFY_TOLERANCE = 0.0003

# Coordinate precision (5 decimal places ~ 1.1m accuracy)
COORD_PRECISION = 5


def round_coordinates(obj):
    """Recursively round all coordinate numbers in a GeoJSON geometry."""
    if isinstance(obj, float):
        return round(obj, COORD_PRECISION)
    elif isinstance(obj, list):
        return [round_coordinates(item) for item in obj]
    elif isinstance(obj, dict):
        return {k: round_coordinates(v) if k in ('coordinates', 'geometry') or isinstance(v, (list, dict))
                else v for k, v in obj.items()}
    return obj


def simplify_geojson_file(filepath: Path) -> dict:
    """Load, simplify, and return a GeoJSON dict."""
    try:
        import geopandas as gpd
        from shapely.validation import make_valid
    except ImportError:
        print("WARNING: geopandas not available, falling back to coordinate rounding only")
        with open(filepath, 'r') as f:
            data = json.load(f)
        return round_coordinates(data)

    # Load with geopandas for geometry simplification
    gdf = gpd.read_file(filepath)

    original_bounds = gdf.total_bounds
    feature_count = len(gdf)

    # Ensure all geometries are valid before simplification
    gdf['geometry'] = gdf['geometry'].apply(
        lambda geom: make_valid(geom) if geom is not None and not geom.is_valid else geom
    )

    # Simplify geometry (preserve_topology=True prevents self-intersections)
    gdf['geometry'] = gdf['geometry'].simplify(
        tolerance=SIMPLIFY_TOLERANCE,
        preserve_topology=True
    )

    # Convert back to GeoJSON dict
    geojson_dict = json.loads(gdf.to_json())

    # Round coordinates for further size reduction
    geojson_dict = round_coordinates(geojson_dict)

    # Verify feature count preserved
    assert len(geojson_dict['features']) == feature_count, \
        f"Feature count changed: {feature_count} -> {len(geojson_dict['features'])}"

    return geojson_dict


def process_all_geojson_files():
    """Process all GeoJSON files in the data directory."""
    geojson_dir = Path(__file__).parent.parent / 'data' / 'Processed GeoJsons'

    if not geojson_dir.exists():
        # Fallback for Docker build context where __file__ may differ
        geojson_dir = Path('data/Processed GeoJsons')

    if not geojson_dir.exists():
        print(f"ERROR: Directory {geojson_dir} not found")
        sys.exit(1)

    geojson_files = sorted(geojson_dir.glob('*.geojson'))
    if not geojson_files:
        print(f"ERROR: No .geojson files found in {geojson_dir}")
        sys.exit(1)

    print(f"Found {len(geojson_files)} GeoJSON files in {geojson_dir}\n")

    total_original = 0
    total_simplified = 0

    for filepath in geojson_files:
        original_size = filepath.stat().st_size
        total_original += original_size

        print(f"Processing {filepath.name}...")
        print(f"  Original size: {original_size / 1024 / 1024:.2f} MB")

        # Simplify
        simplified = simplify_geojson_file(filepath)
        feature_count = len(simplified.get('features', []))

        # Write simplified GeoJSON (compact JSON)
        simplified_json = json.dumps(simplified, separators=(',', ':'))
        with open(filepath, 'w') as f:
            f.write(simplified_json)

        simplified_size = filepath.stat().st_size
        total_simplified += simplified_size

        # Regenerate compressed version
        gz_path = filepath.with_suffix('.geojson.gz')
        with gzip.open(gz_path, 'wt') as f:
            f.write(simplified_json)

        compressed_size = gz_path.stat().st_size
        reduction = (1 - simplified_size / original_size) * 100

        print(f"  Simplified:    {simplified_size / 1024 / 1024:.2f} MB ({feature_count} features)")
        print(f"  Compressed:    {compressed_size / 1024:.0f} KB")
        print(f"  Reduction:     {reduction:.1f}%")
        print()

    total_reduction = (1 - total_simplified / total_original) * 100
    print(f"{'='*50}")
    print(f"Total original:   {total_original / 1024 / 1024:.2f} MB")
    print(f"Total simplified: {total_simplified / 1024 / 1024:.2f} MB")
    print(f"Total reduction:  {total_reduction:.1f}%")


if __name__ == '__main__':
    process_all_geojson_files()
