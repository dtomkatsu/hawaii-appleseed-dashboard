#!/usr/bin/env python3
"""
Script to optimize and compress GeoJSON files for faster loading.
This script will:
1. Compress existing GeoJSON files with gzip
2. Create simplified versions with reduced precision
3. Generate size comparison report
"""

import json
import gzip
import os
from pathlib import Path
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def compress_geojson_file(input_path, output_path):
    """Compress a GeoJSON file with gzip."""
    try:
        with open(input_path, 'r') as f_in:
            with gzip.open(output_path, 'wt') as f_out:
                # Load and re-save to ensure consistent formatting
                data = json.load(f_in)
                json.dump(data, f_out, separators=(',', ':'))  # Compact JSON
        
        original_size = os.path.getsize(input_path)
        compressed_size = os.path.getsize(output_path)
        compression_ratio = (1 - compressed_size / original_size) * 100
        
        logger.info(f"Compressed {input_path.name}: {original_size:,} -> {compressed_size:,} bytes ({compression_ratio:.1f}% reduction)")
        return original_size, compressed_size
        
    except Exception as e:
        logger.error(f"Error compressing {input_path}: {e}")
        return 0, 0

def simplify_coordinates(coords, precision=4):
    """Simplify coordinate precision to reduce file size."""
    if isinstance(coords[0], list):
        return [simplify_coordinates(coord, precision) for coord in coords]
    else:
        return [round(coord, precision) for coord in coords]

def optimize_geojson_geometry(geojson_data, precision=4):
    """Optimize GeoJSON by reducing coordinate precision."""
    if 'features' not in geojson_data:
        return geojson_data
    
    for feature in geojson_data['features']:
        if 'geometry' in feature and feature['geometry']:
            geometry = feature['geometry']
            if 'coordinates' in geometry:
                geometry['coordinates'] = simplify_coordinates(geometry['coordinates'], precision)
    
    return geojson_data

def main():
    """Main optimization function."""
    # Define paths
    base_path = Path(__file__).parent / 'data' / 'Processed GeoJsons'
    
    if not base_path.exists():
        logger.error(f"GeoJSON directory not found: {base_path}")
        return
    
    # Files to optimize
    geojson_files = [
        'hawaii_state_boundary.geojson',
        'hawaii_county_boundaries.geojson',
        'Hawaii_State_House_Districts_2022.geojson',
        'Hawaii_State_Senate_Districts_2022.geojson'
    ]
    
    total_original = 0
    total_compressed = 0
    
    logger.info("Starting GeoJSON optimization...")
    
    for filename in geojson_files:
        file_path = base_path / filename
        
        if not file_path.exists():
            logger.warning(f"File not found: {file_path}")
            continue
        
        # Create compressed version
        compressed_path = base_path / f"{filename}.gz"
        
        # Load, optimize, and compress
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            # Keep all data properties, only optimize coordinate precision
            optimized_data = optimize_geojson_geometry(data, precision=4)
            
            # Save compressed version
            with gzip.open(compressed_path, 'wt') as f:
                json.dump(optimized_data, f, separators=(',', ':'))
            
            original_size = os.path.getsize(file_path)
            compressed_size = os.path.getsize(compressed_path)
            
            total_original += original_size
            total_compressed += compressed_size
            
            compression_ratio = (1 - compressed_size / original_size) * 100
            logger.info(f"✓ {filename}: {original_size:,} -> {compressed_size:,} bytes ({compression_ratio:.1f}% reduction)")
            
        except Exception as e:
            logger.error(f"Error processing {filename}: {e}")
    
    # Summary
    if total_original > 0:
        total_reduction = (1 - total_compressed / total_original) * 100
        logger.info(f"\n📊 SUMMARY:")
        logger.info(f"Total original size: {total_original:,} bytes ({total_original/1024/1024:.1f} MB)")
        logger.info(f"Total compressed size: {total_compressed:,} bytes ({total_compressed/1024/1024:.1f} MB)")
        logger.info(f"Total reduction: {total_reduction:.1f}%")
        logger.info(f"Space saved: {(total_original - total_compressed):,} bytes ({(total_original - total_compressed)/1024/1024:.1f} MB)")

if __name__ == "__main__":
    main()
