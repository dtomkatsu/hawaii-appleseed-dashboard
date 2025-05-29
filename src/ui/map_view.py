"""Map view components for the Hawaii Appleseed Dashboard."""
import streamlit as st
import folium
from streamlit_folium import folium_static
import logging
from typing import Dict, Any, Optional

from src.maps.builder import MapBuilder

logger = logging.getLogger(__name__)

def create_map_view(active_layer: str, debug_info: bool = False) -> None:
    """
    Create and display the map view with session state for better performance.
    
    Args:
        active_layer: The name of the active layer to display
        debug_info: Whether to show debug information
    """
    try:
        # Initialize session state for map if it doesn't exist
        if 'map_object' not in st.session_state:
            st.session_state.map_object = None
        if 'active_layer' not in st.session_state:
            st.session_state.active_layer = None
        
        # Create a container for the map
        map_container = st.container()
        
        with map_container:
            # Only recreate the map if necessary
            if (st.session_state.map_object is None or 
                st.session_state.active_layer != active_layer):
                
                with st.spinner('Loading map...'):
                    map_builder = MapBuilder(active_layer=active_layer)
                    st.session_state.map_object = map_builder.create_map()
                    st.session_state.active_layer = active_layer
            
            m = st.session_state.map_object
            
            if m is None:
                st.error("Failed to create map. Please check the logs for details.")
                return
            
            # Display debug information if enabled
            if debug_info:
                st.markdown("### Debug Information")
                
                # Get map bounds from various possible attributes
                bounds = None
                if hasattr(m, 'used_bounds'):
                    bounds = m.used_bounds
                elif hasattr(m, 'hawaii_bounds'):
                    bounds = m.hawaii_bounds
                
                # Create debug info dictionary
                debug_info_dict = {
                    "active_layer": active_layer,
                    "map_type": type(m).__name__,
                    "map_bounds": bounds if bounds else "Not available",
                    "layers_loaded": list(m._children.keys()) if hasattr(m, '_children') else 'No layers',
                    "session_state_keys": list(st.session_state.keys())
                }
                
                # Log debug info to file
                with open('debug.log', 'a') as f:
                    f.write(f"\nMap Debug Info: {debug_info_dict}\n")
                
                # Display debug info in UI
                st.json(debug_info_dict)
            
            # Display the map
            st.markdown("### Map View")
            folium_static(m, width=1200, height=800)
                
    except Exception as e:
        logger.error(f"Error in map view: {str(e)}", exc_info=True)
        st.error(f"An error occurred while creating the map: {str(e)}")

def create_data_summary() -> None:
    """Create a data summary view."""
    st.markdown("### Data Summary")
    st.write("Select a layer from the sidebar to view data.")
