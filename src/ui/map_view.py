"""Map view components for the Hawaii Appleseed Dashboard."""
import streamlit as st
import folium
from streamlit_folium import st_folium
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
    Create and display a map view with layer controls and variable selection in the sidebar.
    """
    try:
        logger.debug("Starting map view creation")
        
        # Initialize data loader to get available variables
        from src.data.data_loader import DataLoader
        data_loader = DataLoader()
        available_variables = data_loader.get_available_variables()
        
        # Add variable selection to the sidebar
        st.sidebar.markdown("### Data Options")
        
        # Default variable to show
        if 'selected_variable' not in st.session_state:
            st.session_state.selected_variable = 'poverty_rate'
        
        # Create a dropdown for variable selection
        selected_variable = st.sidebar.selectbox(
            "Select variable to display:",
            options=list(available_variables.keys()),
            format_func=lambda x: available_variables[x],
            index=list(available_variables.keys()).index(st.session_state.selected_variable),
            key="variable_selector"
        )
        
        # Update session state
        st.session_state.selected_variable = selected_variable
        
        # Add layer controls to the sidebar
        st.sidebar.markdown("### Map Layers")
        
        # Use checkboxes for multiple layer selection
        st.sidebar.markdown("**Select layers to display:**")
        
        # Default layers to show
        if 'active_layers' not in st.session_state:
            st.session_state.active_layers = ['State Boundary']
        
        # Layer options with default visibility
        layer_options = {
            'State Boundary': st.sidebar.checkbox(
                'State Boundary', 
                value='State Boundary' in st.session_state.active_layers,
                key='state_layer'
            ),
            'County Boundaries': st.sidebar.checkbox(
                'County Boundaries',
                value='County Boundaries' in st.session_state.active_layers,
                key='county_layer'
            ),
            'State House Districts': st.sidebar.checkbox(
                'State House Districts',
                value='State House Districts' in st.session_state.active_layers,
                key='house_layer'
            ),
            'State Senate Districts': st.sidebar.checkbox(
                'State Senate Districts',
                value='State Senate Districts' in st.session_state.active_layers,
                key='senate_layer'
            )
        }
        
        # Update active layers based on checkboxes
        active_layers = [layer for layer, active in layer_options.items() if active]
        st.session_state.active_layers = active_layers
        
        # Create a container for the map
        with st.container():
            # Display selected variable info
            st.markdown(f"### Map View: {available_variables[selected_variable]}")
            
            # Create the map builder with active layers and selected variable
            logger.debug(f"Creating map builder with variable: {selected_variable}")
            map_builder = MapBuilder(active_layers=active_layers, selected_variable=selected_variable)
            
            # Create the map
            logger.debug("Building map")
            m = map_builder.create_map()
            
            if m is None:
                logger.error("Map creation failed, returned None")
                st.error("Failed to create map. Please check the logs for details.")
                return
            
            logger.debug(f"Map created successfully: {type(m).__name__}")
            
            # Display the map using st_folium with proper error handling
            logger.debug("Displaying map with st_folium")
            try:
                # Create a container for the map
                map_container = st.empty()
                
                # Display the map in the container
                with map_container.container():
                    st_folium(
                        m,
                        width=800,
                        height=600,
                        returned_objects=[],
                        use_container_width=True
                    )
                logger.debug("Map display complete")
                
            except Exception as e:
                logger.error(f"Error displaying map: {str(e)}")
                logger.error(traceback.format_exc())
                st.error("An error occurred while displaying the map. Please check the logs for details.")
                
                # Fallback: Try to display a simple map
                try:
                    st.warning("Falling back to basic map display...")
                    m = folium.Map(location=[20.8, -157.3], zoom_start=7)
                    st_folium(m, width=800, height=600)
                except Exception as fallback_error:
                    logger.error(f"Fallback map display failed: {str(fallback_error)}")
                    st.error("Failed to display the map. Please try again later.")
            
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
