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
    if 'selected_variable' not in st.session_state or st.session_state['selected_variable'] not in ['poverty_rate', 'median_income', 'unemployment_rate', 'population', 'median_home_value', 'college_educated_pct', 'rent_burden_rate']:
        st.session_state['selected_variable'] = 'poverty_rate'
    if 'color_scheme' not in st.session_state:
        st.session_state['color_scheme'] = 'blue'
        
    active_layer = st.session_state['active_layer']
    selected_variable = st.session_state['selected_variable']
    color_scheme = st.session_state['color_scheme']
    
    # Debug: Print the selected variable
    logger.info(f"Selected variable: {selected_variable}")
    logger.info(f"Active layer: {active_layer}")
    logger.info(f"Color scheme: {color_scheme}")
    
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
        # Debug: Print ACS data columns and first row
        logger.info(f"ACS data columns: {acs_data.columns.tolist()}")
        if not acs_data.empty:
            logger.info(f"First row of ACS data: {acs_data.iloc[0].to_dict()}")
            
        # Special debug for county data
        if geo_level == 'county':
            logger.info(f"COUNTY DATA DEBUG: Full dataframe:\n{acs_data}")
            logger.info(f"COUNTY DATA DEBUG: Column types:\n{acs_data.dtypes}")
            if 'poverty_rate' in acs_data.columns:
                logger.info(f"COUNTY DATA DEBUG: Poverty rate values:\n{acs_data['poverty_rate']}")
            else:
                logger.info(f"COUNTY DATA DEBUG: 'poverty_rate' column not found in county data")
                logger.info(f"COUNTY DATA DEBUG: Available columns: {acs_data.columns.tolist()}")
                
            # Check for related columns that might be used to calculate poverty rate
            for col in ['below_poverty', 'total_population']:
                if col in acs_data.columns:
                    logger.info(f"COUNTY DATA DEBUG: {col} values:\n{acs_data[col]}")
                else:
                    logger.info(f"COUNTY DATA DEBUG: '{col}' column not found in county data")
                    
            # Debug the exact format of NAME column values to help with matching
            name_col_debug = 'name' if 'name' in acs_data.columns else 'NAME' if 'NAME' in acs_data.columns else None
            if name_col_debug:
                logger.info(f"COUNTY DATA DEBUG: Exact format of {name_col_debug} column values:\n{acs_data[name_col_debug].tolist()}")
        
        # Merge ACS data with GeoJSON
        for feature in geojson_data['features']:
            # Get the feature ID based on the geo level
            if geo_level == 'state':
                feature_id = 'Hawaii'
            elif geo_level == 'county':
                # Get county name from county_name property (not NAME)
                county_name = feature['properties'].get('county_name')
                logger.info(f"County name from GeoJSON: {county_name}")
                
                # Set display name (special case for Oahu -> Honolulu)
                display_name = 'Honolulu' if county_name == 'Oahu' else county_name
                feature['properties']['display_name'] = display_name
                
                # Handle special case for Oahu/Honolulu data matching
                if county_name == 'Oahu':
                    logger.info("Special case: Oahu -> Honolulu for data matching")
                    # Use all possible formats for data matching
                    formats = [
                        'Honolulu',
                        'Honolulu County',
                        'Honolulu County, Hawaii',
                        '"Honolulu County, Hawaii"',
                        'Honolulu, Hawaii',
                        # Also keep original Oahu formats as fallback
                        county_name,
                        f"{county_name} County",
                        f"{county_name} County, Hawaii",
                        f"\"{county_name} County, Hawaii\"",
                        f"{county_name}, Hawaii"
                    ]
                else:
                    # Try different formats that might match the ACS data
                    formats = [
                        county_name,  # Original format (e.g., 'Hawaii')
                        f"{county_name} County",  # Add 'County' suffix
                        f"{county_name} County, Hawaii",  # Add state
                        f"\"{county_name} County, Hawaii\"",  # Quoted format with state (matches CSV format)
                        f"{county_name}, Hawaii"  # Without 'County' but with state
                    ]
                feature_id = formats  # Store all possible formats to try
            elif geo_level == 'house':
                # Extract district number from different possible property names
                district_num = None
                if 'DISTRICT' in feature['properties']:
                    district_num = feature['properties']['DISTRICT']
                elif 'house_id' in feature['properties']:
                    district_num = feature['properties']['house_id']
                elif 'house_name' in feature['properties'] and 'District' in feature['properties']['house_name']:
                    # Try to extract the number from the name (e.g., 'State House District 1')
                    import re
                    match = re.search(r'District (\d+)', feature['properties']['house_name'])
                    if match:
                        district_num = match.group(1)
                
                feature_id = f"State House District {district_num} (2022); Hawaii"
                # Also store a simpler display name
                feature['properties']['display_name'] = f"House District {district_num}"
                # Debug: Log the feature ID we're looking for
                logger.info(f"Looking for house district with NAME: {feature_id}")
            elif geo_level == 'senate':
                # Extract district number from different possible property names
                district_num = None
                if 'DISTRICT' in feature['properties']:
                    district_num = feature['properties']['DISTRICT']
                elif 'senate_id' in feature['properties']:
                    district_num = feature['properties']['senate_id']
                elif 'senate_name' in feature['properties'] and 'District' in feature['properties']['senate_name']:
                    # Try to extract the number from the name (e.g., 'State Senate District 1')
                    import re
                    match = re.search(r'District (\d+)', feature['properties']['senate_name'])
                    if match:
                        district_num = match.group(1)
                
                feature_id = f"State Senate District {district_num} (2022); Hawaii"
                # Also store a simpler display name
                feature['properties']['display_name'] = f"Senate District {district_num}"
                # Debug: Log the feature ID we're looking for
                logger.info(f"Looking for senate district with NAME: {feature_id}")
            else:
                feature_id = None
            
            # Store the ID in the properties
            feature['properties']['id'] = feature_id
            
            # Find matching data
            if feature_id:
                # Debug: Print feature ID we're trying to match
                logger.info(f"Trying to match feature_id: {feature_id}")
                
                # Check if 'name' column exists, otherwise try 'NAME' or create a name field
                name_col = 'name' if 'name' in acs_data.columns else 'NAME' if 'NAME' in acs_data.columns else None
                logger.info(f"Using name column: {name_col}")
                
                if name_col:
                    # Handle both single feature_id (string) and list of possible IDs (for counties)
                    possible_ids = [feature_id] if isinstance(feature_id, str) else feature_id
                    matching_rows = None
                    logger.info(f"Trying to match feature with {len(possible_ids)} possible IDs for geo_level: {geo_level}")
                    
                    # Debug logging for ACS data
                    logger.info(f"ACS data contains {len(acs_data)} rows with name column '{name_col}'")
                    logger.info(f"First few values in name column: {acs_data[name_col].head().tolist()}")
                    
                    for i, fid in enumerate(possible_ids):
                        logger.info(f"Trying ID format {i+1}: '{fid}'")
                        matching_rows = acs_data[acs_data[name_col] == fid]
                        if not matching_rows.empty:
                            logger.info(f"Found exact match for '{fid}'")
                            break
                        if isinstance(fid, str):
                            logger.info(f"Trying case-insensitive match for '{fid}'")
                            matching_rows = acs_data[acs_data[name_col].str.lower() == fid.lower()]
                            if not matching_rows.empty:
                                logger.info(f"Found case-insensitive match for '{fid}'")
                                break
                    
                    if matching_rows is not None:
                        logger.info(f"Found {len(matching_rows)} matches for {possible_ids}")
                        if len(matching_rows) > 0:
                            logger.info(f"Match data: {matching_rows.iloc[0].to_dict()}")
                    matching_data = matching_rows.to_dict('records') if matching_rows is not None else []
                else:
                    # If no name column exists, try matching by geoid or district number
                    if 'geoid' in acs_data.columns and 'GEOID' in feature['properties']:
                        geoid_val = feature['properties']['GEOID']
                        logger.info(f"Trying to match by GEOID: {geoid_val}")
                        matching_data = acs_data[acs_data['geoid'] == geoid_val].to_dict('records')
                    elif 'district' in acs_data.columns and 'DISTRICT' in feature['properties']:
                        district_val = feature['properties']['DISTRICT']
                        logger.info(f"Trying to match by DISTRICT: {district_val}")
                        matching_data = acs_data[acs_data['district'] == district_val].to_dict('records')
                    else:
                        # No matching criteria found
                        logger.info("No matching criteria found")
                        matching_data = []
                
                if matching_data:
                    # Add ACS data to feature properties
                    for key, value in matching_data[0].items():
                        # Skip name/id fields as we already have them
                        if key not in ['name', 'NAME', 'geoid', 'GEOID', 'district', 'DISTRICT']:
                            feature['properties'][key] = value
    
    # Map controls (no title)
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
        # Define variable options with display names
        variable_options = {
            'poverty_rate': 'Poverty Rate',
            'median_income': 'Median Income',
            'unemployment_rate': 'Unemployment Rate',
            'population': 'Population',
            'median_home_value': 'Median Home Value',
            'college_educated_pct': 'College Educated',
            'rent_burden_rate': 'Housing Cost Burden'
        }
        
        selected_var = st.selectbox(
            "Data Variable",
            options=list(variable_options.keys()),
            format_func=lambda x: variable_options[x],
            index=list(variable_options.keys()).index(selected_variable) if selected_variable in variable_options else 0,
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
    
    # Create a mapping of variable names to display names
    variable_display_names = {
        'poverty_rate': 'Poverty Rate',
        'median_income': 'Median Income',
        'unemployment_rate': 'Unemployment Rate',
        'population': 'Population',
        'median_home_value': 'Median Home Value',
        'college_educated_pct': 'College Educated (%)',
        'bachelors_rate': 'Bachelors Degree Rate',
        'renter_rate': 'Renter Rate',
        'rent_burden_rate': 'Housing Cost Burden (%)'
    }
    
    # Create the map
    clicked_feature = create_leaflet_map(
        geojson_data=geojson_data,
        selected_variable=selected_variable,
        variable_display_name=variable_display_names.get(selected_variable, selected_variable.replace('_', ' ').title()),
        color_scheme=color_scheme,
        map_height=500,
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

def prepare_feature_details(feature_id, geojson_data):
    """Prepare the feature details data for display.
    
    Args:
        feature_id: The ID of the feature to display details for.
        geojson_data: The GeoJSON data containing the feature.
        
    Returns:
        A dictionary containing the formatted feature details or None if the feature is not found.
    """
    # Find the feature in the GeoJSON data
    selected_feature = None
    for feature in geojson_data['features']:
        if feature['properties'].get('id') == feature_id:
            selected_feature = feature
            break
    
    if not selected_feature:
        return None
    
    # Get properties
    properties = selected_feature['properties']
    
    # Format display values
    feature_name = properties.get('name', properties.get('NAME', feature_id))
    
    # Format numeric values
    def format_number(value, prefix='', suffix=''):
        if isinstance(value, (int, float)):
            return f"{prefix}{value:,}{suffix}"
        return f"{prefix}{value}{suffix}"
    
    # Prepare data for each tab
    demographics = {
        "Population": format_number(properties.get('population', 'N/A')),
        "White Alone (%)": format_number(properties.get('white_alone_pct', 'N/A'), suffix='%'),
        "Asian Alone (%)": format_number(properties.get('asian_alone_pct', 'N/A'), suffix='%'),
        "Native Hawaiian/PI (%)": format_number(properties.get('native_hawaiian_pi_pct', 'N/A'), suffix='%')
    }
    
    economic = {
        "Poverty Rate": format_number(properties.get('poverty_rate', 'N/A'), suffix='%'),
        "Median Income": format_number(properties.get('median_income', 'N/A'), prefix='$'),
        "Unemployment Rate": format_number(properties.get('unemployment_rate', 'N/A'), suffix='%'),
        "SNAP Benefits (%)": format_number(properties.get('snap_benefits_pct', 'N/A'), suffix='%')
    }
    
    housing = {
        "Median Home Value": format_number(properties.get('median_home_value', 'N/A'), prefix='$'),
        "Homeownership Rate": format_number(properties.get('homeownership_rate', 'N/A'), suffix='%'),
        "Rent Burden (%)": format_number(properties.get('rent_burden_pct', 'N/A'), suffix='%'),
        "Median Rent": format_number(properties.get('median_rent', 'N/A'), prefix='$')
    }
    
    education_health = {
        "College Educated (%)": format_number(properties.get('college_educated_pct', 'N/A'), suffix='%'),
        "High School Graduate (%)": format_number(properties.get('high_school_grad_pct', 'N/A'), suffix='%'),
        "Health Insurance Coverage (%)": format_number(properties.get('health_insurance_pct', 'N/A'), suffix='%'),
        "Disability (%)": format_number(properties.get('disability_pct', 'N/A'), suffix='%')
    }
    
    return {
        "name": feature_name,
        "demographics": demographics,
        "economic": economic,
        "housing": housing,
        "education_health": education_health
    }


def display_feature_details(feature_id, geojson_data, selected_variable):
    """Display detailed information for the selected feature."""
    # Prepare the data
    details = prepare_feature_details(feature_id, geojson_data)
    
    if not details:
        return
    
    # Create a feature detail card
    st.markdown("### Feature Details")
    
    with st.container():
        st.markdown(f"#### {details['name']}")
        
        # Create tabs for different categories of data
        tab1, tab2, tab3, tab4 = st.tabs(["Demographics", "Economic", "Housing", "Education & Health"])
        
        with tab1:
            # Demographics tab
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Population", details['demographics']['Population'])
                st.metric("White Alone (%)", details['demographics']['White Alone (%)'])
            with col2:
                st.metric("Asian Alone (%)", details['demographics']['Asian Alone (%)'])
                st.metric("Native Hawaiian/PI (%)", details['demographics']['Native Hawaiian/PI (%)'])
        
        with tab2:
            # Economic tab
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Poverty Rate", details['economic']['Poverty Rate'])
                st.metric("Median Income", details['economic']['Median Income'])
            with col2:
                st.metric("Unemployment Rate", details['economic']['Unemployment Rate'])
                st.metric("SNAP Benefits (%)", details['economic']['SNAP Benefits (%)'])
        
        with tab3:
            # Housing tab
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Median Home Value", details['housing']['Median Home Value'])
                st.metric("Homeownership Rate", details['housing']['Homeownership Rate'])
            with col2:
                st.metric("Rent Burden (%)", details['housing']['Rent Burden (%)'])
                st.metric("Median Rent", details['housing']['Median Rent'])
        
        with tab4:
            # Education & Health tab
            col1, col2 = st.columns(2)
            with col1:
                st.metric("College Educated (%)", details['education_health']['College Educated (%)'])
                st.metric("High School Graduate (%)", details['education_health']['High School Graduate (%)'])
            with col2:
                st.metric("Health Insurance Coverage (%)", details['education_health']['Health Insurance Coverage (%)'])
                st.metric("Disability (%)", details['education_health']['Disability (%)'])

# This function is a duplicate and has been removed

def create_data_summary():
    """Create a summary of the data with a bar chart comparison."""
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
    
    if data is not None and not data.empty:
        # Create columns for summary statistics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if 'poverty_rate' in data.columns:
                avg_poverty = data['poverty_rate'].mean()
                st.metric("Average Poverty Rate", f"{avg_poverty:.1f}%")
        
        with col2:
            if 'median_income' in data.columns:
                avg_income = data['median_income'].mean()
                st.metric("Average Median Income", f"${avg_income:,.0f}")
        
        with col3:
            if 'population' in data.columns:
                total_pop = data['population'].sum()
                st.metric("Total Population", f"{total_pop:,}")
        
        # Add some space
        st.markdown("---")
        
        # Create two columns for chart and table
        chart_col, table_col = st.columns([2, 1])
        
        with chart_col:
            st.markdown(f"#### {selected_variable.replace('_', ' ').title()} Comparison")
            
            # Check if the selected variable exists in the data
            if selected_variable in data.columns:
                # Sort data by the selected variable for better visualization
                sorted_data = data.sort_values(by=selected_variable, ascending=False)
                
                # Create a bar chart
                st.bar_chart(
                    data=sorted_data,
                    x='name',
                    y=selected_variable,
                    use_container_width=True,
                    height=400
                )
                
                # Add some context about the chart
                st.caption(f"Comparison of {selected_variable.replace('_', ' ')} across {active_layer.lower()}")
            else:
                st.warning(f"Selected variable '{selected_variable}' not found in the data.")
        
        with table_col:
            st.markdown("#### Data Table")
            # Display a scrollable table
            st.dataframe(
                data[[col for col in ['name', selected_variable] if col in data.columns]],
                height=400,
                use_container_width=True
            )
        
        # Add a full-width data table below
        st.markdown("#### Full Data Table")
        st.dataframe(data, use_container_width=True)
        
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
