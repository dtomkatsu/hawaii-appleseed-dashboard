import streamlit as st
import folium
from streamlit_folium import folium_static, st_folium
from folium.plugins import Fullscreen, MeasureControl
import geopandas as gpd
import pandas as pd
import numpy as np
import logging
import os
import traceback
from pathlib import Path
import json
import sys

# Configure logging with debug file
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Create a dedicated debug log file
debug_logger = logging.getLogger('debug')
debug_logger.setLevel(logging.DEBUG)
debug_file_handler = logging.FileHandler('debug.log')
debug_file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
debug_logger.addHandler(debug_file_handler)

# Log system information
debug_logger.info(f"Python version: {sys.version}")
debug_logger.info(f"Folium version: {folium.__version__}")
debug_logger.info(f"GeoPandas version: {gpd.__version__}")
debug_logger.info(f"Starting application at {logging.Formatter().formatTime(logging.LogRecord('', 0, '', 0, '', (), None, None))}")

# Function to log errors to debug file
def log_error(message, exception=None):
    """Log error to debug file with traceback"""
    debug_logger.error(message)
    if exception:
        debug_logger.error(traceback.format_exc())
        with open('debug.log', 'a') as f:
            f.write(f"\n{message}\n{traceback.format_exc()}\n")


# Define paths to GeoJSON files
DATA_DIR = Path("data/Processed GeoJsons")
GEOJSON_FILES = {
    'State': DATA_DIR / 'hawaii_state_boundary.geojson',
    'Counties': DATA_DIR / 'hawaii_county_boundaries.geojson',
    'State House Districts': DATA_DIR / 'Hawaii_State_House_Districts_2022.geojson',
    'State Senate Districts': DATA_DIR / 'Hawaii_State_Senate_Districts_2022.geojson'
}

# Function to load GeoJSON files
def load_geojson(file_path):
    """Load GeoJSON file into GeoDataFrame"""
    try:
        if not file_path.exists():
            logger.warning(f"File not found: {file_path}")
            return None
            
        logger.info(f"Loading GeoJSON file: {file_path}")
        gdf = gpd.read_file(file_path)
        
        if gdf.empty:
            logger.warning(f"Empty GeoDataFrame: {file_path}")
            return None
            
        # Ensure the CRS is EPSG:4326 (WGS84)
        if gdf.crs is None:
            logger.warning(f"No CRS found in {file_path}, assuming WGS84")
            gdf.crs = 'EPSG:4326'
        elif gdf.crs.to_epsg() != 4326:
            logger.info(f"Converting CRS from {gdf.crs} to EPSG:4326")
            gdf = gdf.to_crs(epsg=4326)
            
        # Log some information about the loaded data
        logger.info(f"Loaded {len(gdf)} features from {file_path}")
        logger.info(f"Columns: {list(gdf.columns)}")
            
        return gdf
        
    except Exception as e:
        logger.error(f"Error loading {file_path}: {str(e)}", exc_info=True)
        # Create a debug log file for errors
        with open('debug.log', 'a') as f:
            f.write(f"Error loading {file_path}: {str(e)}\n")
        return None

def get_layer_color(layer_name):
    """Get a distinct color for each layer type"""
    colors = {
        'State': '#3186cc',
        'Counties': '#31a354',
        'State House Districts': '#756bb1',
        'State Senate Districts': '#e6550d'
    }
    return colors.get(layer_name, '#3186cc')

def style_function(feature, layer_name):
    """Style function for GeoJSON layers with distinct colors"""
    return {
        'fillColor': get_layer_color(layer_name),
        'color': 'black',
        'weight': 1,
        'fillOpacity': 0.6,  # Increased fill opacity
        'opacity': 0.8,
        'dashArray': '5, 5' if 'Districts' in layer_name else None  # Add dash for districts
    }

def highlight_function(feature, layer_name):
    """Highlight function for GeoJSON layers"""
    return {
        'fillColor': '#ff0000',  # Red highlight on hover
        'color': 'yellow',
        'weight': 3,
        'fillOpacity': 0.8,
        'opacity': 1
    }

