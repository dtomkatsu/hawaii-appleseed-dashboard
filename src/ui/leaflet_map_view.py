"""Leaflet Map View for Hawaii Appleseed Dashboard."""
import streamlit as st
import pandas as pd
import json
import logging
from pathlib import Path
import sys
import plotly.express as px

# Add the parent directory to the path
sys.path.append(str(Path(__file__).parent.parent.parent))

# Import local modules
from src.data.data_loader import DataLoader
# Remove MapBuilder import as we're not using it in this implementation
from src.ui.leaflet_component import create_leaflet_map

# Set up logging
logger = logging.getLogger(__name__)

@st.cache_data
def load_geojson(layer_name):
    """Load GeoJSON data for the specified layer."""
    import gzip
    
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
    
    # Construct the file paths (try compressed first)
    base_path = Path(__file__).parent.parent.parent / 'data' / 'Processed GeoJsons'
    compressed_path = base_path / f"{layer_files[layer_name]}.gz"
    original_path = base_path / layer_files[layer_name]
    
    try:
        # Try compressed file first
        if compressed_path.exists():
            with gzip.open(compressed_path, 'rt') as f:
                geojson_data = json.load(f)
                logger.info(f"Successfully loaded compressed GeoJSON for {layer_name}")
                return geojson_data
        
        # Fallback to original file
        elif original_path.exists():
            with open(original_path, 'r') as f:
                geojson_data = json.load(f)
                logger.info(f"Successfully loaded GeoJSON for {layer_name} from {original_path}")
                return geojson_data
        
        else:
            logger.error(f"Neither compressed nor original GeoJSON file found for {layer_name}")
            return None
            
    except Exception as e:
        logger.error(f"Error loading GeoJSON for {layer_name}: {str(e)}")
        return None

@st.cache_resource
def get_data_loader():
    """Get a cached DataLoader instance."""
    return DataLoader()

