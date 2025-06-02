"""Leaflet Map View for Hawaii Appleseed Dashboard."""
import streamlit as st
import pandas as pd
import json
import logging
from pathlib import Path
import sys

# Add the parent directory to the path
sys.path.append(str(Path(__file__).parent.parent.parent))

# Import local modules
from src.data.data_loader import DataLoader
# Remove MapBuilder import as we're not using it in this implementation
from src.ui.leaflet_component import create_leaflet_map

# Set up logging
logger = logging.getLogger(__name__)

def load_geojson(layer_name):
    """Load GeoJSON data for the specified layer."""
    # Map layer names to file paths
    layer_files = {
        'State Boundary': 'hawaii_state_boundary.geojson',
        'Counties': 'hawaii_county_boundaries.geojson',
        'House Districts': 'Hawaii_State_House_Districts_2022.geojson',
        'Senate Districts': 'Hawaii_State_Senate_Districts_2022.geojson'
    }
    
    if layer_name not in layer_files:
        logger.error(f"Unknown layer: {layer_name}")
        return None
    
    # Construct the file path
    file_path = Path(__file__).parent.parent.parent / 'data' / 'Processed GeoJsons' / layer_files[layer_name]
    
    try:
        with open(file_path, 'r') as f:
            geojson_data = json.load(f)
            logger.info(f"Successfully loaded GeoJSON for {layer_name} from {file_path}")
            return geojson_data
    except Exception as e:
        logger.error(f"Error loading GeoJSON for {layer_name}: {str(e)}")
        return None

def create_leaflet_map_view(debug_info: bool = False) -> None:
    """Create the Leaflet map view."""
    logger.debug("Building Leaflet map view")
    
    # Get user selections from session state or initialize them if not present
    if 'active_layer' not in st.session_state:
        st.session_state['active_layer'] = 'State Boundary'
    if 'selected_variable' not in st.session_state:
        st.session_state['selected_variable'] = 'poverty_rate'
    if 'color_scheme' not in st.session_state:
        st.session_state['color_scheme'] = 'blue'
        
    active_layer = st.session_state['active_layer']
    selected_variable = st.session_state['selected_variable']
    color_scheme = st.session_state['color_scheme']
    
    # Load GeoJSON data for the selected layer
    geojson_data = load_geojson(active_layer)
    
    if geojson_data is None:
        st.error(f"Failed to load GeoJSON data for {active_layer}")
        return
    
    # Load ACS data
    data_loader = DataLoader()
    
    # Map geo levels to their data loader equivalents
    geo_level_map = {
        'State Boundary': 'state',
        'Counties': 'county',
        'House Districts': 'house',
        'Senate Districts': 'senate'
    }
    
    geo_level = geo_level_map.get(active_layer, 'state')
    
    # Get data for the current geographic level
    acs_data = data_loader.get_data(geo_level)
    
    if acs_data is not None:
        # Merge ACS data with GeoJSON
        for feature in geojson_data['features']:
            # Get the feature ID based on the geo level
            if geo_level == 'state':
                feature_id = 'Hawaii'
            elif geo_level == 'county':
                feature_id = feature['properties'].get('NAME')
            elif geo_level == 'house':
                feature_id = f"District {feature['properties'].get('DISTRICT')}"
            elif geo_level == 'senate':
                feature_id = f"District {feature['properties'].get('DISTRICT')}"
            else:
                feature_id = None
            
            # Store the ID in the properties
            feature['properties']['id'] = feature_id
            
            # Find matching data
            if feature_id:
                # Check if 'name' column exists, otherwise try 'NAME' or create a name field
                name_col = 'name' if 'name' in acs_data.columns else 'NAME' if 'NAME' in acs_data.columns else None
                
                if name_col:
                    matching_data = acs_data[acs_data[name_col] == feature_id].to_dict('records')
                else:
                    # If no name column exists, try matching by geoid or district number
                    if 'geoid' in acs_data.columns and 'GEOID' in feature['properties']:
                        matching_data = acs_data[acs_data['geoid'] == feature['properties']['GEOID']].to_dict('records')
                    elif 'district' in acs_data.columns and 'DISTRICT' in feature['properties']:
                        matching_data = acs_data[acs_data['district'] == feature['properties']['DISTRICT']].to_dict('records')
                    else:
                        # No matching criteria found
                        matching_data = []
                
                if matching_data:
                    # Add ACS data to feature properties
                    for key, value in matching_data[0].items():
                        # Skip name/id fields as we already have them
                        if key not in ['name', 'NAME', 'geoid', 'GEOID', 'district', 'DISTRICT']:
                            feature['properties'][key] = value
    
    # Create map controls
    st.subheader("Map Controls")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        selected_layer = st.selectbox(
            "Geographic Layer",
            ['State Boundary', 'Counties', 'House Districts', 'Senate Districts'],
            index=['State Boundary', 'Counties', 'House Districts', 'Senate Districts'].index(active_layer),
            key="layer_selector"
        )
        if selected_layer != active_layer:
            st.session_state['active_layer'] = selected_layer
            st.rerun()
    
    with col2:
        selected_var = st.selectbox(
            "Data Variable",
            [
                'poverty_rate', 'median_income', 'unemployment_rate', 
                'population', 'median_home_value', 'college_educated_pct'
            ],
            index=['poverty_rate', 'median_income', 'unemployment_rate', 
                   'population', 'median_home_value', 'college_educated_pct'].index(selected_variable),
            key="variable_selector"
        )
        if selected_var != selected_variable:
            st.session_state['selected_variable'] = selected_var
            st.rerun()
    
    with col3:
        selected_color = st.selectbox(
            "Color Scheme",
            ['blue', 'green', 'red', 'purple'],
            index=['blue', 'green', 'red', 'purple'].index(color_scheme),
            key="color_selector"
        )
        if selected_color != color_scheme:
            st.session_state['color_scheme'] = selected_color
            st.rerun()
    
    # Create the Leaflet map
    st.subheader(f"{active_layer} Map")
    clicked_feature = create_leaflet_map(
        geojson_data=geojson_data,
        variable=selected_variable,
        color_scheme=color_scheme,
        height=500,
        key=f"map-{active_layer}-{selected_variable}-{color_scheme}"
    )
    
    # Handle clicked feature
    if clicked_feature:
        st.session_state['selected_feature_id'] = clicked_feature
        logger.debug(f"Feature clicked: {clicked_feature}")
    
    # Display feature details if a feature is selected
    if 'selected_feature_id' in st.session_state and st.session_state['selected_feature_id']:
        display_feature_details(
            st.session_state['selected_feature_id'],
            geojson_data,
            selected_variable
        )

