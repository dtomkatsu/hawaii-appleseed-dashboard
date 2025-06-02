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
    Create and display a map view with the selected layer and variable.
    """
    try:
        logger.debug("Starting map view creation")
        
        # Initialize data loader to get available variables
        from src.data.data_loader import DataLoader
        data_loader = DataLoader()
        available_variables = data_loader.get_available_variables()
        
        # Get values from session state (set in sidebar)
        active_layer = st.session_state.get('active_layer', 'State Boundary')
        selected_variable = st.session_state.get('selected_variable', 'poverty_rate')
        color_scheme = st.session_state.get('color_scheme', 'YlOrRd')
        show_labels = st.session_state.get('show_labels', True)
        
        # Create a container for the map with enhanced styling
        with st.container():
            # Display selected layer and variable info with improved formatting
            variable_display_name = available_variables.get(selected_variable, selected_variable.replace('_', ' ').title())
            
            st.markdown(f"### {active_layer}: {variable_display_name}")
            st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)
            
            # Create the map builder with the active layer, selected variable and color scheme
            logger.debug(f"Creating map builder with variable: {selected_variable}, color scheme: {color_scheme}")
            map_builder = MapBuilder(
                active_layers=[active_layer], 
                selected_variable=selected_variable,
                color_scheme=color_scheme,
                show_labels=show_labels
            )
            
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
                # Create a container for the map with styling
                st.markdown("""
                <div class="map-container" style="border: 1px solid rgba(94, 82, 64, 0.2); border-radius: 8px; overflow: hidden;">
                </div>
                """, unsafe_allow_html=True)
                
                # Display the map
                map_data = st_folium(
                    m,
                    width=800,
                    height=600,
                    returned_objects=["last_clicked"],
                    use_container_width=True
                )
                logger.debug("Map display complete")
                
                # Display clicked area information if available
                if map_data.get('last_clicked') is not None:
                    clicked_lat = map_data['last_clicked'].get('lat')
                    clicked_lng = map_data['last_clicked'].get('lng')
                    if clicked_lat and clicked_lng:
                        st.markdown("""
                        <div class="county-info">
                            <h4>📍 Selected Area Information</h4>
                            <p>Click on the map to see detailed information about specific areas.</p>
                        </div>
                        """, unsafe_allow_html=True)
                
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
                    "active_layer": active_layer,
                    "selected_variable": selected_variable,
                    "color_scheme": color_scheme
                }
                st.json(map_info)
                logger.debug(f"Debug info: {map_info}")
                
    except Exception as e:
        logger.error(f"Error in map view: {str(e)}")
        logger.error(traceback.format_exc())
        st.error(f"An error occurred while creating the map: {str(e)}")

def create_data_summary() -> None:
    """Create a data summary view with metric cards."""
    st.markdown("### Data Summary")
    
    # Get data for the selected area
    try:
        from src.data.data_loader import DataLoader
        data_loader = DataLoader()
        
        # Get data based on active layer and selected variable
        active_layer = st.session_state.get('active_layer', 'State Boundary')
        selected_variable = st.session_state.get('selected_variable', 'poverty_rate')
        
        # Create metric cards in a grid layout
        col1, col2 = st.columns(2)
        
        with col1:
            # Poverty Rate Card
            st.markdown("""
            <div class="metric-card poverty-card">
                <h4>Poverty Rate</h4>
                <div class="metric-value">12.5%</div>
                <div class="metric-context">Statewide average</div>
            </div>
            """, unsafe_allow_html=True)
            
            # Median Income Card
            st.markdown("""
            <div class="metric-card income-card">
                <h4>Median Household Income</h4>
                <div class="metric-value">$83,173</div>
                <div class="metric-context">Statewide average</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            # Population Card
            st.markdown("""
            <div class="metric-card population-card">
                <h4>Total Population</h4>
                <div class="metric-value">1,455,271</div>
                <div class="metric-context">2020 Census</div>
            </div>
            """, unsafe_allow_html=True)
            
            # Housing Card
            st.markdown("""
            <div class="metric-card housing-card">
                <h4>Median Home Value</h4>
                <div class="metric-value">$722,500</div>
                <div class="metric-context">Statewide average</div>
            </div>
            """, unsafe_allow_html=True)
        
        # Additional context section
        st.markdown("---")
        st.markdown("### Geographic Context")
        
        # Display geographic context based on active layer
        if active_layer == 'County Boundaries':
            st.markdown("""
            <div class="county-info">
                <p>Hawaii has 5 counties: Hawaii, Honolulu, Kalawao, Kauai, and Maui.</p>
                <p>Honolulu County is the most populous with over 1 million residents.</p>
            </div>
            """, unsafe_allow_html=True)
        elif active_layer == 'State Senate Districts':
            st.markdown("""
            <div class="county-info">
                <p>Hawaii has 25 State Senate districts.</p>
                <p>Each district represents approximately 50,000 residents.</p>
            </div>
            """, unsafe_allow_html=True)
        elif active_layer == 'State House Districts':
            st.markdown("""
            <div class="county-info">
                <p>Hawaii has 51 State House districts.</p>
                <p>Each district represents approximately 24,000 residents.</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="county-info">
                <p>Hawaii is the 50th state of the United States, consisting of 8 main islands.</p>
                <p>The state has a total land area of approximately 10,931 square miles.</p>
            </div>
            """, unsafe_allow_html=True)
            
    except Exception as e:
        logger.error(f"Error creating data summary: {str(e)}")
        logger.error(traceback.format_exc())
        st.error("Unable to load data summary. Please try again later.")
