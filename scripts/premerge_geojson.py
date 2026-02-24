"""
Pre-merge GeoJSON files with statistical data to create static JSON files.
This eliminates server-side data loading and merging at runtime.

Usage:
    python scripts/premerge_geojson.py
"""
import json
import gzip
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.data.data_loader import DataLoader


def premerge_all():
    """Pre-merge all GeoJSON files with their corresponding data."""
    output_dir = project_root / 'static' / 'data' / 'premerged'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    geojson_dir = project_root / 'data' / 'Processed GeoJsons'
    
    # Layer name -> (geojson filename, geo_level for data loader)
    layers = {
        'state_boundary': ('hawaii_state_boundary.geojson', 'state'),
        'counties': ('hawaii_county_boundaries.geojson', 'county'),
        'house_districts': ('Hawaii_State_House_Districts_2022.geojson', 'house'),
        'senate_districts': ('Hawaii_State_Senate_Districts_2022.geojson', 'senate'),
    }
    
    print("Initializing DataLoader...")
    loader = DataLoader()
    
    for layer_key, (geojson_file, geo_level) in layers.items():
        print(f"\n--- Processing {layer_key} ({geo_level}) ---")
        
        # Load GeoJSON
        geojson_path = geojson_dir / geojson_file
        if not geojson_path.exists():
            # Try compressed version
            gz_path = geojson_dir / f"{geojson_file}.gz"
            if gz_path.exists():
                print(f"  Loading compressed: {gz_path.name}")
                with gzip.open(gz_path, 'rt') as f:
                    geojson_data = json.load(f)
            else:
                print(f"  ERROR: File not found: {geojson_path}")
                continue
        else:
            print(f"  Loading: {geojson_file}")
            with open(geojson_path, 'r') as f:
                geojson_data = json.load(f)
        
        feature_count = len(geojson_data.get('features', []))
        print(f"  Features: {feature_count}")
        
        # Merge with data
        print(f"  Merging with {geo_level} data...")
        merged = loader.merge_geojson_with_data(geojson_data, geo_level)
        
        # Verify merge worked by checking if properties were added
        if merged and merged.get('features'):
            sample_props = merged['features'][0].get('properties', {})
            data_keys = [k for k in sample_props.keys() if k not in ('NAME', 'GEOID', 'geometry')]
            print(f"  Merged properties: {len(sample_props)} keys")
            print(f"  Sample data keys: {data_keys[:8]}...")
        
        # Optimize coordinate precision to reduce file size
        merged = _reduce_precision(merged)
        
        # Save as regular JSON
        output_path = output_dir / f"{layer_key}.json"
        with open(output_path, 'w') as f:
            json.dump(merged, f, separators=(',', ':'))
        
        file_size = output_path.stat().st_size
        print(f"  Saved: {output_path.name} ({file_size / 1024:.0f} KB)")
        
        # Also save gzipped version for even smaller size
        gz_output = output_dir / f"{layer_key}.json.gz"
        with gzip.open(gz_output, 'wt', compresslevel=9) as f:
            json.dump(merged, f, separators=(',', ':'))
        
        gz_size = gz_output.stat().st_size
        print(f"  Saved: {gz_output.name} ({gz_size / 1024:.0f} KB)")
    
    print("\n=== Pre-merge complete! ===")
    print(f"Output directory: {output_dir}")


def _reduce_precision(geojson_data, precision=5):
    """Reduce coordinate precision to save file size."""
    if not geojson_data or 'features' not in geojson_data:
        return geojson_data
    
    for feature in geojson_data['features']:
        geometry = feature.get('geometry')
        if geometry:
            feature['geometry'] = _round_coords(geometry, precision)
    
    return geojson_data


def _round_coords(geometry, precision):
    """Recursively round coordinates in a geometry."""
    if geometry is None:
        return None
    
    geom_type = geometry.get('type', '')
    coords = geometry.get('coordinates')
    
    if coords is None:
        return geometry
    
    geometry['coordinates'] = _round_nested(coords, precision)
    return geometry


def _round_nested(coords, precision):
    """Recursively round nested coordinate arrays."""
    if isinstance(coords, (int, float)):
        return round(coords, precision)
    if isinstance(coords, list):
        if len(coords) > 0 and isinstance(coords[0], (int, float)):
            return [round(c, precision) for c in coords]
        return [_round_nested(c, precision) for c in coords]
    return coords


if __name__ == '__main__':
    premerge_all()