def create_leaflet_map_view(debug_info: bool = False) -> None:
    """Create the Leaflet map view."""
    logger.debug("Building Leaflet map view")
    
    # Initialize session state with comprehensive error handling
    try:
        # Ensure active_layer is set
        if 'active_layer' not in st.session_state:
            st.session_state['active_layer'] = 'State Boundary'
        
        # Define all valid variables including SNAP, transportation, tax credit, and CEP variables
        valid_variables = [
            'poverty_rate', 'median_income', 'unemployment_rate',
            'median_home_value', 'college_educated_pct', 'rent_burden_rate', 'alice_rate',
            'snap_household_rate', 'snap_benefit_annual_per_household', 'snap_benefits_annual_total',
            'travel_time_to_work_minutes', 'public_transportation_pct', 'ctc_avg_amount', 'ctc_participation_rate', 
            'federal_eitc_avg_amount', 'eitc_participation_rate', 'state_eitc_avg_amount',
            'cep_percentage', 'cep_schools', 'total_schools'
        ]
        
        # Ensure selected_variable is valid
        current_var = st.session_state.get('selected_variable', 'alice_rate')
        if current_var not in valid_variables:
            logger.warning(f"Invalid variable '{current_var}' in session state, resetting to alice_rate")
            st.session_state['selected_variable'] = 'alice_rate'
        elif 'selected_variable' not in st.session_state:
            st.session_state['selected_variable'] = 'alice_rate'
            
        # Ensure color_scheme is set
        if 'color_scheme' not in st.session_state:
            st.session_state['color_scheme'] = 'blue'
            
        # Initialize food security variable (starts as None - no selection)
        if 'selected_food_security_variable' not in st.session_state:
            st.session_state['selected_food_security_variable'] = None
            
        # Initialize housing/transportation variable (starts as None - no selection)
        if 'selected_housing_transportation_variable' not in st.session_state:
            st.session_state['selected_housing_transportation_variable'] = None
            
    except Exception as e:
        logger.error(f"Error initializing session state: {e}")
        # Force reset to safe defaults
        st.session_state['active_layer'] = 'State Boundary'
        st.session_state['selected_variable'] = 'alice_rate'
        st.session_state['color_scheme'] = 'blue'
        
    active_layer = st.session_state['active_layer']
    selected_variable = st.session_state['selected_variable']
    color_scheme = st.session_state['color_scheme']
    
    logger.info(f"Selected variable: {selected_variable}")
    logger.info(f"Active layer: {active_layer}")
    logger.info(f"Color scheme: {color_scheme}")
    
    # Load GeoJSON data for the selected layer with progress indicator
    with st.spinner(f"Loading {active_layer} geographic data..."):
        geojson_data = load_geojson(active_layer)
    
    if geojson_data is None:
        st.error(f"Failed to load GeoJSON data for {active_layer}")
        return
    
    # Load data with progress indicator
    with st.spinner(f"Loading {active_layer} statistical data..."):
        data_loader = get_data_loader()
        
        # Map geo levels to their data loader equivalents
        geo_level_map = {
            'State Boundary': 'state',
            'Counties': 'county',
            'House Districts': 'house',
            'Senate Districts': 'senate'
        }
        
        geo_level = geo_level_map.get(active_layer, 'state')
        
        # Get combined data for the selected geographic level
        combined_data = data_loader.get_data(geo_level)
    
    if combined_data is not None:
        # Debug: Print combined data columns and first row
        logger.info(f"Combined data columns: {combined_data.columns.tolist()}")
        if not combined_data.empty:
            logger.info(f"First row of combined data: {combined_data.iloc[0].to_dict()}")
        
        # Use the enhanced merging method from data_loader
        geojson_data = data_loader.merge_geojson_with_data(geojson_data, geo_level)
        
        # Legacy debug info for counties
        if geo_level == 'county':
            logger.info(f"COUNTY DATA DEBUG: Full dataframe:\n{combined_data}")
            logger.info(f"COUNTY DATA DEBUG: Column types:\n{combined_data.dtypes}")
            if 'alice_rate' in combined_data.columns:
                logger.info(f"COUNTY DATA DEBUG: ALICE rate values:\n{combined_data['alice_rate']}")
            if 'poverty_rate' in combined_data.columns:
                logger.info(f"COUNTY DATA DEBUG: Poverty rate values:\n{combined_data['poverty_rate']}")
    else:
        logger.warning(f"No combined data available for {geo_level}")
        
    # Note: The enhanced data loader now handles all the merging automatically
    # The following legacy code is no longer needed but kept for reference
    if False:  # Disabled legacy manual merging code
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
                # Create unique county ID with prefix to avoid conflicts
                county_fips = feature['properties'].get('county_fips')
                state_fips = feature['properties'].get('state_fips', '15')
                if county_fips and county_fips != 'null':
                    feature_id = f"county_{state_fips}{county_fips}"
                else:
                    # Fallback for counties without FIPS (like Oahu)
                    county_map = {'Hawaii': '001', 'Honolulu': '003', 'Kauai': '007', 'Maui': '009', 'Oahu': '003'}
                    county_fips = county_map.get(county_name, '999')
                    feature_id = f"county_{state_fips}{county_fips}"
                
                # Store the unique ID in the feature properties
                feature['properties']['unique_id'] = feature_id
                feature_formats = formats
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
                
                # Create unique house district ID with prefix
                feature_id = f"house_{district_num:05d}"  # e.g., house_00001
                
                # Store the unique ID and display name
                feature['properties']['unique_id'] = feature_id
                feature['properties']['display_name'] = f"House District {district_num}"
                # Debug: Log the feature ID we're looking for
                logger.info(f"Created unique house district ID: {feature_id}")
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
                
                # Create unique senate district ID with prefix
                feature_id = f"senate_{district_num:05d}"  # e.g., senate_00001
                
                # Store the unique ID and display name
                feature['properties']['unique_id'] = feature_id
                feature['properties']['display_name'] = f"Senate District {district_num}"
                # Debug: Log the feature ID we're looking for
                logger.info(f"Created unique senate district ID: {feature_id}")
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
                    # For counties, use the feature_formats for matching if available
                    if geo_level == 'county' and 'feature_formats' in locals():
                        possible_ids = feature_formats
                    else:
                        possible_ids = [feature_id] if isinstance(feature_id, str) else [feature_id] 
                    
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
    
    # Add custom styles for the map container and UI elements
    st.markdown("""
    <style>
        /* Style for dropdown container */
        .dropdown-container {
            display: flex;
            gap: 20px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }
        
        /* Style for dropdown wrapper */
        .dropdown-wrapper {
            position: relative;
            min-width: 200px;
            flex: 1;
        }
        
        /* Style for dropdown labels */
        .dropdown-label {
            font-weight: 600;
            margin-bottom: 4px;
            color: #1E88E5;
            display: block;
        }
        
        /* Style for dropdown hover effect */
        .stSelectbox {
            width: 100% !important;
        }
        
        .stSelectbox > div {
            width: 100% !important;
        }
        
        .stSelectbox > div > div[data-baseweb="select"] {
            transition: all 0.2s ease;
            border-radius: 6px;
            border: 1px solid #e0e0e0;
            background: white;
            width: 100% !important;
            min-height: 38px !important;
        }
        
        .stSelectbox > div > div[data-baseweb="select"]:hover {
            border-color: #1E88E5;
            box-shadow: 0 0 0 2px rgba(30, 136, 229, 0.2);
        }
        
        /* Control the selected value display */
        .stSelectbox > div > div[data-baseweb="select"] > div {
            padding: 6px 12px !important;
            font-size: 14px !important;
        }
        
        /* Style for dropdown options */
        [data-baseweb="popover"] {
            z-index: 1000 !important;
            position: fixed !important;
        }
        
        /* Map container styles */
        .map-container {
            width: 100% !important;
            height: 70vh !important;
            min-height: 500px;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            margin: 0 0 20px 0 !important;
            padding: 0 !important;
            position: relative;
        }
        
        /* Force proper dropdown positioning and scrolling */
        [data-baseweb="popover"] [data-baseweb="popover-content"] {
            max-height: 400px !important;
            overflow: hidden !important;
        }
        
        [data-baseweb="popover"] [role="listbox"] {
            padding: 8px 0 !important;
            max-height: 400px !important;
            overflow-y: auto !important;
            overflow-x: hidden !important;
            scrollbar-width: thin !important;
        }
        
        /* Webkit scrollbar styling for better UX */
        [data-baseweb="popover"] [role="listbox"]::-webkit-scrollbar {
            width: 6px !important;
        }
        
        [data-baseweb="popover"] [role="listbox"]::-webkit-scrollbar-track {
            background: #f1f1f1 !important;
            border-radius: 3px !important;
        }
        
        [data-baseweb="popover"] [role="listbox"]::-webkit-scrollbar-thumb {
            background: #c1c1c1 !important;
            border-radius: 3px !important;
        }
        
        [data-baseweb="popover"] [role="listbox"]::-webkit-scrollbar-thumb:hover {
            background: #a8a8a8 !important;
        }
        
        [data-baseweb="popover"] [role="listbox"] > div {
            padding: 0 !important;
            margin: 0 !important;
        }
        
        [data-baseweb="popover"] [role="listbox"] [role="option"] {
            padding: 10px 16px 10px 12px !important;
            margin: 0 !important;
            transition: all 0.2s ease !important;
            border-left: 3px solid transparent !important;
            position: relative !important;
            left: 0 !important;
            z-index: 1 !important;
            min-height: 40px !important;
            display: flex !important;
            align-items: center !important;
        }
        
        [data-baseweb="popover"] [role="listbox"] [role="option"]:hover {
            background-color: #f5f5f5 !important;
            border-left: 3px solid #1E88E5 !important;
            transform: translateX(4px) !important;
            z-index: 2 !important;
            box-shadow: -2px 0 5px rgba(0,0,0,0.1) !important;
        }
        
        /* Style for selected option */
        [data-baseweb="popover"] [role="listbox"] [aria-selected="true"] {
            background-color: #E3F2FD !important;
            font-weight: 500 !important;
            border-left: 3px solid #1E88E5 !important;
        }
    </style>
    <script>
    // Enhanced fix for dropdown scrolling issues
    function fixDropdownScrolling() {
        // Find all dropdown containers
        const dropdowns = document.querySelectorAll('[data-baseweb="popover"] [role="listbox"]');
        
        dropdowns.forEach(dropdown => {
            // Force proper scrolling behavior
            dropdown.style.maxHeight = '350px';
            dropdown.style.overflowY = 'auto';
            dropdown.style.overflowX = 'hidden';
            dropdown.style.scrollBehavior = 'smooth';
            
            // Ensure proper container setup
            const container = dropdown.parentElement;
            if (container) {
                container.style.maxHeight = '350px';
                container.style.overflow = 'hidden';
            }
            
            // Fix individual options
            const options = dropdown.querySelectorAll('[role="option"]');
            options.forEach((option, index) => {
                option.style.minHeight = '42px';
                option.style.maxHeight = '42px';
                option.style.display = 'flex';
                option.style.alignItems = 'center';
                option.style.padding = '8px 12px';
                option.style.boxSizing = 'border-box';
                option.style.whiteSpace = 'nowrap';
                option.style.overflow = 'hidden';
                option.style.textOverflow = 'ellipsis';
                
                // Add hover scroll behavior
                option.addEventListener('mouseenter', function() {
                    this.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                });
            });
            
            // Add keyboard scroll support
            dropdown.addEventListener('keydown', function(e) {
                if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
                    setTimeout(() => {
                        const selected = dropdown.querySelector('[aria-selected="true"]');
                        if (selected) {
                            selected.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                        }
                    }, 10);
                }
            });
        });
    }
    
    // Enhanced observer for better detection
    let observer;
    
    function startObserver() {
        if (observer) observer.disconnect();
        
        observer = new MutationObserver(function(mutations) {
            let shouldFix = false;
            
            mutations.forEach(function(mutation) {
                if (mutation.addedNodes.length > 0) {
                    mutation.addedNodes.forEach(function(node) {
                        if (node.nodeType === 1) { // Element node
                            if (node.matches && node.matches('[data-baseweb="popover"]')) {
                                shouldFix = true;
                            } else if (node.querySelector && node.querySelector('[data-baseweb="popover"]')) {
                                shouldFix = true;
                            }
                        }
                    });
                }
            });
            
            if (shouldFix) {
                setTimeout(fixDropdownScrolling, 50);
                setTimeout(fixDropdownScrolling, 200);
            }
        });
        
        observer.observe(document.body, {
            childList: true,
            subtree: true,
            attributes: false
        });
    }
    
    // Initialize
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
            startObserver();
            setTimeout(fixDropdownScrolling, 100);
        });
    } else {
        startObserver();
        setTimeout(fixDropdownScrolling, 100);
    }
    
    // Also fix on window events
    window.addEventListener('resize', function() {
        setTimeout(fixDropdownScrolling, 100);
    });
    
    // Periodic check for stubborn cases
    setInterval(fixDropdownScrolling, 2000);
    </script>
    """, unsafe_allow_html=True)
    
    # Create dropdown controls in main content area
    col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
    
    with col1:
        # Geography dropdown
        st.markdown('<div class="dropdown-label" style="color: #2a5a0c; font-family: Roboto, sans-serif; font-weight: 600;">Geography</div>', unsafe_allow_html=True)
        layer_options = ['State Boundary', 'Counties', 'House Districts', 'Senate Districts']
        try:
            layer_index = layer_options.index(active_layer)
        except (ValueError, KeyError):
            layer_index = 0
            
        selected_layer = st.selectbox(
            "",
            layer_options,
            index=layer_index,
            key="layer_selector",
            label_visibility="collapsed"
        )
        
        # Update session state only if selection actually changes (prevents infinite loops)
        if selected_layer != active_layer:
            st.session_state['active_layer'] = selected_layer
            st.rerun()
    
    with col2:
        # Data Variable dropdown
        st.markdown('<div class="dropdown-label" style="color: #2a5a0c; font-family: Roboto, sans-serif; font-weight: 600;">Data Variable</div>', unsafe_allow_html=True)
        
        # Define available variables based on geography
        if active_layer == 'State Boundary':
            variable_options = {
                'alice_rate': 'ALICE Households',
                'poverty_rate': 'Poverty Rate',
                'median_income': 'Median Income',
                'ctc_avg_amount': 'Child Tax Credit - Average Amount ($)',
                'ctc_participation_rate': 'Child Tax Credit - Participation Rate (%)',
                'federal_eitc_avg_amount': 'Federal EITC - Average Amount ($)',
                'eitc_participation_rate': 'Federal EITC - Participation Rate (%)',
                'state_eitc_avg_amount': 'State EITC - Average Amount ($)'
            }
        elif active_layer == 'Counties':
            variable_options = {
                'alice_rate': 'ALICE Households',
                'poverty_rate': 'Poverty Rate',
                'median_income': 'Median Income',
                'ctc_avg_amount': 'Child Tax Credit - Average Amount ($)',
                'ctc_participation_rate': 'Child Tax Credit - Participation Rate (%)',
                'federal_eitc_avg_amount': 'Federal EITC - Average Amount ($)',
                'eitc_participation_rate': 'Federal EITC - Participation Rate (%)',
                'state_eitc_avg_amount': 'State EITC - Average Amount ($)'
            }
        else:  # House and Senate Districts
            variable_options = {
                'alice_rate': 'ALICE Households',
                'poverty_rate': 'Poverty Rate',
                'median_income': 'Median Income',
                'ctc_avg_amount': 'Child Tax Credit - Average Amount ($)',
                'ctc_participation_rate': 'Child Tax Credit - Participation Rate (%)',
                'federal_eitc_avg_amount': 'Federal EITC - Average Amount ($)',
                'eitc_participation_rate': 'Federal EITC - Participation Rate (%)',
                'state_eitc_avg_amount': 'State EITC - Average Amount ($)'
            }
        
        # Get current variable index
        try:
            var_index = list(variable_options.keys()).index(selected_variable)
        except (ValueError, KeyError):
            var_index = 0
            
        selected_var = st.selectbox(
            "",
            options=list(variable_options.keys()),
            format_func=lambda x: variable_options[x],
            index=var_index,
            key="variable_selector",
            label_visibility="collapsed"
        )
        
        # Update session state only if selection actually changes (prevents infinite loops)
        if selected_var != selected_variable:
            st.session_state['selected_variable'] = selected_var
            # Clear food security and housing/transportation selections when data variable is selected
            if 'selected_food_security_variable' in st.session_state:
                st.session_state['selected_food_security_variable'] = None
            if 'selected_housing_transportation_variable' in st.session_state:
                st.session_state['selected_housing_transportation_variable'] = None
            st.rerun()
    
    with col3:
        # Food Security dropdown
        st.markdown('<div class="dropdown-label" style="color: #2a5a0c; font-family: Roboto, sans-serif; font-weight: 600;">Food Security</div>', unsafe_allow_html=True)
        
        food_security_options = {
            'snap_household_rate': 'SNAP Households (%)',
            'snap_benefit_annual_per_household': 'Avg Annual SNAP Benefit',
            'snap_benefits_annual_total': 'Total Annual SNAP Benefits',
            'cep_percentage': 'Schools with CEP (%)',
            'cep_schools': 'Number of CEP Schools',
            'total_schools': 'Total Number of Schools'
        }
        
        # Add None option for mutual exclusion
        fs_options = [None] + list(food_security_options.keys())
        
        def fs_format_func(x):
            if x is None:
                return "Select Food Security Variable..."
            return food_security_options[x]
        
        # Get current food security variable
        selected_food_security_var = st.session_state.get('selected_food_security_variable', None)
        
        try:
            fs_index = fs_options.index(selected_food_security_var)
        except (ValueError, TypeError):
            fs_index = 0
            
        selected_fs_var = st.selectbox(
            "",
            options=fs_options,
            format_func=fs_format_func,
            index=fs_index,
            key="food_security_selector",
            label_visibility="collapsed"
        )
        
        # Update session state only if selection actually changes (prevents infinite loops)
        if selected_fs_var != selected_food_security_var:
            st.session_state['selected_food_security_variable'] = selected_fs_var
            # Clear data variable and housing/transportation selections when food security variable is selected
            if selected_fs_var is not None:
                st.session_state['selected_variable'] = None
                if 'selected_housing_transportation_variable' in st.session_state:
                    st.session_state['selected_housing_transportation_variable'] = None
            else:
                # Set default data variable when food security is cleared
                st.session_state['selected_variable'] = 'alice_rate'
            st.rerun()
    
    with col4:
        # Housing and Transportation dropdown
        st.markdown('<div class="dropdown-label" style="color: #2a5a0c; font-family: Roboto, sans-serif; font-weight: 600;">Housing & Transportation</div>', unsafe_allow_html=True)
        
        housing_transportation_options = {
            'rent_burden_rate': 'Housing Cost Burden (%)',
            'travel_time_to_work_minutes': 'Average Travel Time to Work (minutes)',
            'public_transportation_pct': 'Public Transportation Commuters (%)'
        }
        
        # Add None option for mutual exclusion
        ht_options = [None] + list(housing_transportation_options.keys())
        
        def ht_format_func(x):
            if x is None:
                return "Select Housing/Transportation Variable..."
            return housing_transportation_options[x]
        
        # Get current housing/transportation variable
        selected_housing_transportation_var = st.session_state.get('selected_housing_transportation_variable', None)
        
        try:
            ht_index = ht_options.index(selected_housing_transportation_var)
        except (ValueError, TypeError):
            ht_index = 0
            
        selected_ht_var = st.selectbox(
            "",
            options=ht_options,
            format_func=ht_format_func,
            index=ht_index,
            key="housing_transportation_selector",
            label_visibility="collapsed"
        )
        
        # Update session state only if selection actually changes (prevents infinite loops)
        if selected_ht_var != selected_housing_transportation_var:
            st.session_state['selected_housing_transportation_variable'] = selected_ht_var
            # Clear data variable and food security selections when housing/transportation variable is selected
            if selected_ht_var is not None:
                st.session_state['selected_variable'] = None
                if 'selected_food_security_variable' in st.session_state:
                    st.session_state['selected_food_security_variable'] = None
            else:
                # Set default data variable when housing/transportation is cleared
                st.session_state['selected_variable'] = 'alice_rate'
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
        'rent_burden_rate': 'Housing Cost Burden (%)',
        'alice_rate': 'ALICE Households (%)',
        'snap_household_rate': 'SNAP Households (%)',
        'snap_benefit_annual_per_household': 'Avg Annual SNAP Benefit ($)',
        'snap_benefits_annual_total': 'Total Annual SNAP Benefits ($)',
        'travel_time_to_work_minutes': 'Average Travel Time to Work (minutes)',
        'cep_percentage': 'Schools with CEP (%)',
        'cep_schools': 'Number of CEP Schools',
        'total_schools': 'Total Number of Schools'
    }
    
    # Determine which variable to use for the map
    food_security_var = st.session_state.get('selected_food_security_variable')
    housing_transportation_var = st.session_state.get('selected_housing_transportation_variable')
    data_var = st.session_state.get('selected_variable')
    
    # Use food security variable if selected, otherwise housing/transportation, otherwise data variable
    if food_security_var is not None:
        map_variable = food_security_var
    elif housing_transportation_var is not None:
        map_variable = housing_transportation_var
    elif data_var is not None:
        map_variable = data_var
    else:
        # Default to alice_rate if nothing is selected, but don't update session state to avoid loops
        map_variable = 'alice_rate'
    
    # Create the map with built-in JavaScript info panel
    create_leaflet_map(
        geojson_data=geojson_data,
        selected_variable=map_variable,
        variable_display_name=variable_display_names.get(map_variable, map_variable.replace('_', ' ').title()),
        color_scheme=color_scheme,
        active_layer=active_layer,
        map_height=500,
        key=f"map-{active_layer}-{map_variable}-{color_scheme}",
        show_side_panel=True  # Enable the JavaScript panel as a popup-style panel
    )