def display_feature_details(feature_id, geojson_data, selected_variable):
    """Display detailed information for the selected feature."""
    # Find the feature in the GeoJSON data
    selected_feature = None
    for feature in geojson_data['features']:
        if feature['properties'].get('id') == feature_id:
            selected_feature = feature
            break
    
    if not selected_feature:
        return
    
    # Get properties
    properties = selected_feature['properties']
    
    # Create a feature detail card
    st.markdown("### Feature Details")
    
    with st.container():
        st.markdown(f"#### {properties.get('name', properties.get('NAME', feature_id))}")
        
        # Create tabs for different categories of data
        tab1, tab2, tab3, tab4 = st.tabs(["Demographics", "Economic", "Housing", "Education & Health"])
        
        with tab1:
            # Demographics tab
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Population", f"{properties.get('population', 'N/A'):,}")
                st.metric("White Alone (%)", f"{properties.get('white_alone_pct', 'N/A')}%")
            with col2:
                st.metric("Asian Alone (%)", f"{properties.get('asian_alone_pct', 'N/A')}%")
                st.metric("Native Hawaiian/PI (%)", f"{properties.get('native_hawaiian_pi_pct', 'N/A')}%")
        
        with tab2:
            # Economic tab
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Poverty Rate", f"{properties.get('poverty_rate', 'N/A')}%")
                st.metric("Median Income", f"${properties.get('median_income', 'N/A'):,}")
            with col2:
                st.metric("Unemployment Rate", f"{properties.get('unemployment_rate', 'N/A')}%")
                st.metric("SNAP Benefits (%)", f"{properties.get('snap_benefits_pct', 'N/A')}%")
        
        with tab3:
            # Housing tab
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Median Home Value", f"${properties.get('median_home_value', 'N/A'):,}")
                st.metric("Homeownership Rate", f"{properties.get('homeownership_rate', 'N/A')}%")
            with col2:
                st.metric("Rent Burden (%)", f"{properties.get('rent_burden_pct', 'N/A')}%")
                st.metric("Median Rent", f"${properties.get('median_rent', 'N/A'):,}")
        
        with tab4:
            # Education & Health tab
            col1, col2 = st.columns(2)
            with col1:
                st.metric("College Educated (%)", f"{properties.get('college_educated_pct', 'N/A')}%")
                st.metric("High School Graduate (%)", f"{properties.get('high_school_grad_pct', 'N/A')}%")
            with col2:
                st.metric("Health Insurance Coverage (%)", f"{properties.get('health_insurance_pct', 'N/A')}%")
                st.metric("Disability (%)", f"{properties.get('disability_pct', 'N/A')}%")

def create_data_summary():
    """Create a summary of the data."""
    st.subheader("Data Summary")
    
    # Get the active layer and selected variable
    active_layer = st.session_state.get('active_layer', 'State Boundary')
    selected_variable = st.session_state.get('selected_variable', 'poverty_rate')
    
    # Load data
    data_loader = DataLoader()
    
    # Map geo levels to their data loader equivalents
    geo_level_map = {
        'State Boundary': 'state',
        'Counties': 'county',
        'House Districts': 'house',
        'Senate Districts': 'senate'
    }
    
    geo_level = geo_level_map.get(active_layer, 'state')
    
    # Get data for the current geographic level
    data = data_loader.get_data(geo_level)
    
    # Ensure we have a name column for display
    if data is not None and 'name' not in data.columns:
        if 'NAME' in data.columns:
            data['name'] = data['NAME']
        elif 'geoid' in data.columns:
            data['name'] = 'Area ' + data['geoid'].astype(str)
        elif 'district' in data.columns:
            data['name'] = 'District ' + data['district'].astype(str)
    
    if data is not None:
        # Create summary statistics
        st.markdown("#### Summary Statistics")
        
        # Calculate summary statistics
        if 'poverty_rate' in data.columns:
            avg_poverty = data['poverty_rate'].mean()
            st.metric("Average Poverty Rate", f"{avg_poverty:.1f}%")
        
        if 'median_income' in data.columns:
            avg_income = data['median_income'].mean()
            st.metric("Average Median Income", f"${avg_income:,.0f}")
        
        if 'population' in data.columns:
            total_pop = data['population'].sum()
            st.metric("Total Population", f"{total_pop:,}")
        
        # Display the data table
        st.markdown("#### Data Table")
        st.dataframe(data)
        
        # Add download button
        csv = data.to_csv(index=False)
        st.download_button(
            label="Download Data as CSV",
            data=csv,
            file_name=f"hawaii_{geo_level}_data.csv",
            mime="text/csv",
            key="data_summary_download_button"
        )
    else:
        st.warning(f"No data available for {active_layer}")
