"""Sidebar components for the Hawaii Appleseed Dashboard."""
import streamlit as st
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

def create_sidebar() -> Dict[str, Any]:
    """
    Create the sidebar with layer selection and other controls.
    
    Returns:
        Dict containing the user selections
    """
    st.sidebar.title("🌴 Hawaii Appleseed Dashboard")
    
    # Define layer options
    layer_options = [
        'State Boundary',
        'Counties',
        'House Districts',
        'Senate Districts'
    ]
    
    # Initialize session state for active layer if not set
    if 'active_layer' not in st.session_state:
        st.session_state.active_layer = 'State Boundary'
    
    # Variable options with descriptions
    variable_options = {
        'poverty_rate': 'Poverty Rate',
        'median_income': 'Median Income',
        'median_home_value': 'Median Home Value ($)',
        'unemployment_rate': 'Unemployment Rate (%)',
        'college_educated_pct': 'Bachelor\'s Degree or Higher (%)',
        'rent_burden_rate': 'Housing Cost Burden (%)',
        'white_alone_pct': 'White Alone (%)',
        'asian_alone_pct': 'Asian Alone (%)',
        'native_hawaiian_pi_pct': 'Native Hawaiian/Pacific Islander (%)',
        'alice_rate': 'ALICE Households (%)',
        'snap_household_rate': 'SNAP Households (%)',
        'snap_benefit_annual_per_household': 'Avg Annual SNAP Benefit ($)',
        'snap_benefits_annual_total': 'Total Annual SNAP Benefits ($)'
    }
    
    # Initialize selected variable if not set
    if 'selected_variable' not in st.session_state:
        st.session_state.selected_variable = 'poverty_rate'
    
    # Color scheme options with descriptive names
    color_schemes = {
        'blue': 'Blue Scale',
        'green': 'Green Scale',
        'red': 'Red Scale',
        'purple': 'Purple Scale'
    }
    
    # Initialize color scheme if not set
    if 'color_scheme' not in st.session_state:
        st.session_state.color_scheme = 'blue'
    
    # Data visualization controls
    st.sidebar.markdown("### 📊 Visualization Controls")
    
    # Layer selection
    try:
        layer_index = layer_options.index(st.session_state.active_layer)
    except (ValueError, KeyError):
        layer_index = 0
    
    active_layer = st.sidebar.selectbox(
        "Map Layer:",
        options=layer_options,
        index=layer_index,
        key="sidebar_layer_selector"
    )
    st.session_state.active_layer = active_layer
    
    # Variable selection with descriptions
    try:
        variable_index = list(variable_options.keys()).index(st.session_state.selected_variable)
    except (ValueError, KeyError):
        variable_index = 0
        
    selected_variable = st.sidebar.selectbox(
        "Select Variable:",
        options=list(variable_options.keys()),
        format_func=lambda x: variable_options[x],
        index=variable_index,
        key="sidebar_variable_selector"
    )
    st.session_state.selected_variable = selected_variable
    
    # Color scheme selection
    try:
        color_index = list(color_schemes.keys()).index(st.session_state.color_scheme)
    except (ValueError, KeyError):
        color_index = 0
        
    selected_color = st.sidebar.selectbox(
        "Color Scheme:",
        options=list(color_schemes.keys()),
        format_func=lambda x: color_schemes[x],
        index=color_index,
        key="sidebar_color_selector"
    )
    st.session_state.color_scheme = selected_color
    
    # Display options
    st.sidebar.markdown("### 🔧 Display Options")
    show_legend = st.sidebar.checkbox("Show Legend", value=True)
    show_labels = st.sidebar.checkbox("Show Area Labels", value=True)
    debug_info = st.sidebar.checkbox("Show Debug Info", value=False)
    
    if debug_info:
        st.sidebar.warning("⚠️ Debug mode is enabled")
    
    # Data download section
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📥 Download Data")
    st.sidebar.download_button(
        label="Download Current Data (CSV)",
        data="sample,data\n1,2\n3,4",  # This would be replaced with actual data
        file_name="hawaii_appleseed_data.csv",
        mime="text/csv",
        key="sidebar_download_button"
    )
    
    # About section
    st.sidebar.markdown("---")
    st.sidebar.info(
        "### About\n\n"
        "Hawaii Appleseed Dashboard provides interactive visualizations "
        "of demographic and economic data for the state of Hawaii.\n\n"
        "Data sources: US Census Bureau, ACS 5-Year Estimates"
    )
    
    return {
        'active_layer': st.session_state.active_layer,
        'selected_variable': st.session_state.selected_variable,
        'color_scheme': st.session_state.color_scheme,
        'show_legend': show_legend,
        'show_labels': show_labels,
        'debug_info': debug_info
    }