def create_map():
    """Create a base map with geographic layers"""
    try:
        logger.info("Initializing map...")
        # Initialize a simpler map with CartoDB Positron as base layer
        m = folium.Map(
            location=[20.7984, -156.3319],
            zoom_start=7,
            tiles='CartoDB Positron',
            min_zoom=6,
            max_zoom=18,
            control_scale=True,
            prefer_canvas=True
        )
        
        # Add additional tile layers with proper attribution
        folium.TileLayer(
            'OpenStreetMap',
            name='OpenStreetMap',
            attr='&copy; OpenStreetMap contributors'
        ).add_to(m)
        
        # Create a FeatureGroup for each layer
        for layer_name, file_path in GEOJSON_FILES.items():
            try:
                logger.info(f"Loading layer: {layer_name} from {file_path}")
                gdf = load_geojson(file_path)
                if gdf is not None and not gdf.empty:
                    # Simplify geometry for better performance
                    logger.info(f"Simplifying geometry for {layer_name}")
                    gdf['geometry'] = gdf['geometry'].simplify(tolerance=0.001, preserve_topology=True)
                    
                    # Create GeoJson layer with better styling
                    logger.info(f"Creating GeoJSON layer for {layer_name}")
                    geojson_data = gdf.to_json()
                    
                    # Get the appropriate name field and create tooltip fields/aliases
                    tooltip_fields = []
                    tooltip_aliases = []
                    
                    # Add common fields we want to show in tooltips
                    if 'name' in gdf.columns:
                        tooltip_fields.append('name')
                        tooltip_aliases.append('Name')
                    if 'county_name' in gdf.columns:
                        tooltip_fields.append('county_name')
                        tooltip_aliases.append('County')
                    if 'state_house' in gdf.columns:
                        tooltip_fields.append('state_house')
                        tooltip_aliases.append('District')
                    if 'state_senate' in gdf.columns:
                        tooltip_fields.append('state_senate')
                        tooltip_aliases.append('District')
                    
                    # If no specific fields found, use the first few columns
                    if not tooltip_fields and len(gdf.columns) > 0:
                        for i, col in enumerate(gdf.columns[:3]):  # Limit to first 3 columns
                            if col != 'geometry':
                                tooltip_fields.append(col)
                                tooltip_aliases.append(str(col).replace('_', ' ').title())
                    
                    # Create GeoJSON layer with enhanced tooltip
                    geojson_layer = folium.GeoJson(
                        data=geojson_data,
                        name=layer_name,
                        style_function=lambda x, name=layer_name: style_function(x, name),
                        highlight_function=lambda x, name=layer_name: highlight_function(x, name),
                        tooltip=folium.GeoJsonTooltip(
                            fields=tooltip_fields,
                            aliases=tooltip_aliases,
                            localize=True,
                            sticky=True,
                            labels=True,
                            style="""
                                background-color: #F0EFEF;
                                border: 2px solid black;
                                border-radius: 3px;
                                box-shadow: 3px 3px 4px gray;
                                font-size: 14px;
                                padding: 5px;
                            """,
                            max_width=800,
                        ) if tooltip_fields else None
                    )
                    
                    # Create a feature group for the layer
                    fg = folium.FeatureGroup(name=layer_name)
                    geojson_layer.add_to(fg)
                    
                    # Add the feature group to the map
                    fg.add_to(m)
                    logger.info(f"Successfully added layer: {layer_name}")
                else:
                    logger.warning(f"Empty or invalid GeoDataFrame for {layer_name}")
                    st.warning(f"Could not load layer: {layer_name}")
                    
            except Exception as e:
                error_msg = f"Error adding layer {layer_name}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                st.error(f"Error loading layer: {layer_name}. See logs for details.")
        
        # Add layer control
        folium.LayerControl(position='topright', collapsed=False).add_to(m)
        
        # Add fullscreen button
        Fullscreen(
            position="topleft",
            title="Full Screen",
            title_cancel="Exit Full Screen",
            force_separate_button=True
        ).add_to(m)
        
        # Add measure control
        measure = MeasureControl()
        measure.add_to(m)
        
        # Fit bounds to show all features
        m.fit_bounds(m.get_bounds())
        
        logger.info("Map creation completed successfully")
        return m
        
    except Exception as e:
        logger.error(f"Error in create_map: {str(e)}", exc_info=True)
        # Return a basic map with error message
        error_map = folium.Map(location=[20.7984, -156.3319], zoom_start=7)
        folium.Marker(
            location=[20.7984, -156.3319],
            popup="Error loading map layers. Check the logs for details.",
            icon=folium.Icon(color='red', icon='warning')
        ).add_to(error_map)
        return error_map

def main():
    # Page config
    st.set_page_config(
        page_title="Hawaii Appleseed Data Dashboard",
        page_icon="🌺",
        layout="wide"
    )
    
    # Add custom CSS to make the map fill the screen
    st.markdown(
        """
        <style>
        .main .block-container {
            padding-top: 1rem;
            padding-bottom: 1rem;
        }
        #root > div:nth-child(1) > div > div > div > div > section > div {
            padding: 0rem 1rem 0rem 1rem;
        }
        .stApp {
            margin: 0;
            padding: 0;
            width: 100%;
        }
        </style>
        """,
        unsafe_allow_html=True
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
    The map includes the following geographic layers:
    - **State**: Hawaii state boundary
    - **Counties**: County boundaries (2022)
    - **State House Districts**: Hawaii State House legislative districts (2022)
    - **State Senate Districts**: Hawaii State Senate legislative districts (2022)
    
    Click the layers icon in the top-right corner of the map to toggle layers on/off.
    
    Note: Legislative districts are based on 2022 redistricting data.
    """)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.critical(f"Application error: {str(e)}", exc_info=True)
        st.error("An error occurred. Please check the logs for more details.")
