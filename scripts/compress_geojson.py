#!/usr/bin/env python3
"""Compress GeoJSON files to reduce cloud loading times."""

import json
import gzip
from pathlib import Path

def compress_geojson_files():
    """Compress large GeoJSON files for faster cloud loading."""
    geojson_dir = Path("data/Processed GeoJsons")
    
    if not geojson_dir.exists():
        print(f"Directory {geojson_dir} not found")
        return
    
    for geojson_file in geojson_dir.glob("*.geojson"):
        print(f"Processing {geojson_file.name}...")
        
        # Read original file
        with open(geojson_file, 'r') as f:
            data = json.load(f)
        
        # Create compressed version
        compressed_file = geojson_file.with_suffix('.geojson.gz')
        with gzip.open(compressed_file, 'wt') as f:
            json.dump(data, f, separators=(',', ':'))  # Compact JSON
        
        # Check size reduction
        original_size = geojson_file.stat().st_size
        compressed_size = compressed_file.stat().st_size
        reduction = (1 - compressed_size / original_size) * 100
        
        print(f"  Original: {original_size / 1024 / 1024:.1f}MB")
        print(f"  Compressed: {compressed_size / 1024 / 1024:.1f}MB")
        print(f"  Reduction: {reduction:.1f}%")
        print()

if __name__ == "__main__":
    compress_geojson_files()