def create_info_panel(selected_variable, geojson_data):
    """Create the static info panel that shows selected geography details."""
    st.markdown("### Geographic Info")
    
    # Initialize session state for selected geography if not exists
    if 'selected_geography' not in st.session_state:
        st.session_state.selected_geography = None
    
    # No need for additional JavaScript communication since we're using proper component return values
    
    # Variable display names mapping
    variable_display_names = {
        'poverty_rate': 'Poverty Rate (%)',
        'median_income': 'Median Income ($)',
        'college_educated_pct': 'College Educated (%)',
        'rent_burden_rate': 'Housing Cost Burden (%)',
        'alice_rate': 'ALICE Households (%)',
        'snap_household_rate': 'SNAP Households (%)',
        'snap_benefit_annual_per_household': 'Avg Annual SNAP Benefit ($)',
        'snap_benefits_annual_total': 'Total Annual SNAP Benefits ($)',
        'travel_time_to_work_minutes': 'Average Travel Time to Work (minutes)',
        'public_transportation_pct': 'Public Transportation Commuters (%)',
        'ctc_avg_amount': 'Child Tax Credit - Average Amount ($)',
        'ctc_participation_rate': 'Child Tax Credit - Participation Rate (%)',
        'federal_eitc_avg_amount': 'Federal EITC - Average Amount ($)',
        'eitc_participation_rate': 'Federal EITC - Participation Rate (%)',
        'state_eitc_avg_amount': 'State EITC - Average Amount ($)'
    }
    
    # Display selected variable
    if selected_variable:
        var_name = variable_display_names.get(selected_variable, selected_variable.replace('_', ' ').title())
        st.markdown(f"**Selected Variable:** {var_name}")
    else:
        st.markdown("**Selected Variable:** No variable selected")
    
    st.markdown("---")
    
    # Display selected geography info
    if st.session_state.selected_geography:
        geo_info = st.session_state.selected_geography
        st.markdown(f"**{geo_info.get('name', 'Unknown')}**")
        
        # Show selected variable prominently
        if selected_variable and selected_variable in geo_info:
            value = geo_info[selected_variable]
            var_name = variable_display_names.get(selected_variable, selected_variable.replace('_', ' ').title())
            
            if isinstance(value, (int, float)):
                if selected_variable.endswith('_pct') or selected_variable.endswith('_rate'):
                    formatted_value = f"{value:.1f}%"
                elif 'income' in selected_variable or 'amount' in selected_variable:
                    formatted_value = f"${value:,.0f}"
                elif 'minutes' in selected_variable:
                    formatted_value = f"{value:.1f} minutes"
                else:
                    formatted_value = f"{value:,.0f}"
            else:
                formatted_value = str(value)
            
            st.markdown(f"<div style='background: #1a73e8; color: white; padding: 8px; border-radius: 4px; text-align: center; margin: 10px 0;'><strong>{var_name}: {formatted_value}</strong></div>", unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Key Metrics Section
        st.markdown("**Key Metrics**")
        key_metrics = [
            ('poverty_rate', 'Poverty Rate', 'percentage'),
            ('median_income', 'Median Income', 'currency'),
            ('unemployment_rate', 'Unemployment Rate', 'percentage'),
            ('population', 'Population', 'number')
        ]
        
        for metric_key, metric_label, metric_type in key_metrics:
            if metric_key in geo_info:
                value = geo_info[metric_key]
                if isinstance(value, (int, float)):
                    is_selected = metric_key == selected_variable
                    style = "background: #e8f0fe; border: 1px solid #1a73e8; font-weight: bold;" if is_selected else "background: #f8f9fa; border: 1px solid #e0e0e0;"
                    
                    if metric_type == 'percentage':
                        formatted = f"{value:.1f}%"
                    elif metric_type == 'currency':
                        formatted = f"${value:,.0f}"
                    else:
                        formatted = f"{value:,.0f}"
                    
                    st.markdown(f"<div style='{style} padding: 4px 6px; margin: 2px 0; border-radius: 3px; line-height: 1.2;'><div style='font-size: 10px; color: #666;'>{metric_label}</div><div style='font-size: 12px; color: #333;'>{formatted}</div></div>", unsafe_allow_html=True)
        
        st.markdown("---")
        
        # SNAP Section
        st.markdown("**SNAP**")
        snap_metrics = [
            ('snap_household_rate', 'SNAP Households', 'percentage'),
            ('snap_benefit_annual_per_household', 'Avg Annual Benefit', 'currency'),
            ('snap_benefits_annual_total', 'Total Annual Benefits', 'currency')
        ]
        
        for metric_key, metric_label, metric_type in snap_metrics:
            if metric_key in geo_info:
                value = geo_info[metric_key]
                if isinstance(value, (int, float)):
                    is_selected = metric_key == selected_variable
                    style = "background: #e8f0fe; border: 1px solid #1a73e8; font-weight: bold;" if is_selected else "background: #f8f9fa; border: 1px solid #e0e0e0;"
                    
                    if metric_type == 'percentage':
                        formatted = f"{value:.1f}%"
                    elif metric_type == 'currency':
                        formatted = f"${value:,.0f}"
                    else:
                        formatted = f"{value:,.0f}"
                    
                    st.markdown(f"<div style='{style} padding: 4px 6px; margin: 2px 0; border-radius: 3px; line-height: 1.2;'><div style='font-size: 10px; color: #666;'>{metric_label}</div><div style='font-size: 12px; color: #333;'>{formatted}</div></div>", unsafe_allow_html=True)
        
        st.markdown("---")
        
        # View Detailed Data Button
        if 'unique_id' in geo_info and geo_info['unique_id']:
            geo_id = geo_info['unique_id']
            detail_url = f"/geo_detail?geo_id={geo_id}"
            st.markdown(f"<div style='text-align: center; margin-top: 12px;'><a href='{detail_url}' target='_blank' style='display: inline-block; background-color: #3a7710; color: white; padding: 8px 16px; border-radius: 4px; text-decoration: none; font-weight: bold;'>View Detailed Data</a></div>", unsafe_allow_html=True)
        else:
            st.markdown("<div style='text-align: center; margin-top: 12px;'><span style='display: inline-block; background-color: #ccc; color: #666; padding: 8px 16px; border-radius: 4px; font-style: italic;'>Detailed data unavailable</span></div>", unsafe_allow_html=True)
    else:
        st.markdown("**Location:** Click on the map to select a location")
        st.markdown("**Value:** No location selected")

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
        "ALICE Households": format_number(properties.get('alice_rate', 'N/A'), suffix='%')
    }
    
    # SNAP data section
    snap_data = {
        "SNAP Households": format_number(properties.get('snap_household_rate', 'N/A'), suffix='%'),
        "Avg Annual SNAP Benefit": format_number(properties.get('snap_benefit_annual_per_household', 'N/A'), prefix='$'),
        "Total Annual SNAP Benefits": format_number(properties.get('snap_benefits_annual_total', 'N/A'), prefix='$')
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
        "snap": snap_data,
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
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["Key Metrics", "SNAP", "Demographics", "Housing", "Education & Health"])
        
        with tab1:
            # Key Metrics tab (Economic data)
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Poverty Rate", details['economic']['Poverty Rate'])
                st.metric("Median Income", details['economic']['Median Income'])
            with col2:
                st.metric("Unemployment Rate", details['economic']['Unemployment Rate'])
                st.metric("ALICE Households", details['economic']['ALICE Households'])
        
        with tab2:
            # SNAP tab
            col1, col2 = st.columns(2)
            with col1:
                st.metric("SNAP Households", details['snap']['SNAP Households'])
                st.metric("Avg Annual SNAP Benefit", details['snap']['Avg Annual SNAP Benefit'])
            with col2:
                st.metric("Total Annual SNAP Benefits", details['snap']['Total Annual SNAP Benefits'])
        
        with tab3:
            # Demographics tab
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Population", details['demographics']['Population'])
                st.metric("White Alone (%)", details['demographics']['White Alone (%)'])
            with col2:
                st.metric("Asian Alone (%)", details['demographics']['Asian Alone (%)'])
                st.metric("Native Hawaiian/PI (%)", details['demographics']['Native Hawaiian/PI (%)'])
        
        with tab4:
            # Housing tab
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Median Home Value", details['housing']['Median Home Value'])
                st.metric("Homeownership Rate", details['housing']['Homeownership Rate'])
            with col2:
                st.metric("Rent Burden (%)", details['housing']['Rent Burden (%)'])
                st.metric("Median Rent", details['housing']['Median Rent'])
        
        with tab5:
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
    selected_variable = st.session_state.get('selected_variable', 'alice_rate')
    
    # Load data
    data_loader = get_data_loader()
    
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
                
                # Calculate appropriate width based on number of data points
                num_items = len(sorted_data)
                
                # For many items (districts), hide x-axis labels to avoid crowding
                if num_items > 10:
                    # Create the chart with custom hover template
                    fig = px.bar(
                        sorted_data,
                        x='name',
                        y=selected_variable,
                        title=f"{selected_variable.replace('_', ' ').title()} by {active_layer}",
                        labels={'name': active_layer, selected_variable: selected_variable.replace('_', ' ').title()}
                    )
                    
                    # Format the variable name for display
                    variable_display_name = selected_variable.replace('_', ' ').title()
                    
                    # Create custom hover template similar to map hover
                    hover_template = f"""
                    <b>%{{x}}</b><br>
                    {variable_display_name}: %{{y}}<br>
                    <extra></extra>
                    """
                    
                    # Update traces with custom hover template
                    fig.update_traces(
                        hovertemplate=hover_template,
                        hoverlabel=dict(
                            bgcolor="white",
                            bordercolor="black",
                            font_size=12,
                            font_family="Arial"
                        )
                    )
                    
                    # Update layout - hide x-axis labels for districts
                    fig.update_layout(
                        height=400,
                        margin=dict(l=50, r=50, t=50, b=50),
                        showlegend=False,
                        title_x=0.5
                    )
                    
                    # Hide x-axis labels and ticks for cleaner look
                    fig.update_xaxes(
                        showticklabels=False,
                        title_text=""
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                    
                else:
                    # For fewer items, use regular chart with custom hover
                    fig = px.bar(
                        sorted_data,
                        x='name',
                        y=selected_variable,
                        title=f"{selected_variable.replace('_', ' ').title()} by {active_layer}",
                        labels={'name': active_layer, selected_variable: selected_variable.replace('_', ' ').title()}
                    )
                    
                    # Format the variable name for display
                    variable_display_name = selected_variable.replace('_', ' ').title()
                    
                    # Create custom hover template similar to map hover
                    hover_template = f"""
                    <b>%{{x}}</b><br>
                    {variable_display_name}: %{{y}}<br>
                    <extra></extra>
                    """
                    
                    # Update traces with custom hover template
                    fig.update_traces(
                        hovertemplate=hover_template,
                        hoverlabel=dict(
                            bgcolor="white",
                            bordercolor="black",
                            font_size=12,
                            font_family="Arial"
                        )
                    )
                    
                    fig.update_layout(
                        height=400,
                        xaxis_tickangle=-45,
                        margin=dict(l=50, r=50, t=50, b=100),
                        showlegend=False
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                
                # Add some context about the chart
                st.caption(f"Comparison of {selected_variable.replace('_', ' ')} across {active_layer.lower()}. Chart is horizontally scrollable for better readability.")
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
