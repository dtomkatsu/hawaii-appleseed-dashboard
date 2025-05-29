"""Test script to verify map functionality."""
import streamlit as st
import folium
from streamlit_folium import folium_static
import pandas as pd
import json
from pathlib import Path
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/map_test.log')
    ]
)
logger = logging.getLogger(__name__)

# Create debug log file
debug_log_path = Path('logs/map_test_debug.log')
with open(debug_log_path, 'w') as f:
    f.write("Map Test Debug Log\n")

def log_debug(message):
    """Write to debug log file."""
    with open(debug_log_path, 'a') as f:
        f.write(f"{message}\n")

def main():
    """Main function to test map display."""
    st.title("Map Test")
    
    # Create a basic map
    m = folium.Map(
        location=[20.8, -157.3],  # Center of Hawaii
        zoom_start=7,
        tiles='CartoDB positron'
    )
    
    # Test loading GeoJSON files
    base_dir = Path(__file__).parent
    geojson_dir = base_dir / 'data' / 'Processed GeoJsons'
    
    log_debug(f"Looking for GeoJSON files in: {geojson_dir}")
    
    # List all GeoJSON files
    geojson_files = list(geojson_dir.glob('*.geojson'))
    log_debug(f"Found {len(geojson_files)} GeoJSON files:")
    for file in geojson_files:
        log_debug(f"  - {file.name}")
    
    # Try to load and display each GeoJSON file
    for file in geojson_files:
        try:
            log_debug(f"Loading {file.name}...")
            
            # Create a feature group for this layer
            layer_name = file.stem
            fg = folium.FeatureGroup(name=layer_name, show=True)
            
            # Load GeoJSON
            with open(file, 'r', encoding='utf-8') as f:
                geojson_data = json.load(f)
            
            log_debug(f"  - Loaded GeoJSON with {len(geojson_data.get('features', []))} features")
            
            # Add GeoJSON to map
            folium.GeoJson(
                data=geojson_data,
                name=layer_name,
                style_function=lambda feature: {
                    'fillColor': '#ff7800',
                    'color': '#000000',
                    'weight': 1,
                    'fillOpacity': 0.5
                }
            ).add_to(fg)
            
            # Add feature group to map
            fg.add_to(m)
            log_debug(f"  - Added {layer_name} to map")
            
        except Exception as e:
            log_debug(f"Error loading {file.name}: {str(e)}")
            logger.error(f"Error loading {file.name}: {str(e)}", exc_info=True)
    
    # Add layer control
    folium.LayerControl().add_to(m)
    
    # Display the map
    st.write("Map should appear below:")
    folium_static(m, width=1000, height=600)
    
    # Display debug info
    st.subheader("Debug Information")
    st.text(f"GeoJSON Directory: {geojson_dir}")
    st.text(f"Number of GeoJSON files: {len(geojson_files)}")
    
    # List GeoJSON files
    st.subheader("GeoJSON Files")
    for file in geojson_files:
        st.text(f"- {file.name}")

if __name__ == "__main__":
    main()
