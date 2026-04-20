"""Leaflet Map View for Hawaii Appleseed Dashboard."""
import streamlit as st
import pandas as pd
import copy
import json
import logging
from pathlib import Path
import sys
import plotly.express as px

# Import local modules
from data.data_loader import DataLoader
from .leaflet_component import create_leaflet_map
from config.variable_registry import (
    get_valid_variable_keys,
    get_variables_for_dropdown,
    get_display_names,
    get_display_name,
    get_variable_source,
)

# Set up logging
logger = logging.getLogger(__name__)

@st.cache_resource
def load_geojson(layer_name):
    """Load GeoJSON data for the specified layer.

    Uses @st.cache_resource to avoid pickle/unpickle overhead on every call.
    The returned dict is shared across sessions (read-only). Callers that
    need to mutate the data must deep-copy it first.
    """
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

@st.cache_resource(ttl=None, show_spinner=False, hash_funcs={})
def get_data_loader(_cache_version="v7"):
    """Get a cached DataLoader instance."""
    # _cache_version parameter forces cache invalidation when changed
    return DataLoader()

# Bump this to bust _get_merged_geojson cache when the data pipeline changes.
# The cache has no other invalidation key, so stale merged GeoJSON persists until bumped.
_MERGED_GEOJSON_VERSION = "2026-04-19-v2"


@st.cache_data(show_spinner=False)
def _get_merged_geojson(layer_name, geo_level, _version=_MERGED_GEOJSON_VERSION):
    """Load GeoJSON and merge with statistical data, cached.

    Combines load_geojson + merge into one cached call so repeated
    renders skip both the deep-copy and the merge computation.
    """
    geojson_data = copy.deepcopy(load_geojson(layer_name))
    if geojson_data is None:
        return None
    data_loader = get_data_loader()
    return data_loader.merge_geojson_with_data(geojson_data, geo_level)


