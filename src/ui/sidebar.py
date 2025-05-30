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
    st.sidebar.title("Hawaii Appleseed Dashboard")
    
    # Define layer options (moved to map view)
    layer_options = [
        'State Boundary',
        'County Boundaries',
        'State House Districts',
        'State Senate Districts'
    ]
    
    # Initialize session state for active layer if not set
    if 'active_layer' not in st.session_state:
        st.session_state.active_layer = 'State Boundary'
    
    # Map settings
    st.sidebar.markdown("### Map Settings")
    show_legend = st.sidebar.checkbox("Show Legend", value=True)
    debug_info = st.sidebar.checkbox("Show Debug Info", value=False)
    
    if debug_info:
        st.sidebar.warning("Debug mode is enabled")
    
    # About section
    st.sidebar.markdown("---")
    st.sidebar.info(
        "Hawaii Appleseed Dashboard\n\n"
        "Explore geographic data for Hawaii."
    )
    
    return {
        'active_layer': st.session_state.active_layer,
        'show_legend': show_legend,
        'debug_info': debug_info
    }
