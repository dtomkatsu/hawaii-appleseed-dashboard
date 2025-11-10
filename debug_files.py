#!/usr/bin/env python3
"""
Debug script to check what files are available in different deployment environments.
Run this in the online environment to see what paths and files exist.
"""

import os
from pathlib import Path

def debug_file_structure():
    """Debug the file structure to help with deployment issues."""
    
    print("=== File Structure Debug ===")
    print(f"Current working directory: {Path.cwd()}")
    print(f"Script location: {Path(__file__).parent}")
    print()
    
    # Check different possible base paths
    possible_paths = [
        Path(__file__).parent / 'data',
        Path(__file__).parent / 'data' / 'Processed GeoJsons',
        Path(__file__).parent / 'data' / 'processed_geojsons',
        Path.cwd() / 'data',
        Path.cwd() / 'data' / 'Processed GeoJsons',
        Path.cwd() / 'data' / 'processed_geojsons',
        Path('/app/data'),  # Common deployment path
        Path('/app/data/Processed GeoJsons'),
        Path('/app/data/processed_geojsons'),
    ]
    
    print("=== Checking Possible Paths ===")
    for path in possible_paths:
        print(f"\nPath: {path}")
        print(f"Exists: {path.exists()}")
        
        if path.exists():
            try:
                # List contents
                contents = list(path.iterdir())
                print(f"Contents ({len(contents)} items):")
                for item in sorted(contents):
                    size = ""
                    if item.is_file():
                        try:
                            size = f" ({item.stat().st_size:,} bytes)"
                        except:
                            size = " (size unknown)"
                    print(f"  {'[DIR]' if item.is_dir() else '[FILE]'} {item.name}{size}")
                    
                # Look specifically for GeoJSON files
                geojson_files = list(path.glob('*.geojson*'))
                if geojson_files:
                    print(f"GeoJSON files found:")
                    for f in geojson_files:
                        print(f"  {f.name} ({f.stat().st_size:,} bytes)")
                        
            except Exception as e:
                print(f"Error listing contents: {e}")
    
    print("\n=== Environment Variables ===")
    relevant_env_vars = ['HOME', 'PWD', 'STREAMLIT_SERVER_PORT', 'PORT']
    for var in relevant_env_vars:
        value = os.environ.get(var, 'Not set')
        print(f"{var}: {value}")
    
    print("\n=== Python Path ===")
    import sys
    for i, path in enumerate(sys.path):
        print(f"{i}: {path}")

if __name__ == "__main__":
    debug_file_structure()