def create_leaflet_map_view(debug_info: bool = False) -> None:
    """Create the Leaflet map view."""
    logger.debug("Building Leaflet map view")
    
    # Initialize session state with comprehensive error handling
    try:
        # Ensure active_layer is set
        if 'active_layer' not in st.session_state:
            st.session_state['active_layer'] = 'State Boundary'
        
        # Valid variables loaded from centralized registry
        valid_variables = get_valid_variable_keys()
        
        # Ensure selected_variable is valid (None is allowed for mutual exclusivity)
        current_var = st.session_state.get('selected_variable', 'alice_rate')
        if current_var is not None and current_var not in valid_variables:
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
        
    # Apply pending dropdown resets BEFORE widgets are created.
    # Mapping from group name -> (widget key, state key for selected variable)
    _DROPDOWN_GROUPS = {
        'econ': ('variable_selector', 'selected_variable'),
        'food': ('food_security_selector', 'selected_food_security_variable'),
        'housing': ('housing_transportation_selector', 'selected_housing_transportation_variable'),
    }

    reset_flag = st.session_state.pop('_reset_other_dropdowns', None)
    if reset_flag in _DROPDOWN_GROUPS:
        # Clear all widget keys except the active group
        for name, (widget_key, _state_key) in _DROPDOWN_GROUPS.items():
            if name != reset_flag:
                st.session_state[widget_key] = None
    elif reset_flag == 'restore_econ':
        st.session_state['variable_selector'] = 'alice_rate'

    active_layer = st.session_state['active_layer']
    selected_variable = st.session_state['selected_variable']
    color_scheme = st.session_state['color_scheme']
    
    logger.info(f"Selected variable: {selected_variable}")
    logger.info(f"Active layer: {active_layer}")
    logger.info(f"Color scheme: {color_scheme}")
    
    # Map geo levels to their data loader equivalents
    geo_level_map = {
        'State Boundary': 'state',
        'Counties': 'county',
        'House Districts': 'house',
        'Senate Districts': 'senate'
    }
    geo_level = geo_level_map.get(active_layer, 'state')

    # Load GeoJSON and merge with statistical data (cached)
    geojson_data = _get_merged_geojson(active_layer, geo_level)

    if geojson_data is None:
        st.error(f"Failed to load GeoJSON data for {active_layer}")
        return
        
    # Dropdown scrolling fix (CSS styles are in app_style.css)
    st.markdown("""
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
        # Geography dropdown — styled distinctly via .st-key-layer_selector in enhanced_style.css
        st.markdown('<div style="color: #2a5a0c; font-family: Roboto, sans-serif; font-size: 0.7em; font-weight: 600; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 12px; padding-bottom: 6px; border-bottom: 2px solid transparent; visibility: hidden;">CHOOSE YOUR VARIABLE</div>'
                   '<div style="padding-bottom: 18px;"><span style="display: inline-block; background: #6a9a50; color: white; font-family: Roboto, sans-serif; font-weight: 600; font-size: 0.78em; padding: 3px 10px; border-radius: 4px; letter-spacing: 0.03em;">Geography</span></div>', unsafe_allow_html=True)
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
        # Economic Security dropdown with 'Choose your variable' text
        st.markdown('<div style="color: #2a5a0c; font-family: Roboto, sans-serif; font-size: 0.7em; font-weight: 600; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 12px; padding-bottom: 6px; border-bottom: 2px solid #c8e6b0;">Choose your variable</div>'
                   '<div style="padding-bottom: 18px;"><span style="display: inline-block; background: transparent; color: #2a5a0c; font-family: Roboto, sans-serif; font-weight: 600; font-size: 0.78em; padding: 3px 10px; border-radius: 4px; border: 1.5px solid #b8d4a0; letter-spacing: 0.03em;">Economic Security</span></div>', unsafe_allow_html=True)
        
        # Economic security dropdown options from centralized registry
        _econ_items = get_variables_for_dropdown('economic_security')
        variable_options = {item['key']: item['label'] for item in _econ_items}
        
        econ_keys = list(variable_options.keys())

        # Determine index: None means show placeholder, otherwise find position
        try:
            var_index = econ_keys.index(selected_variable) if selected_variable is not None else None
        except (ValueError, KeyError):
            var_index = None

        selected_var = st.selectbox(
            "",
            options=econ_keys,
            format_func=lambda x: variable_options[x],
            index=var_index,
            placeholder="Select Variable",
            key="variable_selector",
            label_visibility="collapsed"
        )

        # Update session state only if selection actually changes (prevents infinite loops)
        if selected_var != selected_variable:
            st.session_state['selected_variable'] = selected_var
            # Clear food security and housing/transportation selections when an economic variable is selected
            if selected_var is not None:
                st.session_state['selected_food_security_variable'] = None
                st.session_state['selected_housing_transportation_variable'] = None
                st.session_state['_reset_other_dropdowns'] = 'econ'
            st.rerun()
    
    with col3:
        # Food Security dropdown — spacer matches "Choose your variable" height
        st.markdown('<div style="color: #2a5a0c; font-family: Roboto, sans-serif; font-size: 0.7em; font-weight: 600; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 12px; padding-bottom: 6px; border-bottom: 2px solid transparent; visibility: hidden;">CHOOSE YOUR VARIABLE</div>'
                   '<div style="padding-bottom: 18px;"><span style="display: inline-block; background: transparent; color: #2a5a0c; font-family: Roboto, sans-serif; font-weight: 600; font-size: 0.78em; padding: 3px 10px; border-radius: 4px; border: 1.5px solid #b8d4a0; letter-spacing: 0.03em;">Food Security</span></div>', unsafe_allow_html=True)
        
        _food_items = get_variables_for_dropdown('food_security')
        food_security_options = {item['key']: item['label'] for item in _food_items}
        
        fs_keys = list(food_security_options.keys())

        # Get current food security variable
        selected_food_security_var = st.session_state.get('selected_food_security_variable', None)

        try:
            fs_index = fs_keys.index(selected_food_security_var) if selected_food_security_var is not None else None
        except (ValueError, TypeError):
            fs_index = None

        selected_fs_var = st.selectbox(
            "",
            options=fs_keys,
            format_func=lambda x: food_security_options[x],
            index=fs_index,
            placeholder="Select Variable",
            key="food_security_selector",
            label_visibility="collapsed"
        )
        
        # Update session state only if selection actually changes (prevents infinite loops)
        if selected_fs_var != selected_food_security_var:
            st.session_state['selected_food_security_variable'] = selected_fs_var
            # Clear other selections when food security variable is selected
            if selected_fs_var is not None:
                st.session_state['selected_variable'] = None
                st.session_state['selected_housing_transportation_variable'] = None
                st.session_state['_reset_other_dropdowns'] = 'food'
            else:
                # Restore default when food security is cleared and nothing else is active
                if st.session_state.get('selected_housing_transportation_variable') is None:
                    st.session_state['selected_variable'] = 'alice_rate'
                    st.session_state['_reset_other_dropdowns'] = 'restore_econ'
            st.rerun()
    
    with col4:
        # Housing and Transportation dropdown — spacer matches "Choose your variable" height
        st.markdown('<div style="color: #2a5a0c; font-family: Roboto, sans-serif; font-size: 0.7em; font-weight: 600; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 12px; padding-bottom: 6px; border-bottom: 2px solid transparent; visibility: hidden;">CHOOSE YOUR VARIABLE</div>'
                   '<div style="padding-bottom: 18px;"><span style="display: inline-block; background: transparent; color: #2a5a0c; font-family: Roboto, sans-serif; font-weight: 600; font-size: 0.78em; padding: 3px 10px; border-radius: 4px; border: 1.5px solid #b8d4a0; letter-spacing: 0.03em;">Housing &amp; Transportation</span></div>', unsafe_allow_html=True)
        
        _ht_items = get_variables_for_dropdown('housing_transportation')
        housing_transportation_options = {item['key']: item['label'] for item in _ht_items}
        
        ht_keys = list(housing_transportation_options.keys())

        # Get current housing/transportation variable
        selected_housing_transportation_var = st.session_state.get('selected_housing_transportation_variable', None)

        try:
            ht_index = ht_keys.index(selected_housing_transportation_var) if selected_housing_transportation_var is not None else None
        except (ValueError, TypeError):
            ht_index = None

        selected_ht_var = st.selectbox(
            "",
            options=ht_keys,
            format_func=lambda x: housing_transportation_options[x],
            index=ht_index,
            placeholder="Select Variable",
            key="housing_transportation_selector",
            label_visibility="collapsed"
        )
        
        # Update session state only if selection actually changes (prevents infinite loops)
        if selected_ht_var != selected_housing_transportation_var:
            st.session_state['selected_housing_transportation_variable'] = selected_ht_var
            # Clear other selections when housing/transportation variable is selected
            if selected_ht_var is not None:
                st.session_state['selected_variable'] = None
                st.session_state['selected_food_security_variable'] = None
                st.session_state['_reset_other_dropdowns'] = 'housing'
            else:
                # Restore default when housing/transportation is cleared and nothing else is active
                if st.session_state.get('selected_food_security_variable') is None:
                    st.session_state['selected_variable'] = 'alice_rate'
                    st.session_state['_reset_other_dropdowns'] = 'restore_econ'
            st.rerun()
    
    # Display names from centralized registry
    variable_display_names = get_display_names(long=True)
    
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
    
    # Display names from centralized registry
    variable_display_names = get_display_names(long=True)
    
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
        
        # CEP Section
        st.markdown("**CEP Schools**")
        cep_metrics = [
            ('cep_percentage', 'Schools with CEP', 'percentage'),
            ('cep_display', 'CEP Schools', 'text')
        ]
        
        for metric_key, metric_label, metric_type in cep_metrics:
            if metric_key in geo_info:
                value = geo_info[metric_key]
                # Handle both numeric and text values
                if isinstance(value, (int, float)) or (isinstance(value, str) and value):
                    is_selected = metric_key == selected_variable
                    style = "background: #e8f0fe; border: 1px solid #1a73e8; font-weight: bold;" if is_selected else "background: #f8f9fa; border: 1px solid #e0e0e0;"
                    
                    if metric_type == 'percentage' and isinstance(value, (int, float)):
                        formatted = f"{value:.1f}%"
                    elif metric_type == 'currency' and isinstance(value, (int, float)):
                        formatted = f"${value:,.0f}"
                    elif metric_type == 'text':
                        formatted = str(value)
                    else:
                        formatted = f"{value:,.0f}" if isinstance(value, (int, float)) else str(value)
                    
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
    
    # SNAP and CEP data section
    snap_data = {
        "SNAP Households": format_number(properties.get('snap_household_rate', 'N/A'), suffix='%'),
        "Avg Annual SNAP Benefit": format_number(properties.get('snap_benefit_annual_per_household', 'N/A'), prefix='$'),
        "Total Annual SNAP Benefits": format_number(properties.get('snap_benefits_annual_total', 'N/A'), prefix='$'),
        "Schools with CEP": format_number(properties.get('cep_percentage', 'N/A'), suffix='%'),
        "Number of CEP Schools": properties.get('cep_display', 'N/A')
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
            # SNAP and CEP tab
            col1, col2 = st.columns(2)
            with col1:
                st.metric("SNAP Households", details['snap']['SNAP Households'])
                st.metric("Avg Annual SNAP Benefit", details['snap']['Avg Annual SNAP Benefit'])
                st.metric("Schools with CEP", details['snap']['Schools with CEP'])
            with col2:
                st.metric("Total Annual SNAP Benefits", details['snap']['Total Annual SNAP Benefits'])
                st.metric("Number of CEP Schools", details['snap']['Number of CEP Schools'])
                st.markdown("<div style='height: 38px;'></div>", unsafe_allow_html=True)  # Spacer for alignment
        
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

    # ── Styles scoped to the data analysis section ──────────────────────────
    st.markdown("""
    <style>
        /* Hide Streamlit's fullscreen expand button on plotly charts only */
        [data-testid="stPlotlyChart"] [data-testid="StyledFullScreenButton"] {
            display: none !important;
        }
        /* Section label above chart / table panels */
        .da-section-label {
            font-size: 0.7rem;
            font-weight: 700;
            letter-spacing: 0.1em;
            text-transform: uppercase;
            color: #6b8f71;
            margin: 0 0 0.6rem 0;
            padding: 0;
        }
        /* Thin divider between chart row and full table */
        .da-divider {
            border: none;
            border-top: 1px solid #e2e8e3;
            margin: 1.5rem 0 1.25rem 0;
        }
        /* Geo context pill shown above the chart */
        .da-geo-pill {
            display: inline-block;
            background: #eef4ef;
            color: #3d6b45;
            font-size: 0.72rem;
            font-weight: 600;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            padding: 0.2rem 0.65rem;
            border-radius: 99px;
            margin-bottom: 0.5rem;
        }
        /* Download button row */
        .da-download-row {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            margin-top: 0.75rem;
        }
        .da-row-count {
            font-size: 0.75rem;
            color: #8fa899;
        }
    </style>
    """, unsafe_allow_html=True)

    # ── Resolve selected variable ────────────────────────────────────────────
    active_layer = st.session_state.get('active_layer', 'State Boundary')
    food_security_var = st.session_state.get('selected_food_security_variable')
    housing_transportation_var = st.session_state.get('selected_housing_transportation_variable')
    data_var = st.session_state.get('selected_variable')
    if food_security_var is not None:
        selected_variable = food_security_var
    elif housing_transportation_var is not None:
        selected_variable = housing_transportation_var
    elif data_var is not None:
        selected_variable = data_var
    else:
        selected_variable = 'alice_rate'

    # ── Load data ────────────────────────────────────────────────────────────
    data_loader = get_data_loader()
    geo_level_map = {
        'State Boundary': 'state',
        'Counties': 'county',
        'House Districts': 'house',
        'Senate Districts': 'senate',
    }
    geo_level = geo_level_map.get(active_layer, 'state')
    data = data_loader.get_data(geo_level)

    # Ensure name column
    if data is not None and 'name' not in data.columns:
        if 'NAME' in data.columns:
            data['name'] = data['NAME']
        elif 'geoid' in data.columns:
            data['name'] = 'Area ' + data['geoid'].astype(str)
        elif 'district' in data.columns:
            data['name'] = 'District ' + data['district'].astype(str)

    if data is None or data.empty:
        st.warning(f"No data available for {active_layer}")
        return

    # Get both short and long display names (long includes units)
    import re
    var_label_short = get_display_name(selected_variable, long=False)
    var_label_long = get_display_name(selected_variable, long=True)

    # Parse unit from long name (format: "Name (Unit)")
    unit_match = re.search(r'\(([^)]+)\)', var_label_long)
    unit = unit_match.group(1) if unit_match else ''

    # Chart title: "Percentage of X (GeoLevel)" for %, else "X (GeoLevel)"
    if unit == '%':
        chart_title = f"Percentage of {var_label_short} ({active_layer})"
    else:
        chart_title = f"{var_label_long} ({active_layer})"

    # ── Plotly chart config — remove autoscale, reset axes, and Plotly logo ─
    _chart_config = {
        'modeBarButtonsToRemove': ['autoScale2d', 'resetScale2d'],
        'displaylogo': False,
        'toImageButtonOptions': {'filename': f'hawaii_{geo_level}_{selected_variable}'},
    }

    # ── Chart + side table row ───────────────────────────────────────────────
    chart_col, table_col = st.columns([11, 5])

    with chart_col:
        st.markdown(f'<p class="da-geo-pill">{active_layer}</p>', unsafe_allow_html=True)
        source = get_variable_source(selected_variable)
        source_icon = f' <span title="Source: {source}" style="cursor:help;color:#999;font-style:normal">\u24D8</span>' if source else ''
        st.markdown(f'<p class="da-section-label">{var_label_short} — ranked comparison{source_icon}</p>', unsafe_allow_html=True)

        if selected_variable in data.columns:
            sorted_data = data.sort_values(by=selected_variable, ascending=False)
            num_items = len(sorted_data)

            bar_color = '#4a8c64'
            hover_template = (
                f"<b>%{{x}}</b><br>"
                f"{var_label_short}: %{{y}}<br>"
                f"<extra></extra>"
            )

            # Bar label format: include unit symbol if available
            if unit in ('%', '$'):
                text_template = f'%{{text:.1f}}{unit}' if unit == '%' else f'{unit}%{{text:,.0f}}'
            else:
                text_template = '%{text:.1f}'

            fig = px.bar(
                sorted_data,
                x='name',
                y=selected_variable,
                text=selected_variable,
                color_discrete_sequence=[bar_color],
                labels={'name': '', selected_variable: var_label_short},
            )
            fig.update_traces(
                texttemplate=text_template,
                textposition='outside',
                textfont=dict(size=9, color='#555'),
                cliponaxis=False,
                hovertemplate=hover_template,
                hoverlabel=dict(bgcolor='white', bordercolor='#ccc', font_size=12, font_family='Roboto, Arial'),
            )
            common_layout = dict(
                title=dict(
                    text=chart_title,
                    x=0.5,
                    xanchor='center',
                    font=dict(size=13, color='#333', family='Roboto, Arial'),
                ),
                height=400,
                showlegend=False,
                plot_bgcolor='white',
                paper_bgcolor='white',
                font=dict(family='Roboto, Arial', size=12, color='#333'),
                yaxis=dict(
                    gridcolor='#eef0ec',
                    gridwidth=1,
                    zeroline=False,
                    title_text=var_label_long,
                    title_font=dict(size=11, color='#666'),
                    tickfont=dict(size=10),
                ),
                xaxis=dict(title_text='', showgrid=False),
                margin=dict(l=55, r=20, t=50, b=60 if num_items <= 10 else 28),
                hoverlabel=dict(bgcolor='white'),
                uniformtext=dict(minsize=7, mode='hide'),
            )
            if num_items > 10:
                fig.update_xaxes(showticklabels=False)
                common_layout['margin']['b'] = 28
            else:
                fig.update_xaxes(tickangle=-40, tickfont=dict(size=10))
            fig.update_layout(**common_layout)

            # Add state average reference line for county/district charts
            if geo_level != 'state':
                state_data = data_loader.get_data('state')
                if state_data is not None and selected_variable in state_data.columns:
                    state_val = state_data[selected_variable].iloc[0]
                    if pd.notna(state_val):
                        # Format label based on unit
                        if unit == '%':
                            avg_label = f"State: {state_val:.1f}%"
                        elif unit == '$':
                            avg_label = f"State: ${state_val:,.0f}"
                        else:
                            avg_label = f"State: {state_val:.1f}"
                        fig.add_hline(
                            y=state_val,
                            line_dash="dot",
                            line_color="#e74c3c",
                            annotation_text=avg_label,
                            annotation_position="top right",
                            annotation_font_size=10,
                            annotation_font_color="#e74c3c",
                        )

            st.plotly_chart(fig, use_container_width=True, config=_chart_config)
            if num_items > 10:
                st.caption(f"Showing all {num_items} {active_layer.lower()} ranked by {var_label_short}. Hover for details.")
        else:
            st.warning(f"Variable '{selected_variable}' is not available for this geography level.")

    with table_col:
        st.markdown('<p class="da-section-label" style="margin-top:2.3rem">Selected variable</p>', unsafe_allow_html=True)
        display_cols = [c for c in ['name', selected_variable] if c in data.columns]
        st.dataframe(
            data[display_cols],
            height=400,
            use_container_width=True,
            column_config={
                'name': st.column_config.TextColumn('Area'),
                selected_variable: st.column_config.NumberColumn(var_label_long, format='%.1f'),
            },
        )

    # ── Full data table ──────────────────────────────────────────────────────
    st.markdown('<hr class="da-divider">', unsafe_allow_html=True)
    st.markdown('<p class="da-section-label">Full data table</p>', unsafe_allow_html=True)

    # Set medium column widths so the table overflows horizontally and shows a scrollbar
    full_col_config = {col: st.column_config.Column(width='medium') for col in data.columns}
    st.dataframe(
        data,
        height=420,
        use_container_width=True,
        column_config=full_col_config,
    )

    # ── Download ─────────────────────────────────────────────────────────────
    csv = data.to_csv(index=False)
    col_dl, col_info = st.columns([2, 8])
    with col_dl:
        st.download_button(
            label="⬇ Download CSV",
            data=csv,
            file_name=f"hawaii_{geo_level}_data.csv",
            mime="text/csv",
            key="data_summary_download_button",
            use_container_width=True,
        )
    with col_info:
        st.markdown(
            f'<p class="da-row-count" style="padding-top:0.6rem">'
            f'{len(data):,} rows · {len(data.columns):,} columns · {active_layer}</p>',
            unsafe_allow_html=True,
        )
