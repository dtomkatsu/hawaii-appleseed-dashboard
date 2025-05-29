"""Map view components for the Hawaii Appleseed Dashboard."""
import streamlit as st
import folium
from streamlit_folium import folium_static
import logging
import traceback
import os

from src.maps.builder import MapBuilder

# Configure logging to write to a file
log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'map_debug.log')

# Set up file handler
file_handler = logging.FileHandler(log_file)
file_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)

# Get logger and add handler
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(file_handler)

def create_map_view(debug_info: bool = False) -> None:
    """
    Create and display a map view with layer controls in the sidebar.
    """
    try:
        logger.debug("Starting map view creation")
        
        # Add layer controls to the sidebar
        st.sidebar.markdown("### Map Layers")
        
        # Use radio buttons for single-layer selection
        layer_options = [
            "State Boundary",
            "County Boundaries",
            "State House Districts",
            "State Senate Districts"
        ]
        
        selected_layer = st.sidebar.radio(
            "Select a layer to display:",
            options=layer_options,
            index=0,  # Default to State Boundary
            key="layer_selector"
        )
        
        # Map the selected layer to active_layers format
        layer_mapping = {
            "State Boundary": ["State"],
            "County Boundaries": ["Counties"],
            "State House Districts": ["House"],
            "State Senate Districts": ["Senate"]
        }
        
        active_layers = layer_mapping[selected_layer]
        
        # Create a container for the map
        with st.container():
            st.markdown("### Map View")
            
            # Create the map with active layers
            logger.debug("Creating map builder")
            map_builder = MapBuilder(active_layers=active_layers)
            logger.debug("Building map")
            m = map_builder.create_map()
            
            if m is None:
                logger.error("Map creation failed, returned None")
                st.error("Failed to create map. Please check the logs for details.")
                return
            
            logger.debug(f"Map created successfully: {type(m).__name__}")
            
            # Display the map using folium_static
            logger.debug("Displaying map with folium_static")
            folium_static(m, width=800, height=600)
            logger.debug("Map display complete")
            
            # Show debug info if enabled
            if debug_info:
                st.markdown("### Debug Information")
                map_info = {
                    "map_type": type(m).__name__,
                    "center": m.location if hasattr(m, 'location') else "Unknown",
                    "zoom": m.options.get('zoom') if hasattr(m, 'options') else "Unknown",
                }
                st.json(map_info)
                logger.debug(f"Debug info: {map_info}")
                
    except Exception as e:
        logger.error(f"Error in map view: {str(e)}")
        logger.error(traceback.format_exc())
        st.error(f"An error occurred while creating the map: {str(e)}")

def create_data_summary() -> None:
    """Create a data summary view."""
    st.markdown("### Data Summary")
    st.write("Select a layer from the sidebar to view data.")
