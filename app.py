import streamlit as st
import folium
from streamlit_folium import folium_static, st_folium
import geopandas as gpd
import pandas as pd
import numpy as np
import logging
import os
from pathlib import Path
import json

# Define paths to GeoJSON files
DATA_DIR = Path("data/Processed GeoJsons")
GEOJSON_FILES = {
    'State': DATA_DIR / 'hawaii_state_boundary.geojson',
    'Counties': DATA_DIR / 'hawaii_county_boundaries.geojson',
    'State House Districts': DATA_DIR / 'hawaii_house_districts.geojson',
    'State Senate Districts': DATA_DIR / 'hawaii_senate_districts.geojson'
}

# Configure logging
logging.basicConfig(
    filename='debug.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def load_geojson(file_path):
    """Load a GeoJSON file"""
    try:
        gdf = gpd.read_file(file_path)
        # Ensure consistent CRS (WGS84 - EPSG:4326)
        if gdf.crs and gdf.crs.to_epsg() != 4326:
            gdf = gdf.to_crs(epsg=4326)
        return gdf
    except Exception as e:
        logging.error(f"Error loading {file_path}: {str(e)}", exc_info=True)
        return None

def style_function(feature):
    """Style function for the GeoJSON layers"""
    return {
        'fillColor': '#ffaf00',
        'color': 'black',
        'weight': 1,
        'fillOpacity': 0.2,
    }

def highlight_function(feature):
    """Highlight function for GeoJSON layers"""
    return {
        'fillColor': '#ffaf00',
        'color': 'black',
        'weight': 2,
        'fillOpacity': 0.5,
    }

def create_map():
    """Create a base map with TIGER/Line layers"""
    try:
        # Center on Hawaii
        m = folium.Map(location=[20.7984, -156.3319], zoom_start=7, tiles='CartoDB positron')
        
        # Create a FeatureGroup for each layer
        for layer_name, file_path in GEOJSON_FILES.items():
            if file_path.exists():
                gdf = load_geojson(file_path)
                if gdf is not None:
                    # Convert to GeoJSON
                    geojson_data = json.loads(gdf.to_json())
                    
                    # Create a feature group for the layer
                    # Show state and counties by default, hide others
                    show_layer = layer_name in ['State', 'Counties']
                    fg = folium.FeatureGroup(name=layer_name, show=show_layer)
                    
                    # Add the GeoJSON to the feature group
                    folium.GeoJson(
                        geojson_data,
                        name=layer_name,
                        style_function=style_function,
                        highlight_function=highlight_function,
                        tooltip=folium.GeoJsonTooltip(
                            fields=[col for col in gdf.columns if col != 'geometry'],
                            aliases=[col.capitalize() for col in gdf.columns if col != 'geometry'],
                            localize=True,
                            sticky=True,
                            labels=True,
                            style="""
                                background-color: #F0EFEF;
                                border: 1px solid black;
                                border-radius: 3px;
                                box-shadow: 3px;
                            """,
                            max_width=300,
                        ),
                        popup=folium.GeoJsonPopup(
                            fields=[col for col in gdf.columns if col != 'geometry'],
                            aliases=[col.capitalize() for col in gdf.columns if col != 'geometry'],
                            localize=True,
                            labels=True,
                            style="width: 300px;"
                        )
                    ).add_to(fg)
                    
                    # Add the feature group to the map
                    fg.add_to(m)
            else:
                logging.warning(f"File not found: {file_path}")
        
        # Add layer control
        folium.LayerControl(
            collapsed=True,
            position='topright',
            overlay=True,
            control=True
        ).add_to(m)
            
        return m
    except Exception as e:
        logging.error(f"Error creating map: {str(e)}", exc_info=True)
        return None

def main():
    # Page config
    st.set_page_config(
        page_title="Hawaii Appleseed Data Dashboard",
        page_icon="🌺",
        layout="wide"
    )
    
    # Title and description
    st.title("🌺 Hawaii Appleseed Data Dashboard")
    st.markdown("---")
    
    # Sidebar
    st.sidebar.header("Dashboard Controls")
    
    # Add some sample controls
    year = st.sidebar.slider("Select Year", 2018, 2023, 2023)
    data_type = st.sidebar.selectbox(
        "Select Data Type",
        ["Housing", "Education", "Economic"]
    )
    
    # Create columns for layout
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("Hawaii Map")
        map_obj = create_map()
        if map_obj:
            folium_static(map_obj, width=800, height=500)
        else:
            st.error("Failed to load map. Please check the logs.")
    
    with col2:
        st.header("Data Summary")
        # Sample data table
        data = {
            'Category': ['Housing', 'Education', 'Economic'],
            'Value': [1250, 89, 7.2],
            'Change (%)': [2.3, -1.2, 0.5]
        }
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True)
        
        # Add some metrics
        st.metric("Total Data Points", "1,234", "12% from last year")
        st.metric("Average Score", "85.6", "1.2%")
    
    # Add layer information
    st.markdown("---")
    st.header("Map Layers")
    st.markdown("""
    The map includes the following TIGER/Line layers:
    - **State**: Hawaii state boundary
    - **Counties**: County boundaries
    - **State House Districts**: Hawaii State House legislative districts
    - **State Senate Districts**: Hawaii State Senate legislative districts
    
    Click the layers icon in the top-right corner of the map to toggle layers on/off.
    """)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.critical(f"Application error: {str(e)}", exc_info=True)
        st.error("An error occurred. Please check the logs for more details.")
