import streamlit as st
import folium
from streamlit_folium import folium_static, st_folium
from folium.plugins import Fullscreen, MeasureControl
import geopandas as gpd
import pandas as pd
import numpy as np
import logging
import os
from datetime import datetime
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
        
        # Create a debug log file to track the map creation process
        with open('map_debug.log', 'w') as debug_file:
            debug_file.write(f"Map creation started at {datetime.now()}\n")
            
            # Initialize map with explicit dimensions and Hawaii bounds
            m = folium.Map(
                location=[20.5, -157.5],  # Center of Hawaii
                zoom_start=7,  # Good starting zoom level
                tiles='CartoDB Positron',
                control_scale=True,
                prefer_canvas=True,
                zoom_control=True,
                width='100%',
                height='100%',
                min_zoom=6,  # Prevent zooming out too far
                max_zoom=14,  # Prevent zooming in too close
                min_lat=18.5,
                max_lat=22.5,
                min_lon=-160.5,
                max_lon=-154.5,
                max_bounds=True  # Prevent panning outside Hawaii
            )
            
            debug_file.write("Base map initialized\n")
            
            # Add additional tile layers with proper attribution
            folium.TileLayer(
                'OpenStreetMap',
                name='OpenStreetMap',
                attr='&copy; OpenStreetMap contributors'
            ).add_to(m)
            
            # Track bounds of all features to calculate proper zoom
            min_lat, min_lon = 90, 180
            max_lat, max_lon = -90, -180
            
            # Create a FeatureGroup for each layer
            layer_count = 0
            for layer_name, file_path in GEOJSON_FILES.items():
                try:
                    debug_file.write(f"Loading layer: {layer_name} from {file_path}\n")
                    logger.info(f"Loading layer: {layer_name} from {file_path}")
                    gdf = load_geojson(file_path)
                    
                    if gdf is not None and not gdf.empty:
                        # Update bounds based on this layer
                        bounds = gdf.total_bounds  # Returns (min_x, min_y, max_x, max_y)
                        min_lon = min(min_lon, bounds[0])
                        min_lat = min(min_lat, bounds[1])
                        max_lon = max(max_lon, bounds[2])
                        max_lat = max(max_lat, bounds[3])
                        
                        debug_file.write(f"Layer bounds: {bounds}\n")
                        
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
                        layer_count += 1
                        logger.info(f"Successfully added layer: {layer_name}")
                        debug_file.write(f"Successfully added layer: {layer_name}\n")
                    else:
                        logger.warning(f"Empty or invalid GeoDataFrame for {layer_name}")
                        st.warning(f"Could not load layer: {layer_name}")
                        debug_file.write(f"Empty or invalid GeoDataFrame for {layer_name}\n")
                        
                except Exception as e:
                    error_msg = f"Error adding layer {layer_name}: {str(e)}"
                    logger.error(error_msg, exc_info=True)
                    st.error(f"Error loading layer: {layer_name}. See logs for details.")
                    debug_file.write(f"Error adding layer {layer_name}: {str(e)}\n")
            
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
            
            # Log the calculated bounds
            debug_file.write(f"Final calculated bounds: [{min_lat}, {min_lon}], [{max_lat}, {max_lon}]\n")
            
            # Add some padding to the bounds
            lat_padding = (max_lat - min_lat) * 0.1
            lon_padding = (max_lon - min_lon) * 0.1
            
            min_lat -= lat_padding
            max_lat += lat_padding
            min_lon -= lon_padding
            max_lon += lon_padding
            
            debug_file.write(f"Padded bounds: [{min_lat}, {min_lon}], [{max_lat}, {max_lon}]\n")
            
            # Set the map's bounds if we have layers
            if layer_count > 0:  # Only if we have layers
                # Use Hawaii-specific bounds instead of calculated ones
                hi_bounds = [[18.5, -160.5], [22.5, -154.5]]
                m.fit_bounds(hi_bounds, max_zoom=7)
                debug_file.write(f"Set Hawaii-specific bounds: {hi_bounds}\n")
            
            # Always ensure we have a good zoom level for Hawaii
            m.zoom_start = 7
            debug_file.write("Set fixed zoom level\n")
            
            debug_file.write(f"Map creation completed at {datetime.now()}\n")
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
    
    # Add custom CSS for better map display
    st.markdown(
        """
        <style>
        /* Main container adjustments */
        .main .block-container {
            padding: 0.5rem 1rem 1rem 1rem;
            max-width: 100%;
        }
        
        /* Adjust the main app container */
        .stApp {
            margin: 0;
            padding: 0;
            width: 100%;
        }
        
        /* Map container adjustments */
        .stMap {
            height: 70vh !important;
            min-height: 500px;
            margin-bottom: 1rem;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            overflow: hidden;
        }
        
        /* Fullscreen mode adjustments */
        .folium-map {
            width: 100% !important;
            height: 100% !important;
        }
        
        /* Fix for Folium container */
        iframe {
            width: 100% !important;
            min-height: 500px !important;
        }
        
        /* Adjust column layout */
        .st-eb {
            padding: 0 0.5rem;
        }
        
        /* Better spacing for mobile */
        @media (max-width: 768px) {
            .stMap {
                height: 60vh !important;
                min-height: 400px;
            }
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
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.header("Hawaii Map")
        # Create and display the map
        map_obj = create_map()
        if map_obj:
            st_folium(
                map_obj,
                width=800,
                height=600,
                key="hawaii_map",
                returned_objects=[],
                use_container_width=True
            )
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
