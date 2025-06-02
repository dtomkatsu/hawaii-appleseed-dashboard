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
        
        # Get session state values
        active_layer = st.session_state.get('active_layer', 'State Boundary')
        selected_variable = st.session_state.get('selected_variable', 'poverty_rate')
        color_scheme = st.session_state.get('color_scheme', 'YlOrRd')
        show_labels = st.session_state.get('show_labels', True)
        
        # Initialize session state for map clicks if it doesn't exist
        if 'map_last_clicked' not in st.session_state:
            st.session_state.map_last_clicked = None
            st.session_state.map_clicked_data = None
            st.session_state.map_clicked_feature = None
        
        logger.debug(f"Creating map view with active_layer: {active_layer}, selected_variable: {selected_variable}")
        
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
            
            # Generate a stable key for the map that doesn't change with clicks
            map_key = f"map_{active_layer}_{selected_variable}_{color_scheme}_{show_labels}"
            
            # Create a container for the popup info that will be displayed below the map
            popup_container = st.container()
            
            # Display the map using st_folium with proper error handling
            logger.debug("Displaying map with st_folium")
            try:
                # Create a container for the map with styling
                st.markdown("""
                <div class="map-container" style="border: 1px solid rgba(94, 82, 64, 0.2); border-radius: 8px; overflow: hidden;">
                </div>
                """, unsafe_allow_html=True)
                
                # Display the map with the stable key
                map_data = st_folium(
                    m,
                    width=800,
                    height=600,
                    returned_objects=["last_clicked"],
                    use_container_width=True,
                    key=map_key  # Use a consistent key to prevent reloads
                )
                logger.debug("Map display complete")
                
                # Get the current click data
                current_clicked = map_data.get('last_clicked')
                
                # Process the click if it's new
                if current_clicked is not None and current_clicked != st.session_state.map_last_clicked:
                    # Update session state with the new click
                    st.session_state.map_last_clicked = current_clicked
                    
                    # Log that we're processing this click
                    logger.debug(f"Processing click at lat: {current_clicked.get('lat')}, lng: {current_clicked.get('lng')}")
                    
                    clicked_lat = current_clicked.get('lat')
                    clicked_lng = current_clicked.get('lng')
                    
                    # Find the clicked geographic feature
                    if clicked_lat and clicked_lng:
                        # Get the data loader from the map builder
                        data_loader = map_builder.data_loader
                        
                        # Get the geographic level from the active layer
                        geo_level_map = {
                            'State Boundary': 'state',
                            'Counties': 'county',
                            'House Districts': 'house',
                            'Senate Districts': 'senate'
                        }
                        geo_level_short = geo_level_map.get(active_layer, 'state')
                        
                        logger.debug(f"Active layer: {active_layer}, geo_level_short: {geo_level_short}, selected_variable: {selected_variable}")
                        
                        # Get the data for the active layer
                        df = data_loader.get_data(geo_level_short)
                        
                        # Find the feature that contains the clicked point
                        clicked_feature = map_builder.find_feature_at_point(clicked_lat, clicked_lng, geo_level_short)
                        logger.debug(f"Clicked at lat: {clicked_lat}, lng: {clicked_lng}, found feature: {clicked_feature is not None}")
                        
                        # If no feature found, try with all available geographic levels
                        if clicked_feature is None:
                            for level in ['state', 'county', 'senate', 'house']:
                                if level != geo_level_short:  # Skip the already checked level
                                    logger.debug(f"Trying to find feature in {level} layer")
                                    clicked_feature = map_builder.find_feature_at_point(clicked_lat, clicked_lng, level)
                                    if clicked_feature is not None:
                                        # Update geo_level_short to match the found feature
                                        geo_level_short = level
                                        logger.debug(f"Found feature in {level} layer")
                                        break
                        
                        if clicked_feature:
                            # Get feature properties
                            properties = clicked_feature.get('properties', {})
                            feature_id = properties.get('GEOID') or properties.get('geoid')
                            logger.debug(f"Found feature with ID: {feature_id}, properties: {properties}")
                            
                            # Load the data for this geographic level
                            df = data_loader.load_acs_data(geo_level_short)
                            
                            if df is not None and feature_id:
                                logger.debug(f"Loaded data for {geo_level_short}, shape: {df.shape}")
                                logger.debug(f"Data columns: {df.columns.tolist()}")
                                
                                # Try different ID formats to match with the data
                                possible_ids = [
                                    feature_id,  # Full GEOID
                                    feature_id.lstrip('0'),  # GEOID with leading zeros stripped
                                    feature_id.split('-')[-1] if '-' in feature_id else feature_id,  # District number only
                                ]
                                
                                logger.debug(f"Trying to match feature ID with possible IDs: {possible_ids}")
                                
                                # Find matching row
                                for pid in possible_ids:
                                    try:
                                        matches = df[df['geoid'].astype(str).str.strip() == str(pid)]
                                        if not matches.empty:
                                            data_row = matches.iloc[0].to_dict()
                                            logger.debug(f"Found matching data row with ID: {pid}")
                                            break
                                    except Exception as e:
                                        logger.error(f"Error matching ID {pid}: {str(e)}")
                                        continue
                            
                            # Update the popup container with feature info
                            with popup_container:
                                # Get the feature name based on the data row or properties
                                if data_row is not None and 'name' in data_row:
                                    feature_name = data_row['name']
                                else:
                                    # Try to get name from properties
                                    feature_name = properties.get('name', '')
                                    if not feature_name:
                                        # Try common name fields based on geographic level
                                        name_field_map = {
                                            'state': 'state_name',
                                            'county': 'county_name',
                                            'house': 'house_name',
                                            'senate': 'senate_name'
                                        }
                                        name_field = name_field_map.get(geo_level_short, '')
                                        feature_name = properties.get(name_field, f"{geo_level_short.title()} Feature")
                                
                                st.markdown(f"""<div class="county-info">
                                    <h4>📍 {feature_name}</h4>
                                </div>""", unsafe_allow_html=True)
                                
                                if data_row is not None:
                                    # Create a styled container for the data
                                    st.markdown("<div class='data-summary-container'>", unsafe_allow_html=True)
                                    
                                    # Highlight the selected variable first
                                    if selected_variable in data_row and not pd.isna(data_row[selected_variable]):
                                        value = data_row[selected_variable]
                                        # Get the display name for the variable
                                        var_display_name = None
                                        if hasattr(map_builder, 'available_variables') and map_builder.available_variables:
                                            var_display_name = map_builder.available_variables.get(selected_variable)
                                        
                                        if not var_display_name:
                                            # Fallback to a formatted version of the variable name
                                            var_display_name = selected_variable.replace('_', ' ').title()
                                            
                                        logger.debug(f"Selected variable: {selected_variable}, display name: {var_display_name}, value: {value}")
                                        
                                        # Format the value based on the variable type
                                        if selected_variable in ['poverty_rate', 'unemployment_rate', 'bachelors_degree', 'no_health_insurance', 'renter_occupied', 'rent_burden_rate']:
                                            formatted_value = f"{value:.1f}%"
                                        elif selected_variable in ['median_income', 'median_rent', 'median_home_value']:
                                            formatted_value = f"${value:,.0f}"
                                        elif selected_variable == 'population':
                                            formatted_value = f"{value:,.0f}"
                                        elif selected_variable == 'median_age':
                                            formatted_value = f"{value:.1f} years"
                                        else:
                                            formatted_value = str(value)
                                        
                                        # Display the selected variable prominently
                                        st.subheader(var_display_name)
                                        st.markdown(f"<h2 style='color: #21808d; margin-top: 0;'>{formatted_value}</h2>", unsafe_allow_html=True)
                                        st.markdown("<hr style='margin: 15px 0;'>", unsafe_allow_html=True)
                                    
                                    # Group metrics by category for better organization
                                    metric_categories = {
                                        'Demographics': {
                                            'population': 'Population',
                                            'median_age': 'Median Age'
                                        },
                                        'Economic': {
                                            'poverty_rate': 'Poverty Rate',
                                            'median_income': 'Median Income',
                                            'unemployment_rate': 'Unemployment Rate'
                                        },
                                        'Housing': {
                                            'median_rent': 'Median Rent',
                                            'median_home_value': 'Median Home Value',
                                            'renter_occupied': 'Renter-Occupied Housing',
                                            'rent_burden_rate': 'Rent Burden Rate'
                                        },
                                        'Education & Health': {
                                            'bachelors_degree': 'Bachelor\'s Degree or Higher',
                                            'no_health_insurance': 'No Health Insurance'
                                        }
                                    }
                                    
                                    # Skip the selected variable since we already displayed it prominently
                                    skip_variable = selected_variable
                                    
                                    # Display metrics by category
                                    for category, metrics in metric_categories.items():
                                        # Check if any metrics in this category exist in the data
                                        has_data = any(metric_key in data_row and not pd.isna(data_row[metric_key]) for metric_key in metrics if metric_key != skip_variable)
                                        
                                        if has_data:
                                            st.markdown(f"<h4 style='margin-bottom: 10px;'>{category}</h4>", unsafe_allow_html=True)
                                            
                                            # Create columns for metrics in this category
                                            metrics_to_display = {k: v for k, v in metrics.items() if k != skip_variable}
                                            if metrics_to_display:
                                                cols = st.columns(min(2, len(metrics_to_display)))
                                                
                                                col_idx = 0
                                                for metric_key, metric_label in metrics_to_display.items():
                                                    if metric_key in data_row and not pd.isna(data_row[metric_key]):
                                                        value = data_row[metric_key]
                                                        
                                                        # Format the value based on the metric type
                                                        if metric_key in ['poverty_rate', 'unemployment_rate', 'bachelors_degree', 'no_health_insurance', 'renter_occupied', 'rent_burden_rate']:
                                                            formatted_value = f"{value:.1f}%"
                                                        elif metric_key in ['median_income', 'median_rent', 'median_home_value']:
                                                            formatted_value = f"${value:,.0f}"
                                                        elif metric_key == 'population':
                                                            formatted_value = f"{value:,.0f}"
                                                        elif metric_key == 'median_age':
                                                            formatted_value = f"{value:.1f} years"
                                                        else:
                                                            formatted_value = str(value)
                                                        
                                                        # Display in alternating columns
                                                        with cols[col_idx % len(cols)]:
                                                            st.metric(metric_label, formatted_value)
                                                            col_idx += 1
                                    
                                    # Format the value based on the variable type
                                    if selected_variable in ['poverty_rate', 'unemployment_rate', 'bachelors_degree', 'no_health_insurance', 'renter_occupied', 'rent_burden_rate']:
                                        formatted_value = f"{value:.1f}%"
                                    elif selected_variable in ['median_income', 'median_rent', 'median_home_value']:
                                        formatted_value = f"${value:,.0f}"
                                    elif selected_variable == 'population':
                                        formatted_value = f"{value:,.0f}"
                                    elif selected_variable == 'median_age':
                                        formatted_value = f"{value:.1f} years"
                                    else:
                                        formatted_value = str(value)
                                    
                                    # Display the selected variable prominently
                                    st.subheader(var_display_name)
                                    st.markdown(f"<h2 style='color: #21808d; margin-top: 0;'>{formatted_value}</h2>", unsafe_allow_html=True)
                                    st.markdown("<hr style='margin: 15px 0;'>", unsafe_allow_html=True)
                                
                                # Group metrics by category for better organization
                                metric_categories = {
                                    'Demographics': {
                                        'population': 'Population',
                                        'median_age': 'Median Age'
                                    },
                                    'Economic': {
                                        'poverty_rate': 'Poverty Rate',
                                        'median_income': 'Median Income',
                                        'unemployment_rate': 'Unemployment Rate'
                                    },
                                    'Housing': {
                                        'median_rent': 'Median Rent',
                                        'median_home_value': 'Median Home Value',
                                        'renter_occupied': 'Renter-Occupied Housing',
                                        'rent_burden_rate': 'Rent Burden Rate'
                                    },
                                    'Education & Health': {
                                        'bachelors_degree': 'Bachelor\'s Degree or Higher',
                                        'no_health_insurance': 'No Health Insurance'
                                    }
                                }
                                
                                # Skip the selected variable since we already displayed it prominently
                                skip_variable = selected_variable
                                
                                # Display metrics by category
                                for category, metrics in metric_categories.items():
                                    # Check if any metrics in this category exist in the data
                                    has_data = any(metric_key in data_row and not pd.isna(data_row[metric_key]) for metric_key in metrics if metric_key != skip_variable)
                                    
                                    if has_data:
                                        st.markdown(f"<h4 style='margin-bottom: 10px;'>{category}</h4>", unsafe_allow_html=True)
                                        
                                        # Create columns for metrics in this category
                                        metrics_to_display = {k: v for k, v in metrics.items() if k != skip_variable}
                                        if metrics_to_display:
                                            cols = st.columns(min(2, len(metrics_to_display)))
                                            
                                            col_idx = 0
                                            for metric_key, metric_label in metrics_to_display.items():
                                                if metric_key in data_row and not pd.isna(data_row[metric_key]):
                                                    value = data_row[metric_key]
                                                    
                                                    # Format the value based on the metric type
                                                    if metric_key in ['poverty_rate', 'unemployment_rate', 'bachelors_degree', 'no_health_insurance', 'renter_occupied', 'rent_burden_rate']:
                                                        formatted_value = f"{value:.1f}%"
                                                    elif metric_key in ['median_income', 'median_rent', 'median_home_value']:
                                                        formatted_value = f"${value:,.0f}"
                                                    elif metric_key == 'population':
                                                        formatted_value = f"{value:,.0f}"
                                                    elif metric_key == 'median_age':
                                                        formatted_value = f"{value:.1f} years"
                                                    else:
                                                        formatted_value = str(value)
                                                    
                                                    # Display in alternating columns
                                                    with cols[col_idx % len(cols)]:
                                                        st.metric(metric_label, formatted_value)
                                                        col_idx += 1
                            
                            st.markdown("</div>", unsafe_allow_html=True)
                        else:
                            st.info("No demographic data available for this area.")
                    else:
                        # If no feature was clicked, show the coordinates
                        with popup_container:
                            st.markdown(f"""<div class="county-info">
                                <h4>📍 Coordinates: {clicked_lat:.4f}, {clicked_lng:.4f}</h4>
                                <p>No geographic feature found at this location.</p>
                            </div>""", unsafe_allow_html=True)
                else:
                    # Display default info in the popup container
                    with popup_container:
                        st.markdown("""<div class="county-info">
                            <h4>👆 Click on the map to see details</h4>
                            <p>Select a geographic area to view demographic and economic data.</p>
                        </div>""", unsafe_allow_html=True)
                
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
